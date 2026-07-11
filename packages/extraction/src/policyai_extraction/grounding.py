"""Lightweight grounding check shared by the mapping engine and the eval harness.

"Grounded" means a generated claim (a gap description) shares enough content with
the source material (the requirement text + the company's policy excerpts) that it
is plausibly *about* that material rather than invented. It is a cheap, dependency-
free guard against the LLM hallucinating gaps the regulation never implied — used
at write time in the mapping engine and as a scoring signal in the eval suite, so
both judge grounding the same way.
"""

from __future__ import annotations

_STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "of",
    "to",
    "in",
    "for",
    "on",
    "is",
    "are",
    "be",
    "with",
    "as",
    "by",
    "that",
    "this",
    "it",
    "its",
    "from",
    "at",
    "must",
    "shall",
    "should",
    "no",
    "not",
    "company",
    "policy",
    "does",
    "have",
    "has",
    "any",
    "all",
}


def _norm(s: str) -> str:
    return s.strip().lower()


def _stem(token: str) -> str:
    """Light Porter-style step-1a stemming so plural/verb variants match
    ('rates'->'rate', 'incidents'->'incident', 'reporting'->'report') without
    pulling in a full stemming dependency. Order matters: handle 'sses'/'ies'
    before the bare trailing 's', and never strip 's' from an '...ss' word."""
    if token.endswith("sses") and len(token) > 5:
        return token[:-2]  # caresses -> caress
    if token.endswith("ies") and len(token) > 4:
        return token[:-3] + "i"  # ponies -> poni
    for suffix in ("ing", "ed"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[: -len(suffix)]
    if token.endswith("s") and not token.endswith("ss") and len(token) > 3:
        return token[:-1]  # rates -> rate, incidents -> incident
    return token


def content_tokens(text: str) -> set[str]:
    raw = _norm(text).replace(",", " ").replace(".", " ").replace("-", " ").split()
    return {_stem(t) for t in raw if len(t) > 3 and t not in _STOPWORDS}


def is_grounded(text: str, corpus: str, min_overlap: int = 2) -> bool:
    """True if ``text`` shares at least ``min_overlap`` content tokens with ``corpus``.

    A claim with no content tokens of its own (e.g. empty/very short) is treated as
    grounded — there is nothing to hallucinate.
    """
    toks = content_tokens(text)
    if not toks:
        return True
    corpus_toks = content_tokens(corpus)
    return len(toks & corpus_toks) >= min(min_overlap, len(toks))
