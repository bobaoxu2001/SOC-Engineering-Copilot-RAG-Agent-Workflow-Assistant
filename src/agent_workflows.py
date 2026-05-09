"""Multi-step triage agent for build / verification / lint logs.

Pipeline:
    1. classify_issue        — keyword + regex rules
    2. retrieve_context      — pull relevant playbook chunks (RAG)
    3. hypothesize_root_cause — pattern-driven explanation
    4. recommend_next_steps   — extract checklist items from retrieved chunks
    5. decide_escalation      — owner-team + human-review gating
    6. generate_ticket        — compact summary

The pipeline is deterministic so it works without an LLM key. If a key is
present, the rag layer can post-edit the explanation, but the structured
fields and routing are always rule-driven for reliability.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from . import config
from .retrieval import retrieve
from .utils import truncate


# ---------------------------------------------------------------------------
# Step 1 — classification
# ---------------------------------------------------------------------------

CDC_RESET_PATTERNS = [
    r"\bCDC\b",
    r"clock[- ]?domain",
    r"two[- ]?flop\s+sync",
    r"reset\s+(deassertion|ordering|sync)",
    r"metastab",
    r"async(hronous)?\s+(reset|signal|crossing)",
]

VERIFICATION_PATTERNS = [
    r"UVM_(ERROR|FATAL)",
    r"ASSERT_FAIL",
    r"assertion[_ ]failure",
    r"scoreboard",
    r"\btestbench\b",
    r"\bregress(ion)?\b.*(FAIL|fail)",
    r"\bseed\s*[:=]",
]

LINT_PATTERNS = [
    r"^\s*WARNING\s*\[",
    r"\blint\b",
    r"blocking[_ ]in[_ ]seq",
    r"uninitialized[_ ]signal",
    r"PASS_WITH_WARNINGS",
]

BUILD_PATTERNS = [
    r"cannot open include file",
    r"No rule to make target",
    r"^\s*make:\s*\*\*\*",
    r"\[compile\]\s*FAILED",
    r"\bSyntax error\b",
    r"undefined reference",
]


def _matches_any(text: str, patterns: list[str]) -> int:
    return sum(1 for p in patterns if re.search(p, text, flags=re.IGNORECASE | re.MULTILINE))


def classify_issue(log_text: str) -> tuple[str, dict]:
    """Return (category, scores). Categories: build | verification | lint | cdc_reset | unknown."""
    scores = {
        "build": _matches_any(log_text, BUILD_PATTERNS),
        "verification": _matches_any(log_text, VERIFICATION_PATTERNS),
        "lint": _matches_any(log_text, LINT_PATTERNS),
        "cdc_reset": _matches_any(log_text, CDC_RESET_PATTERNS),
    }
    if scores["cdc_reset"] >= 1 and scores["verification"] >= 1:
        return "cdc_reset", scores
    if max(scores.values()) == 0:
        return "unknown", scores
    category = max(scores, key=lambda k: scores[k])
    return category, scores


# ---------------------------------------------------------------------------
# Step 2 — retrieval
# ---------------------------------------------------------------------------

CATEGORY_TO_SOURCES: dict[str, list[str]] = {
    "build": ["build_flow_makefile_notes.md"],
    "verification": ["verification_debug_playbook.md", "systemverilog_notes.md"],
    "lint": ["systemverilog_notes.md", "rtl_design_basics.md"],
    "cdc_reset": ["clock_reset_cdc_notes.md", "verification_debug_playbook.md", "soc_integration_checklist.md"],
    "unknown": [],
}


def retrieve_context(category: str, log_text: str, top_k: int = 4) -> list[dict]:
    sources = CATEGORY_TO_SOURCES.get(category, [])
    items = retrieve(log_text, top_k=top_k, source_filter=sources or None)
    return [it.to_dict() for it in items]


# ---------------------------------------------------------------------------
# Step 3 — root-cause hypothesis
# ---------------------------------------------------------------------------

ROOT_CAUSE_TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "build": [
        (r"cannot open include file", "Compiler could not resolve an include file. Likely an `+incdir+` is missing or the file list is stale."),
        (r"No rule to make target", "Make has no recipe for the requested target. Likely cause: an environment variable (for example SIM_DIR) is unset or a prerequisite path is wrong."),
        (r"Syntax error", "Compile-time syntax error. Confirm the failing file compiles standalone and check recent edits."),
    ],
    "verification": [
        (r"ASSERT_FAIL", "A concurrent or immediate assertion fired. Determine whether the assertion itself is correct, then whether the design or the stimulus is at fault."),
        (r"scoreboard", "Score-board mismatch between observed and expected. Check the reference model and recent design changes."),
        (r"TIMEOUT", "Test ran past its time budget. Possible hang in the design or a stuck handshake."),
    ],
    "lint": [
        (r"blocking[_ ]in[_ ]seq", "Blocking assignment used inside an always_ff block. Replace with non-blocking assignment for sequential logic."),
        (r"uninitialized[_ ]signal", "A signal is read before assignment on some path. Add a default or a reset branch."),
    ],
    "cdc_reset": [
        (r"reset\s+(deassertion|ordering)", "Reset deassertion ordering or synchronization issue across domains. High-risk; requires hardware-engineer review."),
        (r"two[- ]?flop", "Multi-bit signal crossing without an approved CDC structure. High-risk; requires hardware-engineer review."),
        (r"metastab", "Metastability risk on a CDC path. High-risk; requires hardware-engineer review."),
    ],
}

GENERIC_ROOT_CAUSE = {
    "build": "Build-stage failure. Triage with the build-flow notes; usually a path, file-list, or environment issue.",
    "verification": "Verification failure. Categorize against the regression-failure taxonomy and reproduce locally before changing RTL.",
    "lint": "Static-checker finding. Treat as methodology cleanup unless escalated.",
    "cdc_reset": "Clock-domain or reset finding. High-risk; escalate for hardware-engineer review.",
    "unknown": "Could not determine the issue category from the log. Manual triage required.",
}


def hypothesize_root_cause(category: str, log_text: str) -> str:
    for pattern, msg in ROOT_CAUSE_TEMPLATES.get(category, []):
        if re.search(pattern, log_text, flags=re.IGNORECASE | re.MULTILINE):
            return msg
    return GENERIC_ROOT_CAUSE[category]


# ---------------------------------------------------------------------------
# Step 4 — recommended next steps
# ---------------------------------------------------------------------------

DEFAULT_NEXT_STEPS: dict[str, list[str]] = {
    "build": [
        "Confirm the failing file or target name and search the workspace for it.",
        "Re-source the project setup script to refresh tool and path variables.",
        "Run `make -n <target>` to print the planned commands without executing.",
        "If the dependency graph is confused, run `make distclean` and rebuild.",
    ],
    "verification": [
        "Reproduce the failure locally with the same seed and configuration.",
        "Open the waveform around the failure cycle and walk backward to first symptom.",
        "Check `git log` against the testbench, RTL, and shared libraries since last green run.",
        "Confirm the testbench configuration (plus-args, reference model, exclusions).",
    ],
    "lint": [
        "Apply the recommended construct (for example `<=` for sequential logic).",
        "Add a reset branch or default assignment for any uninitialized signal.",
        "Re-run the linter and confirm the warning is gone before merging.",
    ],
    "cdc_reset": [
        "Do not modify RTL until a hardware engineer has reviewed the path.",
        "Capture the CDC tool report and the failing waveform for the reviewer.",
        "Confirm whether the path is a known waiver or a new finding.",
        "Open a ticket and tag the design owner for the involved clock domains.",
    ],
    "unknown": [
        "Re-run the failing job to rule out infrastructure flakiness.",
        "Capture the full log and route to the methodology team for routing.",
    ],
}


def recommend_next_steps(category: str, retrieved: list[dict]) -> list[str]:
    steps = list(DEFAULT_NEXT_STEPS[category])
    # Pull bulleted lines from retrieved chunks to pad the suggestion list.
    extra: list[str] = []
    for chunk in retrieved[:2]:
        for line in (chunk.get("text") or "").splitlines():
            line = line.strip()
            if line.startswith("- ") and len(line) > 4:
                cleaned = line[2:].strip().rstrip(".")
                if cleaned and cleaned not in steps and cleaned not in extra:
                    extra.append(truncate(cleaned, 160))
            if len(extra) >= 3:
                break
        if len(extra) >= 3:
            break
    return steps + [f"From `{retrieved[i]['source']}`: {e}" for i, e in enumerate(extra) if i < len(retrieved)]


# ---------------------------------------------------------------------------
# Step 5 — escalation / human review
# ---------------------------------------------------------------------------

SEVERITY_BY_CATEGORY = {
    "build": "medium",
    "verification": "high",
    "lint": "low",
    "cdc_reset": "high",
    "unknown": "medium",
}


ASSERTION_PATTERNS = [r"ASSERT_FAIL", r"assertion[_ ]failure", r"UVM_FATAL"]


def _is_assertion_failure(log_text: str) -> bool:
    return any(re.search(p, log_text, flags=re.IGNORECASE) for p in ASSERTION_PATTERNS)


def decide_escalation(
    category: str, scores: dict, retrieved: list[dict], log_text: str = ""
) -> tuple[str, bool, float]:
    """Return (owner, human_review_required, confidence).

    Escalation policy:
      - Always escalate `cdc_reset` and `unknown`.
      - Always escalate `verification` cases that contain assertion failures
        (high-risk per the verification playbook).
      - Otherwise escalate only when the classifier itself is uncertain (top
        rule score < 2). Low retrieval similarity alone is not enough to
        escalate a clear-signal log — this avoids over-escalating routine
        build / lint findings.
    """
    owner = config.OWNER_TEAMS[category]
    sig = max(scores.values()) if scores else 0
    retrieval_strength = (
        sum(c.get("score", 0.0) for c in retrieved[:3]) / max(1, len(retrieved[:3]))
        if retrieved
        else 0.0
    )
    classifier_component = min(sig / 3.0, 1.0)
    confidence = 0.55 * classifier_component + 0.45 * retrieval_strength
    if sig >= 2:
        confidence = max(confidence, 0.60)
    confidence = float(max(0.0, min(1.0, confidence)))

    if category in ("cdc_reset", "unknown"):
        return owner, True, confidence
    if category == "verification" and _is_assertion_failure(log_text):
        return owner, True, confidence
    classifier_uncertain = sig < 2
    return owner, classifier_uncertain, confidence


# ---------------------------------------------------------------------------
# Step 6 — ticket summary
# ---------------------------------------------------------------------------


def generate_ticket(
    category: str,
    severity: str,
    root_cause: str,
    owner: str,
    human_review: bool,
) -> str:
    review_tag = " — human review required" if human_review else ""
    return (
        f"[{category.upper()} / severity: {severity}] {root_cause} "
        f"Routing to {owner}{review_tag}."
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


@dataclass
class TriageResult:
    issue_category: str
    severity: str
    likely_root_cause: str
    related_knowledge_sources: list[str]
    recommended_next_steps: list[str]
    suggested_owner_team: str
    confidence: float
    human_review_required: bool
    generated_ticket_summary: str
    classifier_scores: dict = field(default_factory=dict)
    retrieved_chunks: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def triage(log_text: str) -> TriageResult:
    if not log_text or not log_text.strip():
        return TriageResult(
            issue_category="unknown",
            severity="medium",
            likely_root_cause="Empty input.",
            related_knowledge_sources=[],
            recommended_next_steps=["Provide a log snippet to triage."],
            suggested_owner_team=config.OWNER_TEAMS["unknown"],
            confidence=0.0,
            human_review_required=True,
            generated_ticket_summary="[UNKNOWN / severity: medium] Empty input. Routing to Human Review.",
            classifier_scores={},
            retrieved_chunks=[],
        )

    category, scores = classify_issue(log_text)
    retrieved = retrieve_context(category, log_text, top_k=4)
    root_cause = hypothesize_root_cause(category, log_text)
    next_steps = recommend_next_steps(category, retrieved)
    owner, human_review, confidence = decide_escalation(category, scores, retrieved, log_text)
    severity = SEVERITY_BY_CATEGORY[category]
    sources = sorted({c["source"] for c in retrieved})
    ticket = generate_ticket(category, severity, root_cause, owner, human_review)

    return TriageResult(
        issue_category=category,
        severity=severity,
        likely_root_cause=root_cause,
        related_knowledge_sources=sources,
        recommended_next_steps=next_steps,
        suggested_owner_team=owner,
        confidence=round(confidence, 3),
        human_review_required=bool(human_review),
        generated_ticket_summary=ticket,
        classifier_scores=scores,
        retrieved_chunks=retrieved,
    )
