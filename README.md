# AI Consultant Knowledge Copilot

> RAG-powered copilot for Benefits Administration consultants — instant, cited answers from BRDs, benefit specs, and Zendesk / Jira tickets.

---

## Overview

Knowledge is scattered across BRDs, benefit specs, look & feel specs, email specs, and support tickets. This copilot indexes all approved documents and lets consultants ask questions in plain English — with every answer streaming in real time and linked back to the source document.

```
BRDs · Specs · Zendesk · Jira
          │
          ▼
    AI Indexing Layer
    (chunking + embeddings)
          │
          ▼
   FAISS Vector Store
    (in-memory search)
          │
          ▼
  GPT-4o + LangChain
  (RAG + streaming + memory)
          │
          ▼
  FastAPI + Chat UI
  (stream · cite · upload)
```

---

## Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11 + FastAPI |
| LLM | OpenAI GPT-4o |
| Embeddings | text-embedding-3-small |
| Vector Store | FAISS (in-memory) |
| Orchestration | LangChain (LCEL) |
| Frontend | Vanilla HTML/CSS/JS (served by FastAPI) |
| CI/CD | GitHub Actions |

---

## Quick Start

### Prerequisites

- Python 3.11+
- OpenAI API key

### Setup

```bash
# 1. Clone
git clone https://github.com/pulkitmalik099-ctrl/-AI-consultant-.git
cd -AI-consultant-

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env
# Open .env → add OPENAI_API_KEY (required)
#             → set API_KEY to protect endpoints (optional)

# 4. Start the server
uvicorn src.api.main:app --reload

# 5. Open the chat UI
# → http://localhost:8000
```

---

## Adding Documents

| Document type | Where to place |
|---------------|----------------|
| PDF / DOCX / TXT | `data/documents/` |
| Zendesk CSV export | `data/zendesk/` |
| Jira CSV export | `data/jira/` |

After adding files, click **Index All Documents** in the sidebar, or call `POST /ingest`.

You can also **upload** documents directly from the chat UI sidebar.

---

## API Reference

### Core

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/` | No | Chat UI |
| `GET` | `/health` | No | Status + indexed doc count |
| `POST` | `/ingest` | Yes | Index documents and tickets |
| `GET` | `/documents` | Yes | List indexed sources |

### Chat

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/chat` | Yes | Single-turn Q&A (JSON) |
| `GET` | `/chat/stream?question=…&session_id=…` | Key in query | Streaming SSE chat |
| `POST` | `/summarize` | Yes | Summarize a document |

### Sessions

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/sessions` | Yes | List active sessions |
| `DELETE` | `/sessions/{id}` | Yes | Clear session history |

### Documents

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/upload` | Yes | Upload + index a document |

### Governance

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `GET` | `/analytics` | Yes | Query counts, latency, top sources |
| `GET` | `/audit-log?limit=100` | Yes | Raw JSONL audit trail |

**Auth:** Set `X-API-Key: <your-key>` header, or `?api_key=<key>` for SSE. Set `API_KEY=` in `.env` to enable; leave blank for dev mode (no auth).

---

### Ingest with ticket provider selection

```bash
# Offline only (default — reads CSVs)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{}'

# Zendesk offline + Jira online (credentials in .env)
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_sources": [
      {"provider": "zendesk", "mode": "offline"},
      {"provider": "jira",    "mode": "online"}
    ]
  }'

# Jira online with explicit credentials
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "ticket_sources": [{
      "provider": "jira",
      "mode": "online",
      "jira_config": {
        "server_url": "https://company.atlassian.net",
        "username": "admin@company.com",
        "api_token": "xxx",
        "project_key": "BEN"
      }
    }]
  }'
```

---

## Supported Ticket CSV Formats

### Zendesk

Export from **Reporting → Export**. Required columns:

| Column | Description |
|--------|-------------|
| `id` | Ticket ID |
| `subject` | Subject line |
| `description` | Ticket body |
| `status` | open / pending / solved |

### Jira

Export from **Issues → Export to CSV**. Required columns:

| Column | Description |
|--------|-------------|
| `Issue key` | e.g. BEN-42 |
| `Summary` | Issue title |
| `Description` | Issue body |
| `Status` | Open / In Progress / Done |
| `Issue Type` | Story / Bug / Task |

---

## Project Structure

```
ai-knowledge-copilot/
├── .env.example
├── .github/workflows/ci.yml     ← GitHub Actions CI
├── pyproject.toml               ← pytest config
├── requirements.txt
├── data/
│   ├── documents/               ← PDF, DOCX, TXT files
│   ├── zendesk/                 ← Zendesk CSV exports
│   └── jira/                    ← Jira CSV exports
├── logs/
│   └── audit.jsonl              ← auto-created on first query
├── src/
│   ├── ingestion/
│   │   ├── loader.py            ← document + ticket orchestrator
│   │   ├── tickets.py           ← offline CSV loaders
│   │   ├── models.py            ← TicketSource, TicketMode, etc.
│   │   └── online/
│   │       ├── zendesk_api.py   ← live Zendesk API fetcher
│   │       └── jira_api.py      ← live Jira API fetcher
│   ├── retrieval/
│   │   └── vector_store.py      ← FAISS index
│   ├── rag/
│   │   ├── pipeline.py          ← ask() + ask_stream() + summarize()
│   │   └── memory.py            ← per-session conversation history
│   ├── analytics/
│   │   ├── logger.py            ← JSONL audit trail
│   │   └── metrics.py           ← aggregated stats
│   ├── static/
│   │   └── index.html           ← chat UI
│   └── api/
│       ├── auth.py              ← API key middleware
│       ├── upload.py            ← file upload endpoint
│       └── main.py              ← FastAPI app
└── tests/
    └── test_rag.py
```

---

## Phase Roadmap

- [x] **Phase 1** — Ingestion: PDF/DOCX/TXT loading, chunking, FAISS index
- [x] **Phase 2** — RAG Core: Multi-turn chat, summarization, Zendesk + Jira indexing, source citations
- [x] **Phase 3** — Governance: Audit logging, analytics dashboard, API key auth
- [x] **Phase 4** — Complete: Streaming responses, file upload, chat UI, CI/CD

---

## Security Notes

- Never commit `.env` — it is in `.gitignore`
- API keys via environment variables only
- PII/PHI: avoid indexing documents containing personal employee health data
- Add OAuth / SSO before production deployment
- FAISS index is in-memory — restarting the server requires re-ingesting documents
