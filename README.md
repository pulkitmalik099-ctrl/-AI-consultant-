# AI Consultant Knowledge Copilot

[![CI](https://github.com/pulkitmalik099-ctrl/-AI-consultant-/actions/workflows/ci.yml/badge.svg)](https://github.com/pulkitmalik099-ctrl/-AI-consultant-/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111%2B-green)
![LangChain](https://img.shields.io/badge/LangChain-1.x-orange)

> RAG-powered AI copilot for Benefits Administration consultants — instant, cited answers from BRDs, benefit specs, and Zendesk / Jira tickets. Responses stream in real time with source document links.

---

## What It Does

Knowledge is scattered across BRDs, benefit specifications, look & feel specs, email specs, and support tickets. Consultants waste time searching. This copilot:

- Indexes all approved documents and tickets into a searchable vector store
- Answers questions in plain English, streamed in real time
- Cites the exact source document for every answer
- Maintains conversation history per session
- Logs every query for audit and analytics

---

## Architecture

```
BRDs · Benefit Specs · Zendesk · Jira
              │
              ▼
       Document Ingestion
    (PDF / DOCX / TXT / CSV)
              │
              ▼
     Chunking + Embeddings
    (text-embedding-3-small)
              │
              ▼
      FAISS Vector Store
       (in-memory index)
              │
              ▼
   GPT-4o via LangChain LCEL
   (RAG chain + session memory)
              │
              ▼
     FastAPI + Chat UI
  (streaming SSE · upload · analytics)
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+ · FastAPI |
| LLM | OpenAI GPT-4o |
| Embeddings | text-embedding-3-small |
| Vector Store | FAISS (in-memory) |
| Orchestration | LangChain 1.x (LCEL) |
| Frontend | Vanilla HTML/CSS/JS (served by FastAPI) |
| Streaming | Server-Sent Events (SSE) |
| Auth | API key middleware (optional) |
| Audit | JSONL audit log |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Python 3.11 or higher
- OpenAI API key — [get one here](https://platform.openai.com/api-keys)

### Option A — One-Click (Windows)

```
Double-click  run.bat
```

The script will:
1. Create a `.venv` virtual environment
2. Install all dependencies
3. Create `.env` from the example and open Notepad for your API key
4. Start the server and open `http://localhost:8000` in your browser

### Option B — Manual

```bash
# 1. Clone
git clone https://github.com/pulkitmalik099-ctrl/-AI-consultant-.git
cd -AI-consultant-

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
copy .env.example .env        # Windows
# cp .env.example .env        # macOS / Linux
# Open .env and set OPENAI_API_KEY=sk-...

# 5. Start the server
uvicorn src.api.main:app --reload

# 6. Open the UI
# → http://localhost:8000
```

---

## Adding Documents

Drop files into the correct folder, then click **Index All Documents** in the sidebar or call `POST /ingest`.

| Source | Folder | Format |
|--------|--------|--------|
| BRDs, specs, policy docs | `data/documents/` | `.pdf` `.docx` `.txt` |
| Zendesk ticket export | `data/zendesk/` | `.csv` |
| Jira issue export | `data/jira/` | `.csv` |

You can also **upload documents directly** from the chat UI sidebar without restarting the server.

---

## Chat UI

Open `http://localhost:8000` after starting the server.

| Feature | Description |
|---------|-------------|
| Streaming responses | Answers appear token-by-token in real time |
| Source citations | Each AI answer shows which documents were used |
| Session sidebar | Switch between multiple conversations |
| Upload zone | Drag-and-drop or click to upload a document |
| Index button | Re-index all documents in the `data/` folders |
| Quick prompts | One-click starter questions on the welcome screen |

---

## API Reference

All endpoints require `X-API-Key: <key>` if `API_KEY` is set in `.env`. Leave `API_KEY` blank for dev mode (no auth).

### System

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `GET` | `/` | — | Chat UI |
| `GET` | `/health` | — | Status + indexed document count |
| `GET` | `/docs` | — | Interactive Swagger UI |

### Ingestion

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `POST` | `/ingest` | ✓ | Index documents + tickets |
| `POST` | `/upload` | ✓ | Upload and immediately index a file |
| `GET` | `/documents` | ✓ | List all indexed sources |

### Chat

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `POST` | `/chat` | ✓ | Single-turn Q&A (JSON response) |
| `GET` | `/chat/stream?question=…&session_id=…` | `?api_key=` | Streaming SSE chat |
| `POST` | `/summarize` | ✓ | Summarize a document by name |

### Sessions

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `GET` | `/sessions` | ✓ | List active session IDs |
| `DELETE` | `/sessions/{id}` | ✓ | Clear conversation history |

### Governance

| Method | Endpoint | Auth | Description |
|--------|----------|:----:|-------------|
| `GET` | `/analytics` | ✓ | Usage metrics (queries, latency, top sources) |
| `GET` | `/audit-log?limit=100` | ✓ | Raw JSONL audit trail |

---

## Ticket Provider Examples

### Offline — load from CSV export (default)

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{}'
```

### Mixed — Zendesk offline + Jira online

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_sources": [
      {"provider": "zendesk", "mode": "offline"},
      {"provider": "jira",    "mode": "online"}
    ]
  }'
```

Jira online credentials are read from `.env` (`JIRA_SERVER_URL`, `JIRA_USERNAME`, `JIRA_API_TOKEN`).

### Jira online with explicit credentials

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_sources": [{
      "provider": "jira",
      "mode": "online",
      "jira_config": {
        "server_url": "https://yourcompany.atlassian.net",
        "username": "admin@yourcompany.com",
        "api_token": "YOUR_TOKEN",
        "project_key": "BEN"
      }
    }]
  }'
```

Works with both **Jira Cloud** (`*.atlassian.net`) and **self-hosted Jira** (IP or internal domain).

---

## Ticket CSV Formats

### Zendesk — export from Reporting → Export

| Column | Required | Description |
|--------|:--------:|-------------|
| `id` | ✓ | Ticket ID |
| `subject` | ✓ | Subject line |
| `description` | ✓ | Ticket body |
| `status` | | open / pending / solved |

### Jira — export from Issues → Export to CSV

| Column | Required | Description |
|--------|:--------:|-------------|
| `Issue key` | ✓ | e.g. BEN-42 |
| `Summary` | ✓ | Issue title |
| `Description` | ✓ | Issue body |
| `Status` | | Open / In Progress / Done |
| `Issue Type` | | Story / Bug / Task |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in the values.

| Variable | Required | Description |
|----------|:--------:|-------------|
| `OPENAI_API_KEY` | ✓ | Your OpenAI API key |
| `OPENAI_MODEL` | | LLM model (default: `gpt-4o`) |
| `EMBEDDING_MODEL` | | Embedding model (default: `text-embedding-3-small`) |
| `API_KEY` | | Set to enable endpoint authentication |
| `ZENDESK_SUBDOMAIN` | | Zendesk subdomain for online mode |
| `ZENDESK_EMAIL` | | Zendesk account email |
| `ZENDESK_API_TOKEN` | | Zendesk API token |
| `JIRA_SERVER_URL` | | Jira server URL (Cloud or self-hosted) |
| `JIRA_USERNAME` | | Jira username / email |
| `JIRA_API_TOKEN` | | Jira API token |
| `JIRA_PROJECT_KEY` | | Optional project filter |

---

## Running Tests

```bash
pytest tests/ -v
```

All 15 tests pass without an OpenAI key — tests cover ingestion, chunking, vector store, CSV loaders, and session memory.

```
tests/test_rag.py::test_chunk_splits_large_text         PASSED
tests/test_rag.py::test_chunk_preserves_metadata        PASSED
tests/test_rag.py::test_get_store_raises_before_ingest  PASSED
tests/test_rag.py::test_get_indexed_docs_empty          PASSED
tests/test_rag.py::test_ticket_mode_values              PASSED
tests/test_rag.py::test_jira_config_strips_trailing_slash PASSED
tests/test_rag.py::test_ticket_source_offline_zendesk   PASSED
tests/test_rag.py::test_load_zendesk_csv                PASSED
tests/test_rag.py::test_load_zendesk_csv_missing_columns PASSED
tests/test_rag.py::test_load_jira_csv                   PASSED
tests/test_rag.py::test_load_jira_csv_missing_columns   PASSED
tests/test_rag.py::test_load_all_zendesk_skips_missing  PASSED
tests/test_rag.py::test_load_all_jira_skips_missing     PASSED
tests/test_rag.py::test_session_history_is_isolated     PASSED
tests/test_rag.py::test_clear_session_removes_history   PASSED
15 passed in 4.65s
```

CI runs automatically on every push and pull request via GitHub Actions.

---

## Project Structure

```
ai-knowledge-copilot/
├── run.bat                          ← One-click Windows launcher
├── .env.example                     ← Copy to .env, add API key
├── requirements.txt
├── pyproject.toml                   ← pytest config
├── .github/workflows/ci.yml         ← GitHub Actions CI
│
├── data/
│   ├── documents/                   ← PDF / DOCX / TXT files
│   ├── zendesk/                     ← Zendesk CSV exports
│   └── jira/                        ← Jira CSV exports
│
├── logs/
│   └── audit.jsonl                  ← Auto-created on first query
│
├── src/
│   ├── ingestion/
│   │   ├── loader.py                ← Document + ticket orchestrator
│   │   ├── tickets.py               ← Offline CSV loaders
│   │   ├── models.py                ← TicketSource, TicketMode, configs
│   │   └── online/
│   │       ├── zendesk_api.py       ← Live Zendesk REST API fetcher
│   │       └── jira_api.py          ← Live Jira REST API fetcher
│   ├── retrieval/
│   │   └── vector_store.py          ← FAISS in-memory index
│   ├── rag/
│   │   ├── pipeline.py              ← ask() · ask_stream() · summarize()
│   │   └── memory.py                ← Per-session conversation history
│   ├── analytics/
│   │   ├── logger.py                ← Thread-safe JSONL audit trail
│   │   └── metrics.py               ← Aggregated usage stats
│   ├── static/
│   │   └── index.html               ← Chat UI (served at /)
│   └── api/
│       ├── auth.py                  ← API key middleware
│       ├── upload.py                ← File upload endpoint
│       └── main.py                  ← FastAPI app
│
└── tests/
    └── test_rag.py                  ← 15 unit tests
```

---

## Phase Roadmap

| Phase | Status | Description |
|-------|:------:|-------------|
| 1 — Ingestion | ✅ | PDF/DOCX/TXT loading, chunking, FAISS index |
| 2 — RAG Core | ✅ | Multi-turn chat, summarization, source citations, Zendesk + Jira |
| 3 — Governance | ✅ | Audit logging, analytics dashboard, API key auth |
| 4 — Complete | ✅ | Streaming SSE chat, file upload, chat UI, CI/CD |

---

## Security Notes

- `.env` is excluded from git — never commit API keys
- Set `API_KEY` in `.env` to protect all endpoints before sharing access
- FAISS index is in-memory — documents must be re-indexed after server restart
- Avoid indexing documents containing personal employee health data (PHI/PII)
- Add OAuth / SSO before production deployment
