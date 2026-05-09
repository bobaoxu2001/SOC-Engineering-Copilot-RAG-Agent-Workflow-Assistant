# Deployment Guide — Streamlit Community Cloud

**Live app:** https://soc-ai-copilot.streamlit.app/
**Deployed on:** Streamlit Community Cloud
**App entrypoint:** `app.py`
**Default mode:** deterministic mock LLM fallback — no `OPENAI_API_KEY` required for the public demo
**API key policy:** optional `OPENAI_API_KEY` must be configured only through Streamlit Cloud Secrets, never committed to the repository

## Quick deploy

1. Go to **https://share.streamlit.io**
2. Sign in with GitHub
3. Click **New app**
4. Fill in:
   - **Repository:** `bobaoxu2001/SOC-Engineering-Copilot-RAG-Agent-Workflow-Assistant`
   - **Branch:** `main`
   - **Main file path:** `app.py`
5. Expand **Advanced settings**:
   - **Python version:** 3.11
   - **Secrets:** leave empty for mock-LLM mode (see [Secrets](#secrets) below)
6. Click **Deploy**

Build takes ~5–10 minutes (torch + sentence-transformers download). After that the app runs fully offline with the deterministic mock LLM.

---

## App entrypoint

```
app.py          ← Streamlit four-tab UI (Ask Copilot / Retrieval Inspector / Workflow Triage / Evaluation Dashboard)
```

No `packages.txt` is needed — all dependencies are pure Python wheels with no system-level `apt` packages.

---

## Python version

Requires **Python 3.11**. Declared in `runtime.txt`:

```
python-3.11
```

---

## Secrets

The app works without any API key — it falls back automatically to the deterministic mock LLM.

| Secret | Required | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | No | Enables live LLM (OpenAI / Together / Groq / Ollama). Without it, the mock LLM is used. |
| `OPENAI_BASE_URL` | No | Override the OpenAI base URL for compatible endpoints. Default: `https://api.openai.com/v1` |
| `LLM_MODEL` | No | Chat-completion model name. Default: `gpt-4o-mini` |

**To add a secret on Streamlit Cloud:**
App menu (⋮) → **Edit secrets** → add:
```toml
OPENAI_API_KEY = "sk-..."
```
Never commit API keys to the repository.

---

## How the index is built

`data/index/` is gitignored (only `.gitkeep` is committed). On first launch Streamlit Cloud builds the FAISS index from `data/knowledge_base/` — this takes ~10–15 seconds. The index is cached for the lifetime of the container and rebuilt if the knowledge base content hash changes.

---

## Troubleshooting

### Build fails: `faiss-cpu` wheel not found
Streamlit Cloud runs Ubuntu x86_64 — pre-built `faiss-cpu` wheels exist for this platform. If the build fails, pin a specific version:
```
faiss-cpu==1.8.0
```

### `sentence-transformers` download is slow
The model `all-MiniLM-L6-v2` (~90 MB) is downloaded from HuggingFace on first app boot. This is a one-time download per container. The app uses a hash-vector embedding fallback if the download fails, so it will never crash — retrieval quality will just be lower.

### App starts but shows "Mock LLM" badge
This is expected when `OPENAI_API_KEY` is not set. The mock LLM provides deterministic, extractive answers from retrieved chunks. All four tabs work in mock mode.

### `pandas`/`numpy` binary incompatibility warning
Streamlit Cloud installs all packages from scratch, so there is no binary incompatibility. If you see warnings locally, it means your environment has mixed-version compiled extensions — upgrade them with `pip install --upgrade pandas pyarrow`.

### Evaluation Dashboard shows no charts
The charts render after clicking **Run evaluation**. Streamlit Cloud fully supports `st.dataframe` and `st.bar_chart`.

---

## Local development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py           # mock LLM, no API key required
python -m pytest -q            # 27 tests
uvicorn api:app --reload       # optional FastAPI layer on :8000
```
