"""Shared utilities: JSON IO, hashing, text cleaning, lightweight logging."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger("soc_copilot")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def clean_text(text: str) -> str:
    """Light normalization for chunk text. Idempotent and safe on empty input."""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token). Avoids a tokenizer dependency."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def keyword_match_count(text: str, keywords: list[str]) -> int:
    if not text or not keywords:
        return 0
    haystack = text.lower()
    return sum(1 for kw in keywords if kw.lower() in haystack)


def truncate(text: str, max_chars: int = 280) -> str:
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"
