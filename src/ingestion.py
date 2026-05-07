"""Markdown ingestion: header-aware chunking, embedding, FAISS index build.

Index is cached in data/index/ keyed on a content hash so repeated runs do not
re-embed unchanged sources. Falls back to a hashing-based embedder if a
sentence-transformer model is not available locally.
"""
from __future__ import annotations

import json
import pickle
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from . import config
from .mock_llm import hash_embed
from .utils import clean_text, estimate_tokens, file_hash, logger

# faiss is imported lazily so module import succeeds even if not installed yet.
try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


@dataclass
class Chunk:
    chunk_id: str
    source: str
    section: str
    text: str
    n_tokens: int


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_H2 = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _split_by_h2(md: str) -> list[tuple[str, str]]:
    """Split a markdown document into (section_title, body) pairs by H2.

    Content before the first H2 is returned with section title 'Overview'.
    """
    md = clean_text(md)
    if not md:
        return []
    matches = list(_H2.finditer(md))
    if not matches:
        return [("Overview", md)]
    sections: list[tuple[str, str]] = []
    first = matches[0]
    if first.start() > 0:
        head = md[: first.start()].strip()
        if head:
            head_lines = [l for l in head.splitlines() if not l.startswith("#")]
            head_body = "\n".join(head_lines).strip()
            if head_body:
                sections.append(("Overview", head_body))
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(md)
        body = md[start:end].strip()
        if body:
            sections.append((title, body))
    return sections


def _window_split(body: str, target_tokens: int, overlap_tokens: int) -> list[str]:
    """Split a section body into ~target_tokens chunks with overlap.

    Splits on paragraph first; if a single paragraph exceeds the budget, splits
    by sentence so we never exceed the target by more than ~30%.
    """
    target_chars = target_tokens * 4
    overlap_chars = overlap_tokens * 4
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    pieces: list[str] = []
    buf = ""
    for para in paragraphs:
        candidate = (buf + "\n\n" + para).strip() if buf else para
        if len(candidate) <= target_chars:
            buf = candidate
            continue
        if buf:
            pieces.append(buf)
        if len(para) <= target_chars:
            buf = para
        else:
            # paragraph itself is huge — split on sentence boundaries
            sents = re.split(r"(?<=[.!?])\s+", para)
            sub = ""
            for s in sents:
                cand = (sub + " " + s).strip() if sub else s
                if len(cand) <= target_chars:
                    sub = cand
                else:
                    if sub:
                        pieces.append(sub)
                    sub = s
            buf = sub
    if buf:
        pieces.append(buf)

    if overlap_chars <= 0 or len(pieces) <= 1:
        return pieces
    overlapped: list[str] = [pieces[0]]
    for prev, cur in zip(pieces, pieces[1:]):
        tail = prev[-overlap_chars:]
        overlapped.append((tail + "\n" + cur).strip())
    return overlapped


def chunk_document(path: Path) -> list[Chunk]:
    md = path.read_text(encoding="utf-8")
    sections = _split_by_h2(md)
    fh = file_hash(path)
    chunks: list[Chunk] = []
    ordinal = 0
    for section_title, body in sections:
        for piece in _window_split(body, config.CHUNK_TOKENS, config.CHUNK_OVERLAP):
            chunks.append(
                Chunk(
                    chunk_id=f"{fh}-{ordinal:03d}",
                    source=path.name,
                    section=section_title,
                    text=piece,
                    n_tokens=estimate_tokens(piece),
                )
            )
            ordinal += 1
    return chunks


def chunk_corpus(kb_dir: Path | None = None) -> list[Chunk]:
    kb_dir = kb_dir or config.KB_DIR
    files = sorted(kb_dir.glob("*.md"))
    out: list[Chunk] = []
    for f in files:
        out.extend(chunk_document(f))
    return out


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------

_st_model = None
_st_failed = False


def _load_st_model():
    global _st_model, _st_failed
    if _st_model is not None or _st_failed:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore

        _st_model = SentenceTransformer(config.EMBEDDING_MODEL)
        logger.info("Loaded embedding model: %s", config.EMBEDDING_MODEL)
    except Exception as exc:  # noqa: BLE001
        _st_failed = True
        logger.warning(
            "sentence-transformers unavailable (%s); falling back to hashing embedder.",
            exc,
        )
    return _st_model


def embed_texts(texts: list[str]) -> tuple[np.ndarray, str]:
    """Return (matrix, embedder_name). Falls back to hash embedder."""
    if not texts:
        return np.zeros((0, 384), dtype=np.float32), "hash"
    model = _load_st_model()
    if model is not None:
        try:
            mat = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
            return np.asarray(mat, dtype=np.float32), config.EMBEDDING_MODEL
        except Exception as exc:  # noqa: BLE001
            logger.warning("Embedding failed (%s); using hash fallback.", exc)
    return hash_embed(texts), "hash"


# ---------------------------------------------------------------------------
# Index build / load
# ---------------------------------------------------------------------------


def _corpus_signature(kb_dir: Path) -> str:
    parts = []
    for f in sorted(kb_dir.glob("*.md")):
        parts.append(f"{f.name}:{file_hash(f)}")
    return "|".join(parts)


def _index_paths() -> tuple[Path, Path, Path]:
    return (
        config.INDEX_DIR / "faiss.index",
        config.INDEX_DIR / "chunks.pkl",
        config.INDEX_DIR / "manifest.json",
    )


def build_or_load_index(force: bool = False) -> dict:
    """Return {'index', 'chunks', 'embedder', 'signature'}.

    Rebuilds when the corpus signature changes or `force=True`.
    """
    if faiss is None:
        raise RuntimeError("faiss is not installed. Add faiss-cpu to your environment.")

    index_path, chunks_path, manifest_path = _index_paths()
    sig = _corpus_signature(config.KB_DIR)

    if (
        not force
        and index_path.exists()
        and chunks_path.exists()
        and manifest_path.exists()
    ):
        manifest = json.loads(manifest_path.read_text())
        if manifest.get("signature") == sig:
            with chunks_path.open("rb") as f:
                chunks = pickle.load(f)
            index = faiss.read_index(str(index_path))
            return {
                "index": index,
                "chunks": chunks,
                "embedder": manifest.get("embedder", "unknown"),
                "signature": sig,
                "built": False,
            }

    chunks = chunk_corpus()
    if not chunks:
        raise RuntimeError(f"No markdown documents found in {config.KB_DIR}")
    matrix, embedder = embed_texts([c.text for c in chunks])
    dim = matrix.shape[1]
    index = faiss.IndexFlatIP(dim)
    if matrix.shape[0] > 0:
        index.add(matrix)

    faiss.write_index(index, str(index_path))
    with chunks_path.open("wb") as f:
        pickle.dump(chunks, f)
    manifest_path.write_text(
        json.dumps(
            {
                "signature": sig,
                "embedder": embedder,
                "n_chunks": len(chunks),
                "dim": dim,
            },
            indent=2,
        )
    )
    logger.info(
        "Built index: %d chunks across %d files using %s",
        len(chunks),
        len(set(c.source for c in chunks)),
        embedder,
    )
    return {
        "index": index,
        "chunks": chunks,
        "embedder": embedder,
        "signature": sig,
        "built": True,
    }


def chunk_to_dict(c: Chunk) -> dict:
    return asdict(c)
