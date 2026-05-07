"""Deterministic LLM fallback.

Used when OPENAI_API_KEY is unset or FORCE_MOCK_LLM is on. Produces a citation-
grounded answer by extracting the most relevant sentences from the retrieved
chunks. The output is intentionally extractive, never hallucinated, and stable
across runs so the demo is reproducible.

This module also provides a hashing-based embedding fallback so the project
indexes successfully even on a machine that cannot download a model.
"""
from __future__ import annotations

import hashlib
import re
from typing import Iterable

import numpy as np

from .utils import clean_text, truncate

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z(])")


def _split_sentences(text: str) -> list[str]:
    text = clean_text(text)
    if not text:
        return []
    parts = _SENT_SPLIT.split(text)
    return [p.strip() for p in parts if len(p.strip()) > 0]


def _score_sentence(sent: str, query_terms: set[str]) -> int:
    sl = sent.lower()
    return sum(1 for t in query_terms if t in sl)


def compose_answer(query: str, chunks: list[dict]) -> str:
    """Extractive, citation-aware answer. Stable across runs."""
    if not chunks:
        return (
            "I could not find relevant material in the local knowledge base for "
            "this question. Please rephrase, or escalate to a hardware engineer "
            "for a topic-specific answer."
        )

    query_terms = {t for t in re.findall(r"[a-zA-Z_]+", query.lower()) if len(t) >= 3}

    bullets: list[str] = []
    seen: set[str] = set()
    for chunk in chunks[:3]:
        source = chunk.get("source", "unknown")
        section = chunk.get("section", "")
        sentences = _split_sentences(chunk.get("text", ""))
        if not sentences:
            continue
        scored = sorted(
            ((_score_sentence(s, query_terms), -i, s) for i, s in enumerate(sentences)),
            reverse=True,
        )
        picked: list[str] = []
        for score, _, sent in scored:
            if len(picked) >= 2:
                break
            key = sent[:80]
            if key in seen:
                continue
            seen.add(key)
            picked.append(sent)
        if picked:
            citation = f"[{source}" + (f" › {section}" if section else "") + "]"
            bullets.append(f"- {' '.join(picked)} {citation}")

    answer = "\n".join(bullets) if bullets else (
        "Relevant context was retrieved but no high-signal sentences matched the query. "
        "Please review the retrieved chunks below directly."
    )

    answer += (
        "\n\n*This answer was assembled by the deterministic fallback (no LLM API "
        "key configured). It is extracted directly from the cited sources and is "
        "general guidance only.*"
    )
    return answer


# ---------------------------------------------------------------------------
# Hashing-based embedding fallback
# ---------------------------------------------------------------------------

_EMBED_DIM = 384


def _hash_token(token: str, dim: int) -> int:
    h = hashlib.md5(token.encode("utf-8")).digest()
    return int.from_bytes(h[:4], "little") % dim


def hash_embed(texts: Iterable[str], dim: int = _EMBED_DIM) -> np.ndarray:
    """Bag-of-hashed-tokens with L2 normalization. Deterministic, dependency-free."""
    out = []
    for text in texts:
        vec = np.zeros(dim, dtype=np.float32)
        for tok in re.findall(r"[a-zA-Z_]{2,}", (text or "").lower()):
            idx = _hash_token(tok, dim)
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        out.append(vec)
    if not out:
        return np.zeros((0, dim), dtype=np.float32)
    return np.vstack(out).astype(np.float32)


__all__ = ["compose_answer", "hash_embed", "truncate"]
