"""Single LLM entry point — one client, retries, cost tracking, two providers.

Every LLM call in PolicyAI goes through here. Set ``LLM_PROVIDER``:

  - ``anthropic`` (default) : Claude. extraction -> sonnet, mapping -> opus.
  - ``openai_compatible``   : any OpenAI-compatible chat endpoint, so the whole
    pipeline can run on OPEN-SOURCE models from Hugging Face (or Groq / Together /
    Ollama) for free. Set:
        LLM_PROVIDER=openai_compatible
        OPENAI_BASE_URL=https://router.huggingface.co/v1   # HF Inference Providers
        OPENAI_API_KEY=<your HF token>                     # or Groq/Together key
        LLM_MODEL=meta-llama/Llama-3.3-70B-Instruct        # tool-calling open model

Structured extraction uses *forced tool/function calling* on both providers, then
validates the arguments against a Pydantic model — so extraction, obligation
mapping, and the Ask agent all work unchanged on open models.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic").lower()

# USD per 1M tokens, (input, output). Open-model providers default to 0 (free/unknown).
PRICING: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
}

MODEL_EXTRACTION = os.getenv("ANTHROPIC_MODEL_EXTRACTION", "claude-sonnet-4-6")
MODEL_MAPPING = os.getenv("ANTHROPIC_MODEL_MAPPING", "claude-opus-4-8")


def is_payload_too_large(exc: Exception) -> bool:
    """A 413 'request too large' from an OpenAI-compatible gateway (Groq et al)."""
    msg = str(exc)
    return "413" in msg and ("Request too large" in msg or "reduce your message size" in msg)


def _drop_nulls(value):
    if isinstance(value, dict):
        return {k: _drop_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [_drop_nulls(v) for v in value]
    return value


def _validate_with_repair(schema: type[T], data: dict) -> T:
    """Validate a near-miss generation, repairing what's safely repairable:
    backfill a missing summary from the title, then prune individual list items
    that fail validation (a reference without a title, a malformed deadline)
    rather than failing the whole document. Re-raises when the remaining errors
    are not item-local."""
    from pydantic import ValidationError

    if "summary" in schema.model_fields and "summary" not in data:
        data["summary"] = data.get("title", "")
    for _ in range(10):
        try:
            return schema.model_validate(data)
        except ValidationError as ve:
            targets: set[tuple[tuple, int]] = set()
            for err in ve.errors():
                loc = err["loc"]
                idx_pos = max((i for i, p in enumerate(loc) if isinstance(p, int)), default=None)
                if idx_pos is not None:
                    targets.add((tuple(loc[:idx_pos]), loc[idx_pos]))
            if not targets:
                raise
            for path, idx in sorted(targets, key=lambda t: t[1], reverse=True):
                node: object = data
                try:
                    for p in path:
                        node = node[p]  # type: ignore[index]
                    if isinstance(node, list) and 0 <= idx < len(node):
                        node.pop(idx)
                except (KeyError, IndexError, TypeError):
                    raise ve from None
    raise ValueError(f"could not repair {schema.__name__} generation")


def _recover_failed_tool_call(exc: Exception, schema: type[T]) -> T | None:
    """Groq validates forced-tool arguments server-side and 400s on near-misses
    (a missing field, ``null`` where the schema wants ``[]``) while embedding the
    raw generation in the error body. Recover it: parse the JSON, drop nulls so
    Pydantic defaults apply, backfill a missing summary, and validate locally.
    Returns None when the error carries no usable generation."""
    body = getattr(exc, "body", None)
    err = body.get("error", body) if isinstance(body, dict) else {}
    failed = err.get("failed_generation") if isinstance(err, dict) else None
    if not failed or err.get("code") != "tool_use_failed":
        return None
    start, end = failed.find("{"), failed.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = _drop_nulls(json.loads(failed[start : end + 1]))
        return _validate_with_repair(schema, data)
    except Exception:  # noqa: BLE001 - unrecoverable generation; surface the original error
        return None


# Open-source / OpenAI-compatible config (used when LLM_PROVIDER=openai_compatible).
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://router.huggingface.co/v1")
OPENAI_MODEL = os.getenv("LLM_MODEL", "meta-llama/Llama-3.3-70B-Instruct")
# Per-request token ceiling enforced by the gateway (input + max_tokens). Groq's
# free tier rejects anything over its TPM limit with a 413, and its retry-after
# on those is 30-60s, so *proactively* sizing requests under the cap is worth
# far more than reactive retries. 0 disables the cap (HF/Together/paid Groq).
OPENAI_TPM_LIMIT = int(
    os.getenv("OPENAI_TPM_LIMIT") or ("12000" if "groq" in OPENAI_BASE_URL.lower() else "0")
)


def _fit_budget(messages: list[dict], schema_json: str, max_tokens: int) -> int:
    """Cap the completion budget so input + output stays under the gateway's
    per-request token limit. Chars/3 over-estimates tokens for English text,
    which is the safe direction."""
    if not OPENAI_TPM_LIMIT:
        return max_tokens
    est_input = (sum(len(str(m.get("content") or "")) for m in messages) + len(schema_json)) // 3
    return max(1024, min(max_tokens, OPENAI_TPM_LIMIT - est_input - 256))


@dataclass
class CostTracker:
    """Running total of token spend across a process (e.g. one crawl + map run)."""

    input_tokens: int = 0
    output_tokens: int = 0
    calls: int = 0
    by_model: dict[str, dict[str, int]] = field(default_factory=dict)

    def record(self, model: str, in_tok: int, out_tok: int) -> None:
        self.input_tokens += in_tok
        self.output_tokens += out_tok
        self.calls += 1
        bucket = self.by_model.setdefault(model, {"input": 0, "output": 0, "calls": 0})
        bucket["input"] += in_tok
        bucket["output"] += out_tok
        bucket["calls"] += 1

    @property
    def usd(self) -> float:
        total = 0.0
        for model, b in self.by_model.items():
            in_rate, out_rate = PRICING.get(model, (0.0, 0.0))
            total += b["input"] / 1_000_000 * in_rate + b["output"] / 1_000_000 * out_rate
        return round(total, 4)

    def summary(self) -> str:
        return (
            f"{self.calls} calls, {self.input_tokens} in / {self.output_tokens} out "
            f"tokens, ${self.usd}"
        )


def _to_openai_tool(name: str, description: str, schema: dict) -> dict:
    return {
        "type": "function",
        "function": {"name": name, "description": description, "parameters": schema},
    }


class LLMClient:
    """One async client with a provider switch. Public methods are identical
    across providers so callers (pipeline, mapping, agent) never branch."""

    def __init__(self, *, max_retries: int = 4) -> None:
        self.provider = LLM_PROVIDER
        self.cost = CostTracker()
        if self.provider == "openai_compatible":
            from openai import AsyncOpenAI

            self._oai = AsyncOpenAI(
                base_url=OPENAI_BASE_URL,
                api_key=os.getenv("OPENAI_API_KEY") or os.getenv("HF_API_TOKEN", ""),
                max_retries=max_retries,
            )
            self._model = OPENAI_MODEL
        else:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(
                api_key=os.getenv("ANTHROPIC_API_KEY"), max_retries=max_retries
            )

    # ---- text completion --------------------------------------------------
    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        model: str = MODEL_EXTRACTION,
        max_tokens: int = 4096,
        thinking: bool = False,
        effort: str | None = None,
    ) -> str:
        if self.provider == "openai_compatible":
            messages = ([{"role": "system", "content": system}] if system else []) + [
                {"role": "user", "content": prompt}
            ]
            resp = await self._oai.chat.completions.create(
                model=self._model, max_tokens=max_tokens, messages=messages
            )
            self._record_openai(resp)
            return resp.choices[0].message.content or ""

        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        if thinking:
            kwargs["thinking"] = {"type": "adaptive"}
        if effort:
            kwargs["output_config"] = {"effort": effort}
        resp = await self._client.messages.create(**kwargs)
        self.cost.record(model, resp.usage.input_tokens, resp.usage.output_tokens)
        return "".join(b.text for b in resp.content if b.type == "text")

    # ---- structured extraction (forced tool/function call) ----------------
    async def extract(
        self,
        prompt: str,
        schema: type[T],
        *,
        system: str | None = None,
        model: str = MODEL_EXTRACTION,
        max_tokens: int = 8192,
        tool_name: str = "record",
        tool_description: str | None = None,
    ) -> T:
        description = tool_description or f"Record the extracted {schema.__name__}."
        if self.provider == "openai_compatible":
            messages = ([{"role": "system", "content": system}] if system else []) + [
                {"role": "user", "content": prompt}
            ]
            # Free-tier gateways (Groq) count max_tokens toward the per-request
            # token cap, so an 8k completion budget can 413 a modest prompt.
            # Size the request under the cap up front, then shrink the budget on
            # a 413 anyway (the estimate can undershoot); the caller's input-clip
            # fallback handles genuinely oversized prompts.
            schema_json = json.dumps(schema.model_json_schema())
            budget = _fit_budget(messages, schema_json, max_tokens)
            while True:
                try:
                    resp = await self._oai.chat.completions.create(
                        model=self._model,
                        max_tokens=budget,
                        messages=messages,
                        tools=[_to_openai_tool(tool_name, description, schema.model_json_schema())],
                        tool_choice={"type": "function", "function": {"name": tool_name}},
                    )
                    break
                except Exception as exc:
                    if is_payload_too_large(exc) and budget > 2048:
                        budget //= 2
                        continue
                    recovered = _recover_failed_tool_call(exc, schema)
                    if recovered is not None:
                        return recovered
                    raise
            self._record_openai(resp)
            calls = resp.choices[0].message.tool_calls or []
            if not calls:
                raise ValueError(f"Model did not return a '{tool_name}' function call")
            args_json = calls[0].function.arguments
            try:
                return schema.model_validate_json(args_json)
            except Exception:
                # Gateways without server-side tool validation (Cerebras et al)
                # hand us near-miss JSON directly: drop nulls so Pydantic defaults
                # apply, then repair item-local misses. Re-raises if still invalid.
                return _validate_with_repair(schema, _drop_nulls(json.loads(args_json)))

        tool = {
            "name": tool_name,
            "description": description,
            "input_schema": schema.model_json_schema(),
        }
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "tools": [tool],
            "tool_choice": {"type": "tool", "name": tool_name},
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        resp = await self._client.messages.create(**kwargs)
        self.cost.record(model, resp.usage.input_tokens, resp.usage.output_tokens)
        for block in resp.content:
            if block.type == "tool_use" and block.name == tool_name:
                return schema.model_validate(block.input)
        raise ValueError(f"Model did not return a '{tool_name}' tool call")

    # ---- agentic tool-use loop (the Ask agent) ----------------------------
    async def converse_with_tools(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_runner,
        model: str = MODEL_MAPPING,
        max_tokens: int = 4096,
        max_iters: int = 6,
    ) -> str:
        if self.provider == "openai_compatible":
            return await self._converse_openai(
                system, messages, tools, tool_runner, max_tokens, max_iters
            )
        for _ in range(max_iters):
            resp = await self._client.messages.create(
                model=model, max_tokens=max_tokens, system=system, tools=tools, messages=messages
            )
            self.cost.record(model, resp.usage.input_tokens, resp.usage.output_tokens)
            if resp.stop_reason != "tool_use":
                return "".join(b.text for b in resp.content if b.type == "text")
            messages.append({"role": "assistant", "content": resp.content})
            results = []
            for block in resp.content:
                if block.type == "tool_use":
                    output = await tool_runner(block.name, block.input)
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": output}
                    )
            messages.append({"role": "user", "content": results})
        return "".join(b.text for b in resp.content if b.type == "text")

    async def converse_with_tools_stream(
        self,
        *,
        system: str,
        messages: list[dict],
        tools: list[dict],
        tool_runner,
        model: str = MODEL_MAPPING,
        max_tokens: int = 4096,
        max_iters: int = 6,
    ):
        """Async generator yielding assistant text deltas as they are produced.

        Runs the same ≤max_iters tool loop as ``converse_with_tools`` but streams
        the final answer token-by-token, so the UI shows first text in ~1s instead
        of waiting for the whole generation. Tool-deciding turns stream too (any
        preamble is usually empty); tools run between turns as before.
        """
        if self.provider == "openai_compatible":
            # Open models: no token streaming here — emit the whole answer once.
            text = await self._converse_openai(
                system, messages, tools, tool_runner, max_tokens, max_iters
            )
            if text:
                yield text
            return
        for _ in range(max_iters):
            async with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                system=system,
                tools=tools,
                messages=messages,
            ) as stream:
                async for delta in stream.text_stream:
                    yield delta
                final = await stream.get_final_message()
            self.cost.record(model, final.usage.input_tokens, final.usage.output_tokens)
            if final.stop_reason != "tool_use":
                return
            messages.append({"role": "assistant", "content": final.content})
            results = []
            for block in final.content:
                if block.type == "tool_use":
                    output = await tool_runner(block.name, block.input)
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": output}
                    )
            messages.append({"role": "user", "content": results})

    async def _converse_openai(
        self, system, messages, tools, tool_runner, max_tokens, max_iters
    ) -> str:
        oai_tools = [
            _to_openai_tool(t["name"], t.get("description", ""), t["input_schema"]) for t in tools
        ]
        oai_messages = [{"role": "system", "content": system}] + list(messages)
        for _ in range(max_iters):
            resp = await self._oai.chat.completions.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=oai_messages,
                tools=oai_tools,
                tool_choice="auto",
            )
            self._record_openai(resp)
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content or ""
            oai_messages.append(msg.model_dump(exclude_none=True))
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments or "{}")
                output = await tool_runner(tc.function.name, args)
                oai_messages.append({"role": "tool", "tool_call_id": tc.id, "content": output})
        return ""

    def _record_openai(self, resp) -> None:
        usage = getattr(resp, "usage", None)
        if usage:
            self.cost.record(
                self._model,
                getattr(usage, "prompt_tokens", 0) or 0,
                getattr(usage, "completion_tokens", 0) or 0,
            )

    async def aclose(self) -> None:
        if self.provider == "openai_compatible":
            await self._oai.close()
        else:
            await self._client.close()
