"""Top-k retrieval over the FAISS index built by ingestion.py."""
from __future__ import annotations

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

    def to_dict(self) -> dict:
        d = chunk_to_dict(self.chunk)
        d.update(
            {"rank": self.rank, "score": float(self.score), "likely_relevant": self.likely_relevant}
        )
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
