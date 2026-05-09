"""End-to-end RAG: retrieve → build prompt → generate (live or mock) → cite.

Confidence and human-review gating are computed deterministically from
retrieval signals plus a high-risk topic check, so behavior is reproducible
even when the live LLM is in the loop.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional

from . import config
from .mock_llm import compose_answer
from .retrieval import Retrieved, retrieve
from .utils import logger


SYSTEM_PROMPT = (
    "You are the SOC Engineering Copilot, an internal assistant for hardware "
    "engineers. Answer using only the numbered context blocks below. Cite the "
    "source filename for every claim using the form [source.md › Section]. If "
    "the context is insufficient, say so plainly. For high-risk topics — "
    "clock-domain crossing, reset synchronization, integration sign-off, or "
    "assertion failures — phrase the answer as general guidance and remind the "
    "reader that a hardware engineer must review. Never claim this material "
    "is proprietary, and never present yourself as a sign-off authority."
)


@dataclass
class RAGResponse:
    query: str
    answer: str
    citations: list[str]
    chunks: list[dict]
    confidence: float
    human_review_required: bool
    high_risk_topic: bool
    used_mock: bool
    embedder: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _topic_is_high_risk(query: str) -> bool:
    q = (query or "").lower()
    return any(t in q for t in config.HIGH_RISK_TOPICS)


def _compute_confidence(items: list[Retrieved]) -> float:
    if not items:
        return 0.0
    top = [i.score for i in items[:3]]
    base = sum(top) / len(top)
    # Add a small bonus for clear separation between rank-1 and rank-k.
    gap = items[0].score - items[-1].score if len(items) > 1 else 0.0
    return float(max(0.0, min(1.0, 0.65 * base + 0.35 * (base + gap / 2))))


def _build_prompt(query: str, items: list[Retrieved]) -> list[dict]:
    blocks = []
    for it in items:
        c = it.chunk
        header = f"[{c.source} › {c.section}] (score={it.score:.3f})"
        blocks.append(f"{header}\n{c.text}")
    context = "\n\n".join(blocks) if blocks else "(no context retrieved)"
    user = (
        f"Question: {query}\n\n"
        "Context (cite using the bracketed source labels above):\n"
        f"{context}\n\n"
        "Answer concisely. Use bullet points where helpful. Always cite. "
        "If the topic is high-risk, end with a one-line human-review reminder."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _call_live_llm(messages: list[dict]) -> Optional[str]:
    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI(api_key=config.OPENAI_API_KEY, base_url=config.OPENAI_BASE_URL)
        resp = client.chat.completions.create(
            model=config.LLM_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=600,
        )
        return resp.choices[0].message.content or ""
    except Exception as exc:  # noqa: BLE001
        logger.warning("Live LLM call failed (%s); falling back to mock.", exc)
        return None


def answer(query: str, top_k: Optional[int] = None) -> RAGResponse:
    items = retrieve(query, top_k=top_k)
    chunk_dicts = [it.to_dict() for it in items]
    citations = []
    seen = set()
    for it in items:
        label = f"{it.chunk.source} › {it.chunk.section}" if it.chunk.section else it.chunk.source
        if label not in seen:
            citations.append(label)
            seen.add(label)

    high_risk = _topic_is_high_risk(query)
    confidence = _compute_confidence(items)
    human_review = high_risk or confidence < config.CONFIDENCE_HUMAN_REVIEW or len(items) == 0

    used_mock = config.use_mock_llm()
    text: Optional[str] = None
    if not used_mock:
        text = _call_live_llm(_build_prompt(query, items))
        if text is None:
            used_mock = True
    if used_mock:
        text = compose_answer(query, [it.to_dict() for it in items])

    if high_risk and "human" not in (text or "").lower():
        text = (text or "").rstrip() + (
            "\n\n**Human review required.** This topic is high-risk; treat the "
            "above as general guidance and confirm with the relevant hardware, "
            "design, integration, or verification owner before making decisions."
        )

    embedder = ""
    try:
        from .retrieval import index_status

        embedder = index_status()["embedder"]
    except Exception:
        pass

    return RAGResponse(
        query=query,
        answer=text or "",
        citations=citations,
        chunks=chunk_dicts,
        confidence=confidence,
        human_review_required=bool(human_review),
        high_risk_topic=bool(high_risk),
        used_mock=bool(used_mock),
        embedder=embedder,
    )
