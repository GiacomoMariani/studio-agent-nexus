//TODO Each page carries a "What this page demonstrates" footer mapping the UI to the
engineering skills behind it.
Change this into tech adopted

//todo add roadmap
//todo move quickstart in another document

# Studio Agent Nexus

**An agentic AI workflow that turns documents, production notes, and bug reports
into answers, tasks, risks, and team-ready plans. Grounded, cited, and observable.**

![Studio Agent Nexus — Board view](docs/images/board.png)

---

Studio Agent Nexus enhance management with AI tools. It ingests design documents,
bug reports, and technical specs, then uses retrieval-augmented generation and 
agentic reasoning to:

- answer questions with **grounded citations** from the uploaded documents,
- extract **prioritised, department-tagged tasks**,
- detect **risks and contradictions** across documents,
- propose the **work a plan is still missing**, and
- keep every interaction **logged, costed, and auditable**.

It connects 15+ years of tech lead, Systems, feedback loops, constraints, tooling,
and iteration, to modern agentic AI engineering. 

> An example in action: [Link]

---

## The product

A Streamlit UI over a FastAPI backend, organised as five surfaces:

- **Upload** — manage the knowledge base, ingest Markdown/PDF with chunk + status feedback.
- **Ask** — grounded Q&A with citation cards and an explicit fallback state.
- **Board** — fetch tasks from a document, review what's ready (with per-task GitHub/CI
  status), run a planning pass that surfaces missing work, and track tasks by state.
- **Risks** — surface risks and cross-document contradictions, side by side with sources.
- **Logs** — a durable audit log of every question, answer, model, and token cost.

Each page carries a "What this page demonstrates" footer mapping the UI to the
engineering skills behind it.

---

## Tech used

| Capability | What it proves | Where |
|---|---|---|
| **RAG pipeline** | Ingest → chunk → embed → hybrid retrieve → ground | `services/retrieval_service.py`, `services/chunking.py`, `services/document_ingestion_service.py` |
| **Citation grounding** | Every factual claim traced to a source doc + snippet + score | `services/document_answering_service.py` |
| **Fallback logic** | The agent declines when evidence is weak instead of inventing answers | `services/llm_document_answerer.py` |
| **Agentic reasoning** | Multi-step orchestration, not a single prompt | `services/document_answerer_factory.py`, board planning (in progress) |
| **Structured output** | Schema-validated results safe to pipe into real tools | `models/`, Pydantic throughout |
| **Provider-agnostic LLM** | Swap Gemini ↔ Groq ↔ OpenAI ↔ fake via env var; rule-based safety net | `providers/`, `services/document_answerer_factory.py` |
| **Human-in-the-loop tool use** | Pending → confirm before any side-effecting action | `services/tool_assistant_service.py`, `tools/production_tools.py` |
| **Evaluation harness** | Citation rate, fallback rate, latency tracked across runs | `services/document_qa_evaluation_service.py`, `scripts/run_document_qa_eval.py` |
| **Observability & cost** | Every query logged with tokens, estimated cost, latency, sources | `services/usage_tracking_service.py`, `services/document_query_log_store.py` |
| **Production hygiene** | Typed services, API-key auth, Docker, test suite, linting | `auth.py`, `Dockerfile`, `entrypoint.sh`, `tests/` |

---

## Architecture

```text
        Streamlit UI  (frontend/)
              │  HTTP only (X-API-Key)
              ▼
        FastAPI API   (main.py, auth.py)
              │
   ┌──────────┼───────────────────────────────┐
   ▼          ▼                                 ▼
 Ingestion  Retrieval + Answering          Observability
 (chunk,    (hybrid vector + keyword,      (query logs,
  embed,     citations, fallback,           usage + cost,
  PDF parse) rule / Gemini answerer)        evaluation)
   └──────────┴───────────────┬─────────────────┘
                              ▼
                      SQLite  (documents, chunks, jobs,
                               logs, usage, eval results)
```

Local embeddings use `sentence-transformers/all-MiniLM-L6-v2`. Retrieval combines vector
similarity with keyword overlap. The answerer is pluggable: a free Google Gemini path
(the default), an OpenAI path, or a deterministic rule-based path for safe local/demo use,
with automatic fallback to the rule path on failure or low confidence.

---

## Tech stack

Python 3.12 · FastAPI · Streamlit · SQLite (SQLAlchemy + Alembic) ·
sentence-transformers · google-genai · groq · OpenAI SDK · pypdf · pytest · Ruff · Docker

---

## Roadmap


---

## Quick start

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate   # PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt -r requirements-dev.txt

# 2. Configure
cp .env.example .env        # PowerShell: Copy-Item .env.example .env
# set at least: APP_API_KEY=dev-secret-key  and  API_BASE_URL=http://localhost:8000

# 3. Run the backend
uvicorn main:app --reload   # http://127.0.0.1:8000  · docs at /docs  · health at /health

# 4. Run the UI (second terminal)
streamlit run frontend/app.py   # http://localhost:8501
```

Or run both together in one container:

```bash
docker build -t studio-agent-nexus .
docker run -p 8000:8000 -p 8501:8501 --env-file .env studio-agent-nexus
```

---