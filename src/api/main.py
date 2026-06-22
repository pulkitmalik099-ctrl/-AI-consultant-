from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.loader import load_documents, chunk_documents
from src.ingestion.models import TicketSource, TicketProvider, TicketMode
from src.retrieval.vector_store import build_store, get_indexed_docs
from src.rag.pipeline import ask, summarize
from src.rag.memory import clear_session, list_sessions

app = FastAPI(
    title="AI Consultant Knowledge Copilot",
    description="RAG-powered copilot for Benefits Administration consultants.",
    version="0.3.0",
)


class IngestRequest(BaseModel):
    ticket_sources: Optional[list[TicketSource]] = None
    """
    Which ticket providers and modes to include. Examples:

    All offline (default — reads CSVs from data/zendesk/ and data/jira/):
        ticket_sources: null

    Skip tickets entirely:
        ticket_sources: []

    Zendesk offline + Jira online:
        ticket_sources: [
          {"provider": "zendesk", "mode": "offline"},
          {
            "provider": "jira",
            "mode": "online",
            "jira_config": {
              "server_url": "https://company.atlassian.net",
              "username": "admin@company.com",
              "api_token": "xxx",
              "project_key": "BEN"
            }
          }
        ]

    Both providers online (credentials from env vars if config omitted):
        ticket_sources: [
          {"provider": "zendesk", "mode": "online"},
          {"provider": "jira",    "mode": "online"}
        ]
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


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.3.0"}


@app.post("/ingest")
def ingest(request: IngestRequest = IngestRequest()):
    """Index documents and tickets.

    - Drop Zendesk CSV exports in data/zendesk/
    - Drop Jira CSV exports in data/jira/
    - For online mode, pass credentials in ticket_sources or set env vars.
    """
    try:
        docs = load_documents(ticket_sources=request.ticket_sources)
    except Exception as exc:
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

    return {
        "status": "ok",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks),
        "ticket_sources": providers_used,
    }


@app.get("/documents")
def documents():
    return {"documents": get_indexed_docs()}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    try:
        return ask(request.question, session_id=request.session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/summarize")
def summarize_doc(request: SummarizeRequest):
    try:
        return summarize(request.source)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/sessions")
def sessions():
    return {"sessions": list_sessions()}


@app.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    clear_session(session_id)
    return {"status": "ok", "session_id": session_id}
