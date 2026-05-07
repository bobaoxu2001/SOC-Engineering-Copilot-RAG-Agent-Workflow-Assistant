"""Tests for the FastAPI service layer (api.py).

Uses FastAPI's built-in TestClient so no server process is required.
All tests run with the deterministic mock LLM (FORCE_MOCK_LLM=1 or no key set).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from api import app  # local import so module-level index build happens once
    return TestClient(app)


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["n_chunks"] > 0
    assert body["n_sources"] >= 6


def test_retrieve_returns_chunks_for_known_query(client):
    resp = client.post("/retrieve", json={"query": "non-blocking assignment sequential logic", "top_k": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert body["top_k"] == 5
    assert len(body["results"]) >= 1
    sources = {c["source"] for c in body["results"]}
    assert sources & {"rtl_design_basics.md", "systemverilog_notes.md"}
    # scores should be descending
    scores = [c["score"] for c in body["results"]]
    assert scores == sorted(scores, reverse=True)


def test_retrieve_empty_query_rejected(client):
    resp = client.post("/retrieve", json={"query": ""})
    assert resp.status_code == 422  # pydantic min_length violation


def test_ask_returns_answer_and_citations(client):
    resp = client.post("/ask", json={"query": "Why is non-blocking assignment recommended?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"]
    assert isinstance(body["citations"], list)
    assert len(body["citations"]) >= 1
    assert 0.0 <= body["confidence"] <= 1.0
    assert isinstance(body["human_review_required"], bool)
    assert isinstance(body["used_mock"], bool)


def test_ask_high_risk_triggers_human_review(client):
    resp = client.post("/ask", json={"query": "How should reset synchronization be reviewed?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["human_review_required"] is True
    assert body["high_risk_topic"] is True


def test_triage_classifies_missing_include(client):
    log = 'Error-[SE] Syntax error\n  rtl/top.sv, 42\n  Error: cannot open include file "axi_pkg.svh".\n[compile] FAILED'
    resp = client.post("/triage", json={"log_text": log})
    assert resp.status_code == 200
    body = resp.json()
    assert body["issue_category"] == "build"
    assert body["suggested_owner_team"] == "CAD/Methodology"
    assert body["generated_ticket_summary"].startswith("[BUILD")


def test_triage_empty_input_rejected(client):
    resp = client.post("/triage", json={"log_text": ""})
    assert resp.status_code == 422


def test_evaluate_returns_metrics(client):
    resp = client.post("/evaluate")
    assert resp.status_code == 200
    body = resp.json()
    assert "qa" in body and "workflow" in body
    assert 0.0 <= body["qa"]["hit_rate"] <= 1.0
    assert 0.0 <= body["qa"]["out_of_scope_handling_accuracy"] <= 1.0
    assert 0.0 <= body["workflow"]["category_accuracy"] <= 1.0
