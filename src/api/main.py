from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.loader import load_documents, chunk_documents
from src.ingestion.models import TicketSource, TicketProvider, TicketMode
from src.retrieval.vector_store import build_store, get_indexed_docs
from src.rag.pipeline import ask, summarize
from src.rag.memory import clear_session, list_sessions
from src.analytics.logger import log_ingest, log_error, read_log
from src.analytics.metrics import get_metrics
from src.api.auth import require_api_key

app = FastAPI(
    title="AI Consultant Knowledge Copilot",
    description="RAG-powered copilot for Benefits Administration consultants.",
    version="0.3.0",
)

_auth = Depends(require_api_key)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    ticket_sources: Optional[list[TicketSource]] = None
    """
    Which ticket providers and modes to include. Examples:

    All offline — reads CSVs from data/zendesk/ and data/jira/ (default):
        ticket_sources: null

    Zendesk offline + Jira online with explicit credentials:
        ticket_sources: [
          {"provider": "zendesk", "mode": "offline"},
          {"provider": "jira", "mode": "online",
           "jira_config": {"server_url": "https://co.atlassian.net",
                           "username": "admin@co.com", "api_token": "xxx"}}
        ]

    Both providers online — credentials from env vars:
        ticket_sources: [
          {"provider": "zendesk", "mode": "online"},
          {"provider": "jira",    "mode": "online"}
        ]

    Skip tickets entirely:
        ticket_sources: []
    """


class ChatRequest(BaseModel):
    question: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    answer: str
    sources: list[str]
    session_id: str


class SummarizeRequest(BaseModel):
    source: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {
        "status": "ok",
        "version": "0.3.0",
        "indexed_documents": len(get_indexed_docs()),
    }


@app.post("/ingest", dependencies=[_auth])
def ingest(request: IngestRequest = IngestRequest()):
    """Index documents and tickets. Requires API key if API_KEY env var is set."""
    try:
        docs = load_documents(ticket_sources=request.ticket_sources)
    except Exception as exc:
        log_error("ingest", str(exc))
        raise HTTPException(status_code=502, detail=f"Failed to load tickets: {exc}")

    if not docs:
        raise HTTPException(
            status_code=404,
            detail=(
                "No documents found. "
                "Add PDF/DOCX/TXT to data/documents/, "
                "Zendesk CSV to data/zendesk/, "
                "or Jira CSV to data/jira/."
            ),
        )

    chunks = chunk_documents(docs)
    build_store(chunks)

    providers_used = (
        "all offline"
        if request.ticket_sources is None
        else [f"{s.provider.value}:{s.mode.value}" for s in request.ticket_sources]
    )

    log_ingest(len(docs), len(chunks), providers_used)

    return {
        "status": "ok",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks),
        "ticket_sources": providers_used,
    }


@app.get("/documents", dependencies=[_auth])
def documents():
    return {"documents": get_indexed_docs()}


@app.post("/chat", response_model=ChatResponse, dependencies=[_auth])
def chat(request: ChatRequest):
    try:
        return ask(request.question, session_id=request.session_id)
    except RuntimeError as exc:
        log_error("chat", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/summarize", dependencies=[_auth])
def summarize_doc(request: SummarizeRequest):
    try:
        return summarize(request.source)
    except RuntimeError as exc:
        log_error("summarize", str(exc))
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/sessions", dependencies=[_auth])
def sessions():
    return {"sessions": list_sessions()}


@app.delete("/sessions/{session_id}", dependencies=[_auth])
def delete_session(session_id: str):
    clear_session(session_id)
    return {"status": "ok", "session_id": session_id}


@app.get("/analytics", dependencies=[_auth])
def analytics():
    """Usage metrics: query counts, latency, top sources, active sessions."""
    return get_metrics()


@app.get("/audit-log", dependencies=[_auth])
def audit_log(limit: int = 100):
    """Raw audit log entries (newest last). Max 500 per call."""
    return {"records": read_log(limit=min(limit, 500))}
