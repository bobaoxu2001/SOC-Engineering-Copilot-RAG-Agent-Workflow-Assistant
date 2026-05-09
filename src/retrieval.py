"""Top-k retrieval over the FAISS index built by ingestion.py.

The default retriever remains dense FAISS search. A lightweight lexical scorer
and hybrid dense+lexical mode are included for evaluation comparisons without
adding another dependency.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from . import config
from .ingestion import Chunk, build_or_load_index, chunk_to_dict, embed_texts
from .utils import truncate


@dataclass
class Retrieved:
    rank: int
    score: float
    chunk: Chunk
    likely_relevant: bool
    dense_score: float | None = None
    lexical_score: float | None = None

    def to_dict(self) -> dict:
        d = chunk_to_dict(self.chunk)
        d.update(
            {"rank": self.rank, "score": float(self.score), "likely_relevant": self.likely_relevant}
        )
        if self.dense_score is not None:
            d["dense_score"] = float(self.dense_score)
        if self.lexical_score is not None:
            d["lexical_score"] = float(self.lexical_score)
        return d


@lru_cache(maxsize=1)
def _state():
    return build_or_load_index(force=False)


def reset_state() -> None:
    _state.cache_clear()


def rebuild_index() -> dict:
    reset_state()
    bundle = build_or_load_index(force=True)
    return bundle


_TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if len(t) > 1]


def _filter_chunks(chunks: list[Chunk], source_filter: Optional[list[str]]) -> list[tuple[int, Chunk]]:
    if not source_filter:
        return list(enumerate(chunks))
    allowed = set(source_filter)
    return [(i, c) for i, c in enumerate(chunks) if c.source in allowed]


def _normalize(values: dict[int, float]) -> dict[int, float]:
    if not values:
        return {}
    lo = min(values.values())
    hi = max(values.values())
    if math.isclose(lo, hi):
        return {k: 1.0 if v > 0 else 0.0 for k, v in values.items()}
    return {k: (v - lo) / (hi - lo) for k, v in values.items()}


def _lexical_scores(query: str, candidates: list[tuple[int, Chunk]]) -> dict[int, float]:
    """Return dependency-free BM25-like lexical scores for candidate chunks."""
    query_terms = _tokens(query)
    if not query_terms or not candidates:
        return {}

    query_counts = Counter(query_terms)
    docs = {idx: _tokens(f"{chunk.source} {chunk.section} {chunk.text}") for idx, chunk in candidates}
    n_docs = len(docs)
    avg_len = sum(len(toks) for toks in docs.values()) / max(n_docs, 1)
    doc_freq = {
        term: sum(1 for toks in docs.values() if term in toks)
        for term in query_counts
    }

    scores: dict[int, float] = {}
    k1 = 1.2
    b = 0.75
    for idx, toks in docs.items():
        counts = Counter(toks)
        doc_len = max(len(toks), 1)
        score = 0.0
        for term, q_weight in query_counts.items():
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            df = doc_freq.get(term, 0)
            idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
            denom = tf + k1 * (1 - b + b * doc_len / max(avg_len, 1))
            score += q_weight * idf * (tf * (k1 + 1) / denom)
        if score > 0:
            scores[idx] = score
    return scores


def _dense_scores(query: str, candidate_indexes: set[int], top_k: int) -> dict[int, float]:
    bundle = _state()
    index = bundle["index"]
    chunks: list[Chunk] = bundle["chunks"]
    query_vec, _ = embed_texts([query])
    if query_vec.shape[0] == 0:
        return {}

    n = min(max(top_k * 8, top_k, 20), len(chunks))
    scores, idx = index.search(query_vec, n)
    out: dict[int, float] = {}
    for score, i in zip(scores[0], idx[0]):
        if i < 0 or i not in candidate_indexes:
            continue
        out[int(i)] = float(score)
    return out


def retrieve(query: str, top_k: int | None = None, source_filter: Optional[list[str]] = None) -> list[Retrieved]:
    if not query or not query.strip():
        return []
    k = top_k or config.TOP_K_DEFAULT
    bundle = _state()
    index = bundle["index"]
    chunks: list[Chunk] = bundle["chunks"]
    if not chunks:
        return []

    query_vec, _ = embed_texts([query])
    if query_vec.shape[0] == 0:
        return []

    n = min(max(k * 3, k), len(chunks))
    scores, idx = index.search(query_vec, n)
    out: list[Retrieved] = []
    for score, i in zip(scores[0], idx[0]):
        if i < 0 or i >= len(chunks):
            continue
        chunk = chunks[i]
        if source_filter and chunk.source not in source_filter:
            continue
        out.append(
            Retrieved(
                rank=0,
                score=float(score),
                chunk=chunk,
                likely_relevant=float(score) >= config.RELEVANCE_THRESHOLD,
            )
        )
        if len(out) >= k:
            break
    for r, item in enumerate(out, start=1):
        item.rank = r
    return out


def retrieve_lexical(
    query: str, top_k: int | None = None, source_filter: Optional[list[str]] = None
) -> list[Retrieved]:
    if not query or not query.strip():
        return []
    k = top_k or config.TOP_K_DEFAULT
    chunks: list[Chunk] = _state()["chunks"]
    candidates = _filter_chunks(chunks, source_filter)
    scores = _lexical_scores(query, candidates)
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:k]
    out = [
        Retrieved(
            rank=rank,
            score=float(score),
            chunk=chunks[idx],
            likely_relevant=float(score) > 0,
            lexical_score=float(score),
        )
        for rank, (idx, score) in enumerate(ranked, start=1)
    ]
    return out


def retrieve_hybrid(
    query: str,
    top_k: int | None = None,
    source_filter: Optional[list[str]] = None,
    dense_weight: float = 0.70,
) -> list[Retrieved]:
    """Blend dense FAISS similarity with dependency-free lexical matching."""
    if not query or not query.strip():
        return []
    k = top_k or config.TOP_K_DEFAULT
    chunks: list[Chunk] = _state()["chunks"]
    candidates = _filter_chunks(chunks, source_filter)
    candidate_indexes = {idx for idx, _ in candidates}

    dense_raw = _dense_scores(query, candidate_indexes, top_k=max(k, config.TOP_K_DEFAULT))
    lexical_raw = _lexical_scores(query, candidates)
    dense_norm = _normalize(dense_raw)
    lexical_norm = _normalize(lexical_raw)
    lexical_weight = 1.0 - dense_weight

    indexes = set(dense_norm) | set(lexical_norm)
    scored = []
    for idx in indexes:
        score = dense_weight * dense_norm.get(idx, 0.0) + lexical_weight * lexical_norm.get(idx, 0.0)
        scored.append((idx, score))
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)[:k]
    return [
        Retrieved(
            rank=rank,
            score=float(score),
            chunk=chunks[idx],
            likely_relevant=float(score) >= config.RELEVANCE_THRESHOLD,
            dense_score=dense_raw.get(idx, 0.0),
            lexical_score=lexical_raw.get(idx, 0.0),
        )
        for rank, (idx, score) in enumerate(ranked, start=1)
    ]


def compare_retrieval_methods(query: str, top_k: int | None = None) -> dict[str, list[dict]]:
    """Return dense and hybrid retrieval results for transparent side-by-side review."""
    k = top_k or config.TOP_K_DEFAULT
    return {
        "dense": retrieved_summary(retrieve(query, top_k=k)),
        "hybrid": retrieved_summary(retrieve_hybrid(query, top_k=k)),
    }


def retrieved_summary(items: list[Retrieved]) -> list[dict]:
    out = []
    for item in items:
        d = item.to_dict()
        d["snippet"] = truncate(d["text"], 240)
        out.append(d)
    return out


def index_status() -> dict:
    bundle = _state()
    chunks = bundle["chunks"]
    sources = sorted({c.source for c in chunks})
    return {
        "n_chunks": len(chunks),
        "n_sources": len(sources),
        "sources": sources,
        "embedder": bundle["embedder"],
    }
