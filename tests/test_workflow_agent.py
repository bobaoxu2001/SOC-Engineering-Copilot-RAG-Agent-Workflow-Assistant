"""Smoke tests for the multi-step triage agent."""
from __future__ import annotations

from pathlib import Path

from src import config
from src.agent_workflows import triage


def _read_log(name: str) -> str:
    return (config.LOGS_DIR / name).read_text(encoding="utf-8")


def test_classifies_missing_include_as_build():
    result = triage(_read_log("build_error_01.txt"))
    assert result.issue_category == "build"
    assert result.suggested_owner_team == "CAD/Methodology"
    assert "include" in result.likely_root_cause.lower()
    assert result.generated_ticket_summary.startswith("[BUILD")


def test_classifies_makefile_dependency_as_build():
    result = triage(_read_log("build_error_02.txt"))
    assert result.issue_category == "build"
    assert result.suggested_owner_team == "CAD/Methodology"
    assert result.human_review_required is False or result.confidence < config.CONFIDENCE_HUMAN_REVIEW


def test_classifies_lint_warning_as_lint():
    result = triage(_read_log("lint_warning_01.txt"))
    assert result.issue_category == "lint"
    assert result.suggested_owner_team == "Methodology"
    assert result.severity == "low"


def test_assertion_failure_triggers_human_review():
    result = triage(_read_log("verification_failure_01.txt"))
    assert result.issue_category in ("verification", "cdc_reset")
    assert result.human_review_required is True


def test_empty_input_routes_to_human_review():
    result = triage("")
    assert result.issue_category == "unknown"
    assert result.human_review_required is True


def test_triage_output_is_json_serializable():
    import json

    result = triage("Error: cannot open include file 'foo.svh'")
    json.dumps(result.to_dict())  # must not raise
