"""Central configuration for the SOC Engineering Copilot.

Reads environment variables with sensible defaults so the project runs offline
out of the box. All paths are resolved relative to the repository root so the
app behaves the same regardless of working directory.
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)

REPO_ROOT: Path = Path(__file__).resolve().parent.parent
DATA_DIR: Path = REPO_ROOT / "data"
KB_DIR: Path = DATA_DIR / "knowledge_base"
EVAL_DIR: Path = DATA_DIR / "eval"
LOGS_DIR: Path = DATA_DIR / "sample_logs"
INDEX_DIR: Path = DATA_DIR / "index"

INDEX_DIR.mkdir(parents=True, exist_ok=True)

EMBEDDING_MODEL: str = os.getenv(
    "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
)
LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o-mini")
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip()
FORCE_MOCK_LLM: bool = os.getenv("FORCE_MOCK_LLM", "0").strip() not in ("0", "", "false", "False")

CHUNK_TOKENS: int = 350
CHUNK_OVERLAP: int = 50
TOP_K_DEFAULT: int = 5
RELEVANCE_THRESHOLD: float = 0.30
CONFIDENCE_HUMAN_REVIEW: float = 0.55

HIGH_RISK_TOPICS: tuple[str, ...] = (
    # Hardware technical risk topics
    "cdc",
    "clock domain",
    "clock-domain",
    "reset synchronization",
    "reset deassertion",
    "reset architecture",
    "metastability",
    "integration sign-off",
    "ip integration",
    "ip block",
    "soc integration",
    "assertion failure",
    # Sign-off, approval, and proprietary-data requests — always escalate
    "sign off",
    "sign-off",
    "sign off ",
    "approve",
    "approval",
    "tapeout",
    "tape out",
    "proprietary",
    "confidential",
    "invent the missing",
    "ignore the context",
)

OWNER_TEAMS: dict[str, str] = {
    "build": "CAD/Methodology",
    "verification": "Verification",
    "lint": "Methodology",
    "cdc_reset": "Design + Human Review",
    "timing": "Timing/STA",
    "synthesis": "Synthesis",
    "formal": "Formal Verification",
    "dft": "DFT",
    "unknown": "Human Review",
}


def use_mock_llm() -> bool:
    """Return True when the deterministic fallback should be used."""
    if FORCE_MOCK_LLM:
        return True
    return not OPENAI_API_KEY


def llm_mode_label() -> str:
    return "Mock LLM (deterministic fallback)" if use_mock_llm() else f"Live LLM: {LLM_MODEL}"
