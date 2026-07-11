"""Unit tests for the extraction package — pure logic, no DB or network."""

from __future__ import annotations

import pytest
from policyai_extraction import notifications
from policyai_extraction.embeddings import EMBEDDING_DIM, EmbeddingError, _check_dims, _normalize_hf
from policyai_extraction.grounding import content_tokens, is_grounded
from policyai_extraction.llm import MODEL_EXTRACTION, MODEL_MAPPING, PRICING, CostTracker
from policyai_extraction.pipeline import canonical_topic, load_prompt
from policyai_extraction.schemas import ExtractedRegulation, ObligationMapping


def test_routing_classifies_complexity():
    from policyai_extraction.routing import classify_complexity

    # length-driven
    assert classify_complexity("short notice", "notification") == "low"
    assert classify_complexity("y" * 5000, "circular") == "medium"
    assert classify_complexity("x" * 15000, "master_direction") == "high"
    # a dense doc type escalates a medium-length body to high
    assert classify_complexity("z" * 5000, "master_direction") == "high"
    # a light doc type caps a long body at medium
    assert classify_complexity("p" * 15000, "press_release") == "medium"
    # reference density bumps a tiny body to medium
    assert classify_complexity("tiny", "circular", reference_count=6) == "medium"


def test_routing_model_selection_and_toggle(monkeypatch):
    from policyai_extraction import routing

    monkeypatch.setenv("MODEL_ROUTING", "true")
    # cheap model for trivial docs, strong model for dense ones
    assert routing.model_for("extraction", "low") == "claude-haiku-4-5"
    assert routing.model_for("mapping", "low") == "claude-sonnet-4-6"
    assert routing.model_for("mapping", "high") == "claude-opus-4-8"
    m, tag = routing.route_model("mapping", "x" * 20000, "master_direction")
    assert m == "claude-opus-4-8" and tag == "high"

    # env override wins
    monkeypatch.setenv("MODEL_MAPPING_LOW", "claude-haiku-4-5")
    assert routing.model_for("mapping", "low") == "claude-haiku-4-5"

    # routing disabled -> stage default, no tag
    monkeypatch.setenv("MODEL_ROUTING", "false")
    m, tag = routing.route_model("mapping", "anything")
    assert tag is None and m == routing.MODEL_MAPPING


def test_ingest_helpers():
    from datetime import date

    from policyai_extraction.ingest import _content_hash, _parse_date

    # content hash is stable + sensitive to title or body changes
    assert _content_hash("T", "body") == _content_hash("T", "body")
    assert _content_hash("T", "body") != _content_hash("T", "BODY")
    assert _content_hash("T", "body") != _content_hash("X", "body")
    # date parsing is forgiving
    assert _parse_date("2026-03-14") == date(2026, 3, 14)
    assert _parse_date("2026-03-14T00:00:00Z") == date(2026, 3, 14)
    assert _parse_date(None) is None
    assert _parse_date("garbage") is None


def test_grounding_accepts_overlapping_claim():
    req = "The lender must disclose the effective interest rate in the loan factsheet."
    assert is_grounded("Factsheet omits the effective interest rate disclosure.", req)
    # stemming: 'disclosure'/'disclose', 'rates'/'rate'
    assert is_grounded("No disclosure of interest rates.", req)


def test_grounding_rejects_hallucinated_claim():
    req = "The lender must disclose the effective interest rate in the loan factsheet."
    assert not is_grounded("No cryptocurrency custody desk for offshore settlement.", req)


def test_grounding_empty_claim_is_trivially_grounded():
    # Nothing to hallucinate -> not penalised.
    assert is_grounded("", "anything")
    assert is_grounded("the of a", "anything")  # only stopwords


def test_content_tokens_drops_stopwords_and_short_words():
    toks = content_tokens("The company must file a quarterly return.")
    assert "quarterly" in toks and "file" in toks and "return" in toks
    assert "the" not in toks and "must" not in toks


def test_cost_tracker_pricing_math():
    c = CostTracker()
    c.record("claude-opus-4-8", 1_000_000, 1_000_000)
    assert c.usd == pytest.approx(30.0)  # $5 in + $25 out per MTok
    c.record("claude-sonnet-4-6", 1_000_000, 0)
    assert c.usd == pytest.approx(33.0)  # + $3 in
    assert c.calls == 2
    assert "calls" in c.summary()


def test_models_and_pricing_are_known():
    assert MODEL_EXTRACTION in PRICING
    assert MODEL_MAPPING in PRICING
    assert PRICING["claude-opus-4-8"] == (5.0, 25.0)


def test_canonical_topic_normalizes():
    assert canonical_topic("Know Your Customer (KYC)") == "know_your_customer_kyc"
    assert canonical_topic("  Capital Adequacy  ") == "capital_adequacy"
    assert canonical_topic("Fair Practices Code!!!") == "fair_practices_code"


@pytest.mark.parametrize(
    "name", ["regulation_extraction_v1.md", "company_profile_v1.md", "obligation_mapping_v1.md"]
)
def test_prompts_load_non_empty(name):
    body = load_prompt(name)
    assert len(body) > 50
    assert "---" not in body  # separator stripped


def test_check_dims_rejects_wrong_width():
    with pytest.raises(EmbeddingError):
        _check_dims([[0.0, 1.0, 2.0]])
    ok = [[0.0] * EMBEDDING_DIM]
    assert _check_dims(ok) == ok


async def test_reranker_noop_when_off(monkeypatch):
    from policyai_extraction import rerank

    monkeypatch.setattr(rerank, "RERANK_PROVIDER", "off")
    # disabled -> identity order, truncated to top_k, no model loaded
    assert rerank.is_enabled() is False
    order = await rerank.rerank("q", ["a", "b", "c"], top_k=2)
    assert order == [0, 1]


def test_provider_registry_includes_local():
    from policyai_extraction.embeddings import _PROVIDERS

    assert {"local", "hf", "voyage", "cohere"} <= set(_PROVIDERS)


async def test_hf_requires_endpoint_or_token(monkeypatch):
    from policyai_extraction.embeddings import _embed_hf

    monkeypatch.delenv("HF_EMBEDDING_ENDPOINT", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    with pytest.raises(EmbeddingError):
        await _embed_hf(["hello"])


def test_normalize_hf_shapes():
    nested = [[0.1, 0.2], [0.3, 0.4]]
    assert _normalize_hf(nested, 2) == nested
    # bare single vector -> wrapped
    assert _normalize_hf([0.1, 0.2, 0.3], 1) == [[0.1, 0.2, 0.3]]
    # dict-wrapped
    assert _normalize_hf({"embeddings": nested}, 2) == nested


def test_extracted_regulation_defaults_and_validation():
    reg = ExtractedRegulation(
        title="Master Direction on NBFC-MFI",
        regulator_key="rbi",
        summary="Sets pricing caps for microfinance loans.",
    )
    assert reg.entity_classes == []
    assert reg.severity == "medium"
    # round-trips through the JSON schema the LLM tool layer uses
    assert "title" in ExtractedRegulation.model_json_schema()["properties"]


def test_email_alerts_off_by_default(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.delenv("ALERT_EMAIL_TO", raising=False)
    assert notifications.is_configured() is False
    assert notifications.should_email("new_obligation") is False


def test_email_kind_filtering(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("ALERT_EMAIL_TO", "ops@example.com")
    monkeypatch.delenv("ALERT_EMAIL_KINDS", raising=False)  # use defaults
    assert notifications.is_configured() is True
    assert notifications.should_email("new_obligation") is True
    assert notifications.should_email("scan_failed") is True
    # NEW_REGULATION excluded by default to avoid backfill spam
    assert notifications.should_email("new_regulation") is False


async def test_notify_alert_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    # returns False without making any network call
    assert await notifications.notify_alert("new_obligation", "x") is False


def test_obligation_mapping_nested_tasks():
    m = ObligationMapping.model_validate(
        {
            "is_relevant": True,
            "title": "Update KYC policy",
            "summary": "Refresh periodic KYC cadence.",
            "tasks": [{"title": "Revise KYC SOP", "priority": "high"}],
        }
    )
    assert m.tasks[0].title == "Revise KYC SOP"
    assert m.tasks[0].priority == "high"
