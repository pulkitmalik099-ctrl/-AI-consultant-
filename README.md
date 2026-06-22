# AI Consultant Knowledge Copilot

> RAG-powered copilot for Benefits Administration consultants — instant, cited answers from BRDs, benefit specs, and Zendesk tickets.

---

## Overview

Knowledge is scattered across BRDs, benefit specifications, look & feel specs, email specs, and Zendesk tickets. Consultants waste time searching. This copilot indexes all approved documents and lets consultants ask questions in plain English — with every answer linked back to the source document.

```
BRDs / Specs / Zendesk Tickets
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
   (RAG + conversation)
         │
         ▼
  FastAPI Copilot API
   (chat · summarize · cite)
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
# Open .env and add your OPENAI_API_KEY

# 4. Add documents
#    → PDF, DOCX, TXT  →  data/documents/
#    → Zendesk CSV     →  data/zendesk/

# 5. Start the API
uvicorn src.api.main:app --reload
```

API is now live at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## Supported Document Types

| Format | Location |
|--------|----------|
| PDF (.pdf) | `data/documents/` |
| Word (.docx) | `data/documents/` |
| Text (.txt) | `data/documents/` |
| Zendesk export (.csv) | `data/zendesk/` |

---

## API Reference

### Health

```
GET /health
```

### Ingest Documents

Index all documents from `data/documents/` and `data/zendesk/`.  
Call this once on startup and whenever documents change.

```
POST /ingest
```

```json
{
  "status": "ok",
  "documents_loaded": 12,
  "chunks_created": 340
}
```

### List Indexed Documents

```
GET /documents
```

```json
{
  "documents": [
    "data/documents/UK_BRD_2024.pdf",
    "data/documents/Dental_Benefit_Spec.docx",
    "zendesk://ticket/10045"
  ]
}
```

### Chat (Multi-turn)

```
POST /chat
```

```json
{
  "question": "What are the eligibility rules for the dental plan in the UK?",
  "session_id": "consultant-alice"
}
```

Response:

```json
{
  "answer": "Based on the UK Dental Benefit Specification, employees are eligible after 3 months of employment...",
  "sources": ["data/documents/UK_Dental_Spec.pdf"],
  "session_id": "consultant-alice"
}
```

`session_id` is optional (defaults to `"default"`). Reuse the same ID to maintain conversation context across follow-up questions.

### Summarize a Document

```
POST /summarize
```

```json
{
  "source": "BRD"
}
```

```json
{
  "summary": "## UK Benefits BRD Summary\n\n**Purpose:** ...\n\n**Key Requirements:** ...",
  "source": "BRD",
  "chunks_used": 8
}
```

### Clear Conversation History

```
DELETE /sessions/{session_id}
```

---

## Project Structure

```
ai-knowledge-copilot/
├── .env.example               ← copy to .env, add API key
├── requirements.txt
├── data/
│   ├── documents/             ← drop BRDs, specs, TXT files here
│   └── zendesk/               ← drop Zendesk CSV exports here
├── src/
│   ├── ingestion/
│   │   ├── loader.py          ← loads + chunks PDF/DOCX/TXT
│   │   └── zendesk.py         ← loads Zendesk CSV exports
│   ├── retrieval/
│   │   └── vector_store.py    ← FAISS in-memory index
│   ├── rag/
│   │   ├── pipeline.py        ← RAG chain (ask + summarize)
│   │   └── memory.py          ← per-session conversation history
│   └── api/
│       └── main.py            ← FastAPI app
└── tests/
    └── test_rag.py
```

---

## Zendesk CSV Format

Export tickets from Zendesk → **Reports → Export**. The loader expects these columns (extras are ignored):

| Column | Description |
|--------|-------------|
| `id` | Ticket ID |
| `subject` | Ticket subject |
| `description` | Ticket body |
| `status` | open / pending / solved |

---

## Phase Roadmap

- [x] **Phase 1** — Ingestion: PDF/DOCX/TXT loading, chunking, FAISS index
- [x] **Phase 2** — RAG Core: Multi-turn chat, summarization, Zendesk indexing, source citations
- [ ] **Phase 3** — Governance: Analytics dashboard, document versioning, enterprise rollout

---

## Security Notes

- Never commit `.env` (it's in `.gitignore`)
- API keys via environment variables only
- PII/PHI: avoid indexing documents containing personal employee health data
- Add auth (OAuth / API key middleware) before any production deployment
