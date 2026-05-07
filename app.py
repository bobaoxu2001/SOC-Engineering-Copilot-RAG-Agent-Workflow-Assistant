"""SOC Engineering Copilot — Streamlit application.

Four tabs, each surfacing one specific capability:
  1. Ask Copilot (RAG)            — cited LLM answers with confidence + human-review gating
  2. Retrieval Inspector          — transparent top-k retrieval with scores
  3. Workflow Triage Agent        — multi-step deterministic agent over build/verify logs
  4. Evaluation Dashboard         — retrieval and agent quality metrics

Designed to look like a serious internal AI tool, not a classroom chatbot.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src import config
from src.agent_workflows import triage
from src.evaluation import evaluate_qa, evaluate_workflows, save_eval_results
from src.rag_pipeline import answer
from src.retrieval import index_status, rebuild_index, retrieve, retrieved_summary

st.set_page_config(
    page_title="SOC Engineering Copilot",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

ACCENT = "#76B900"
SURFACE = "#FAFAF7"
BORDER = "#E5E5E5"
MUTED = "#6B7280"

CUSTOM_CSS = f"""
<style>
    .block-container {{ padding-top: 1.5rem; padding-bottom: 3rem; }}

    .copilot-hero {{
        background: linear-gradient(180deg, #FFFFFF 0%, {SURFACE} 100%);
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.25rem;
    }}
    .copilot-hero h1 {{
        font-size: 1.5rem; margin: 0 0 0.25rem 0; color: #111827;
        letter-spacing: -0.01em;
    }}
    .copilot-hero p {{ margin: 0; color: {MUTED}; font-size: 0.95rem; }}

    .tag-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.75rem; }}
    .tag {{
        font-size: 0.72rem; padding: 0.18rem 0.55rem; border-radius: 999px;
        background: #F3F4F6; color: #374151; border: 1px solid {BORDER};
        letter-spacing: 0.02em;
    }}
    .tag-accent {{ background: rgba(118,185,0,0.10); color: {ACCENT}; border-color: rgba(118,185,0,0.30); }}

    .metric-card {{
        background: #FFFFFF; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 0.85rem 1rem;
    }}
    .metric-card .label {{ color: {MUTED}; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; }}
    .metric-card .value {{ font-size: 1.5rem; font-weight: 600; color: #111827; margin-top: 0.25rem; }}

    .confidence-pill {{
        display: inline-block; padding: 0.18rem 0.6rem; border-radius: 999px;
        font-size: 0.78rem; font-weight: 600; letter-spacing: 0.02em;
    }}
    .conf-high {{ background: rgba(118,185,0,0.12); color: {ACCENT}; }}
    .conf-mid  {{ background: rgba(251,191,36,0.15); color: #B45309; }}
    .conf-low  {{ background: rgba(239,68,68,0.12); color: #B91C1C; }}

    .review-callout {{
        background: #FFFBEB; border: 1px solid #FDE68A; color: #92400E;
        border-radius: 8px; padding: 0.6rem 0.9rem; margin: 0.5rem 0;
        font-size: 0.9rem;
    }}

    .citation {{
        display: inline-block; font-family: ui-monospace, SFMono-Regular, monospace;
        font-size: 0.78rem; padding: 0.15rem 0.5rem; margin: 0.15rem 0.3rem 0.15rem 0;
        background: #F9FAFB; border: 1px solid {BORDER}; border-radius: 6px;
        color: #374151;
    }}

    .pipeline-step {{
        border-left: 3px solid {ACCENT}; padding: 0.25rem 0 0.25rem 0.75rem;
        margin: 0.4rem 0; font-size: 0.88rem; color: #374151;
    }}

    .stTabs [data-baseweb="tab-list"] {{ gap: 0.5rem; }}
    .stTabs [data-baseweb="tab"] {{
        padding: 0.5rem 1rem; border-radius: 8px 8px 0 0;
        background: transparent; border: 1px solid transparent;
    }}
    .stTabs [aria-selected="true"] {{
        background: #FFFFFF; border: 1px solid {BORDER}; border-bottom: 1px solid #FFFFFF;
        font-weight: 600;
    }}

    .stButton button[kind="primary"] {{
        background: {ACCENT}; color: white; border: 1px solid {ACCENT};
        font-weight: 600;
    }}
    .stButton button[kind="primary"]:hover {{ background: #5E9700; border-color: #5E9700; }}

    .footer-note {{
        color: {MUTED}; font-size: 0.78rem; margin-top: 2rem; text-align: center;
        border-top: 1px solid {BORDER}; padding-top: 1rem;
    }}
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def confidence_pill(confidence: float) -> str:
    if confidence >= 0.70:
        cls = "conf-high"
        label = f"High confidence · {confidence:.2f}"
    elif confidence >= config.CONFIDENCE_HUMAN_REVIEW:
        cls = "conf-mid"
        label = f"Medium confidence · {confidence:.2f}"
    else:
        cls = "conf-low"
        label = f"Low confidence · {confidence:.2f}"
    return f'<span class="confidence-pill {cls}">{label}</span>'


def metric_card(label: str, value: str) -> str:
    return f'<div class="metric-card"><div class="label">{label}</div><div class="value">{value}</div></div>'


def render_hero(title: str, subtitle: str, tags: list[tuple[str, bool]]):
    tag_html = "".join(
        f'<span class="tag {"tag-accent" if accent else ""}">{t}</span>'
        for t, accent in tags
    )
    st.markdown(
        f"""
        <div class="copilot-hero">
            <h1>{title}</h1>
            <p>{subtitle}</p>
            <div class="tag-row">{tag_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


with st.sidebar:
    st.markdown("### SOC Engineering Copilot")
    st.caption("Internal AI tooling prototype")
    st.markdown("---")
    try:
        status = index_status()
        st.markdown("**Index status**")
        st.markdown(
            metric_card("Chunks", str(status["n_chunks"])),
            unsafe_allow_html=True,
        )
        st.markdown(
            metric_card("Sources", str(status["n_sources"])),
            unsafe_allow_html=True,
        )
        st.caption(f"Embedder: `{status['embedder']}`")
    except Exception as exc:  # noqa: BLE001
        st.error(f"Index not ready: {exc}")
    st.markdown("---")
    st.markdown("**LLM mode**")
    st.caption(config.llm_mode_label())
    if st.button("Rebuild index", use_container_width=True):
        with st.spinner("Re-embedding knowledge base..."):
            rebuild_index()
        st.success("Index rebuilt.")
        st.rerun()
    st.markdown("---")
    st.caption(
        "All knowledge content in this prototype is synthetic and public-safe. "
        "It is general engineering guidance, not a sign-off authority."
    )


# ---------------------------------------------------------------------------
# Top hero + tabs
# ---------------------------------------------------------------------------

render_hero(
    "SOC Engineering Copilot",
    "RAG + agent-workflow assistant for hardware/SOC engineering productivity. "
    "Cited answers, transparent retrieval, deterministic triage, and evaluation reliability.",
    [
        ("RAG", True),
        ("Agent Orchestration", True),
        ("Evaluation", True),
        ("Internal Tool", False),
        ("Public-safe synthetic KB", False),
    ],
)

tab_ask, tab_retr, tab_triage, tab_eval = st.tabs(
    ["Ask Copilot", "Retrieval Inspector", "Workflow Triage", "Evaluation Dashboard"]
)


# ---------------------------------------------------------------------------
# Tab 1 — Ask Copilot
# ---------------------------------------------------------------------------

EXAMPLES = [
    "What should I check before integrating a new IP block into an SOC?",
    "Why is non-blocking assignment recommended in sequential logic?",
    "How should I triage a missing include file error in a build?",
    "What are common CDC risks during SOC integration?",
    "How should reset synchronization be reviewed?",
]

with tab_ask:
    st.markdown(
        "**Capability:** Retrieval-Augmented Generation over the local engineering knowledge base. "
        "Every answer is grounded in cited sources; high-risk topics (CDC, reset, integration, "
        "assertion failures) always trigger human-review gating."
    )

    if "ask_query" not in st.session_state:
        st.session_state.ask_query = ""

    st.markdown("**Example questions**")
    cols = st.columns(len(EXAMPLES))
    for i, ex in enumerate(EXAMPLES):
        if cols[i].button(ex, key=f"ex_{i}", use_container_width=True):
            st.session_state.ask_query = ex

    query = st.text_area(
        "Your question",
        value=st.session_state.ask_query,
        height=80,
        placeholder="Ask about RTL, SOC integration, build flow, verification, or CDC...",
    )
    run = st.button("Ask Copilot", type="primary")

    if run and query.strip():
        with st.spinner("Retrieving context and composing answer..."):
            resp = answer(query.strip())

        left, right = st.columns([2, 1])
        with left:
            st.markdown("#### Answer")
            st.markdown(resp.answer)
            st.markdown(
                "**Citations**<br>"
                + "".join(f'<span class="citation">{c}</span>' for c in resp.citations),
                unsafe_allow_html=True,
            )

        with right:
            st.markdown("#### Reliability signals")
            st.markdown(confidence_pill(resp.confidence), unsafe_allow_html=True)
            if resp.human_review_required:
                reason = (
                    "high-risk topic (CDC / reset / integration / assertion)"
                    if resp.high_risk_topic
                    else "low retrieval confidence"
                )
                st.markdown(
                    f'<div class="review-callout"><strong>Human review required</strong> — {reason}. '
                    f"Treat this answer as general guidance and confirm with a hardware engineer.</div>",
                    unsafe_allow_html=True,
                )
            st.caption(
                f"Mode: {'mock LLM' if resp.used_mock else 'live LLM'} · "
                f"top-k chunks: {len(resp.chunks)}"
            )

        with st.expander("Retrieved chunks (transparency)", expanded=False):
            for c in resp.chunks:
                st.markdown(
                    f"**`{c['source']}` › {c['section']}** &nbsp; score: `{c['score']:.3f}` &nbsp; rank: `{c['rank']}`",
                    unsafe_allow_html=True,
                )
                st.markdown(f"> {c['text']}")
                st.markdown("---")


# ---------------------------------------------------------------------------
# Tab 2 — Retrieval Inspector
# ---------------------------------------------------------------------------

with tab_retr:
    st.markdown(
        "**Capability:** Retrieval transparency. Inspect chunking, embedding, and similarity-scored "
        "top-k results — the raw substrate that the RAG layer builds on."
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        ri_query = st.text_input("Query", value="What is a two-flop synchronizer used for?")
    with c2:
        top_k = st.slider("top-k", 1, 10, 5)
    if st.button("Search index", type="primary"):
        with st.spinner("Searching FAISS index..."):
            items = retrieve(ri_query, top_k=top_k)
            rows = retrieved_summary(items)
        if not rows:
            st.warning("No results.")
        else:
            df = pd.DataFrame(
                [
                    {
                        "rank": r["rank"],
                        "score": round(r["score"], 4),
                        "source": r["source"],
                        "section": r["section"],
                        "likely_relevant": r["likely_relevant"],
                        "snippet": r["snippet"],
                    }
                    for r in rows
                ]
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            with st.expander("Full chunk text", expanded=False):
                for r in rows:
                    st.markdown(
                        f"**`{r['source']}` › {r['section']}** · score `{r['score']:.3f}` · rank `{r['rank']}`"
                    )
                    st.markdown(f"> {r['text']}")
                    st.markdown("---")


# ---------------------------------------------------------------------------
# Tab 3 — Workflow Triage Agent
# ---------------------------------------------------------------------------


def _load_sample_logs() -> dict[str, str]:
    out: dict[str, str] = {}
    for f in sorted(config.LOGS_DIR.glob("*.txt")):
        out[f.name] = f.read_text(encoding="utf-8")
    return out


with tab_triage:
    st.markdown(
        "**Capability:** Multi-step agent orchestration. The agent classifies the issue, retrieves "
        "playbook context, hypothesizes a root cause, recommends next steps, decides escalation, "
        "and drafts a ticket — all deterministic so it runs reliably without an LLM key."
    )

    samples = _load_sample_logs()
    sample_choice = st.selectbox(
        "Pick a sample log (or paste your own below)",
        options=["— none —"] + list(samples.keys()),
    )
    default_text = samples.get(sample_choice, "") if sample_choice != "— none —" else ""
    log_text = st.text_area(
        "Log snippet",
        value=default_text,
        height=220,
        placeholder="Paste a build / verification / lint log here...",
    )

    if st.button("Run triage agent", type="primary") and log_text.strip():
        with st.spinner("Running 6-step triage pipeline..."):
            result = triage(log_text)

        c1, c2, c3, c4 = st.columns(4)
        c1.markdown(metric_card("Category", result.issue_category), unsafe_allow_html=True)
        c2.markdown(metric_card("Severity", result.severity), unsafe_allow_html=True)
        c3.markdown(metric_card("Owner team", result.suggested_owner_team), unsafe_allow_html=True)
        c4.markdown(metric_card("Confidence", f"{result.confidence:.2f}"), unsafe_allow_html=True)

        if result.human_review_required:
            st.markdown(
                '<div class="review-callout"><strong>Human review required.</strong> '
                "This category is high-risk or the agent is not confident enough to auto-route. "
                "A qualified engineer must review.</div>",
                unsafe_allow_html=True,
            )

        st.markdown("#### Pipeline trace")
        steps = [
            f"<b>1. Classify</b> → <code>{result.issue_category}</code> "
            f"(scores: {result.classifier_scores})",
            f"<b>2. Retrieve</b> → {len(result.retrieved_chunks)} chunks from "
            f"{', '.join(f'<code>{s}</code>' for s in result.related_knowledge_sources) or 'no source'}",
            f"<b>3. Hypothesize root cause</b> → {result.likely_root_cause}",
            f"<b>4. Recommend next steps</b> → {len(result.recommended_next_steps)} steps",
            f"<b>5. Decide escalation</b> → owner: <code>{result.suggested_owner_team}</code>; "
            f"human review: <code>{result.human_review_required}</code>",
            f"<b>6. Generate ticket</b> → <em>{result.generated_ticket_summary}</em>",
        ]
        for s in steps:
            st.markdown(f'<div class="pipeline-step">{s}</div>', unsafe_allow_html=True)

        left, right = st.columns(2)
        with left:
            st.markdown("#### Recommended next steps")
            for step in result.recommended_next_steps:
                st.markdown(f"- {step}")
        with right:
            st.markdown("#### Generated ticket summary")
            st.code(result.generated_ticket_summary, language="text")
            st.markdown("#### Structured output (JSON)")
            structured = {
                k: v for k, v in result.to_dict().items() if k != "retrieved_chunks"
            }
            st.json(structured)

        with st.expander("Retrieved knowledge chunks", expanded=False):
            for c in result.retrieved_chunks:
                st.markdown(
                    f"**`{c['source']}` › {c['section']}** · score `{c['score']:.3f}`"
                )
                st.markdown(f"> {c['text']}")
                st.markdown("---")


# ---------------------------------------------------------------------------
# Tab 4 — Evaluation Dashboard
# ---------------------------------------------------------------------------

with tab_eval:
    st.markdown(
        "**Capability:** Evaluation reliability. Quantitative retrieval and agent-quality metrics "
        "computed over a held-out evaluation set, including a custom **Grounded Answer Rate / "
        "Citation Faithfulness** metric and an **Out-of-scope handling accuracy** metric that "
        "measures whether the system correctly refuses sign-off and proprietary-data requests."
    )

    run_eval = st.button("Run evaluation", type="primary")
    if run_eval:
        with st.spinner("Running QA + workflow evaluation..."):
            qa = evaluate_qa()
            wf = evaluate_workflows()
            saved_path = save_eval_results(qa, wf)
        st.success(f"Evaluation complete. Results saved to `{saved_path.relative_to(config.REPO_ROOT)}`.")

        st.markdown(f"### QA Retrieval & Answer Quality  ·  {qa.n_regular} in-scope · {qa.n_out_of_scope} safety/OOS")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.markdown(metric_card("Hit rate @ k", f"{qa.hit_rate*100:.1f}%"), unsafe_allow_html=True)
        c2.markdown(metric_card("MRR", f"{qa.mrr:.3f}"), unsafe_allow_html=True)
        c3.markdown(metric_card("Citation coverage", f"{qa.citation_coverage*100:.1f}%"), unsafe_allow_html=True)
        c4.markdown(metric_card("Grounded Answer Rate", f"{qa.grounded_answer_rate*100:.1f}%"), unsafe_allow_html=True)
        c5.markdown(metric_card("High-risk routing", f"{qa.high_risk_routing_accuracy*100:.1f}%"), unsafe_allow_html=True)
        c6, c7, c8, c9 = st.columns(4)
        c6.markdown(metric_card("Avg top-1 score", f"{qa.avg_top_score:.3f}"), unsafe_allow_html=True)
        c7.markdown(metric_card("Avg top-k score", f"{qa.avg_topk_score:.3f}"), unsafe_allow_html=True)
        c8.markdown(metric_card("Missing-context rate", f"{qa.missing_context_rate*100:.1f}%"), unsafe_allow_html=True)
        c9.markdown(metric_card("Out-of-scope accuracy", f"{qa.out_of_scope_handling_accuracy*100:.1f}%"), unsafe_allow_html=True)

        qa_df = pd.DataFrame(qa.items)
        st.markdown("**Per-question results**")
        display_cols = [
            "id", "topic", "is_out_of_scope", "hit", "answer_grounded",
            "out_of_scope_handled", "reciprocal_rank", "top_score",
            "keyword_hits", "expect_human_review", "actual_human_review", "high_risk_correct",
        ]
        st.dataframe(qa_df[display_cols], use_container_width=True, hide_index=True)

        st.markdown("**Topic distribution**")
        topic_counts = qa_df.groupby("topic").size().reset_index(name="count")
        st.bar_chart(topic_counts.set_index("topic"))

        failures = qa_df[~qa_df["hit"]]
        if not failures.empty:
            st.markdown("**Retrieval misses**")
            st.dataframe(
                failures[["id", "question", "expected_sources", "retrieved_sources"]],
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("---")
        st.markdown("### Workflow Triage Quality")
        d1, d2, d3, d4 = st.columns(4)
        d1.markdown(metric_card("Category accuracy", f"{wf.category_accuracy*100:.1f}%"), unsafe_allow_html=True)
        d2.markdown(metric_card("Owner accuracy", f"{wf.owner_accuracy*100:.1f}%"), unsafe_allow_html=True)
        d3.markdown(metric_card("Escalation accuracy", f"{wf.escalation_accuracy*100:.1f}%"), unsafe_allow_html=True)
        d4.markdown(metric_card("Human-review rate", f"{wf.human_review_rate*100:.1f}%"), unsafe_allow_html=True)

        d5, d6 = st.columns(2)
        d5.markdown(metric_card("Avg confidence (correct)", f"{wf.avg_confidence_correct:.2f}"), unsafe_allow_html=True)
        d6.markdown(metric_card("Avg confidence (incorrect)", f"{wf.avg_confidence_incorrect:.2f}"), unsafe_allow_html=True)

        wf_df = pd.DataFrame(wf.items)
        st.markdown("**Per-case results**")
        st.dataframe(wf_df, use_container_width=True, hide_index=True)

        wf_fail = wf_df[~wf_df["category_correct"]]
        if not wf_fail.empty:
            st.markdown("**Classification misses**")
            st.dataframe(wf_fail, use_container_width=True, hide_index=True)
    else:
        st.info("Click **Run evaluation** to compute retrieval and triage metrics over the held-out eval sets.")


st.markdown(
    '<div class="footer-note">Prototype for AI-assisted hardware engineering productivity. '
    "Synthetic public-safe knowledge base. Not a sign-off authority. "
    "Final hardware decisions require human engineering review.</div>",
    unsafe_allow_html=True,
)
