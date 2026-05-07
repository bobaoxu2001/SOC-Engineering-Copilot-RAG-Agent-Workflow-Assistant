# Screenshots

This folder holds screenshots of the four main tabs of the SOC Engineering Copilot Streamlit UI.

## How to capture

1. Start the app: `streamlit run app.py`
2. Open `http://localhost:8501` in a browser.
3. For each tab below, perform the action described, then take a screenshot (⌘+Shift+4 on macOS, or your browser's built-in screenshot tool).
4. Save images here with the filenames listed below.

---

### 01_ask_copilot.png

**Tab:** Ask Copilot

**Action:** Type the example question:
> "What are common CDC risks during SOC integration?"

Then click **Ask Copilot**.

**What to capture:** The full tab view showing the answer (with bullet points), the confidence badge (amber/red for this high-risk topic), the "Human review required" callout, and the citation row.

---

### 02_retrieval_inspector.png

**Tab:** Retrieval Inspector

**Action:** Type the query:
> "reset synchronization deassertion"

Set top-k to 5, then click **Search index**.

**What to capture:** The results table with rank, score, source, section, and "likely_relevant" columns visible. Expand "Full chunk text" if space allows.

---

### 03_triage_agent.png

**Tab:** Workflow Triage Agent

**Action:** Select `verification_failure_01.txt` from the sample log dropdown, then click **Run triage agent**.

**What to capture:** The four metric cards (Category · Severity · Owner team · Confidence), the "Human review required" callout, the full pipeline trace (six labeled steps), and the structured JSON output.

---

### 04_evaluation_dashboard.png

**Tab:** Evaluation Dashboard

**Action:** Click **Run evaluation**.

**What to capture:** All metric cards for both QA and Workflow sections, the topic distribution bar chart, and the per-question results table.

---

## Reference dimensions

Export at 1280×900 or larger for clean rendering in the README.
