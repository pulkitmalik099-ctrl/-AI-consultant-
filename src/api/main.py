from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

from src.ingestion.loader import load_documents, chunk_documents
from src.ingestion.tickets import TicketProvider
from src.retrieval.vector_store import build_store, get_indexed_docs
from src.rag.pipeline import ask, summarize
from src.rag.memory import clear_session, list_sessions

app = FastAPI(
    title="AI Consultant Knowledge Copilot",
    description="RAG-powered copilot for Benefits Administration consultants.",
    version="0.2.0",
)


class IngestRequest(BaseModel):
    ticket_providers: Optional[list[TicketProvider]] = None
    """Which ticketing systems to include. null = all, [] = none."""


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
    return {"status": "ok", "version": "0.2.0"}


@app.post("/ingest")
def ingest(request: IngestRequest = IngestRequest()):
    """Index documents and tickets.

    - ticket_providers: ["zendesk"], ["jira"], ["zendesk","jira"], or omit for all.
    - Place Zendesk CSVs in data/zendesk/ and Jira CSVs in data/jira/.
    """
    docs = load_documents(ticket_providers=request.ticket_providers)
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
    return {
        "status": "ok",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks),
        "ticket_providers": request.ticket_providers or [p.value for p in TicketProvider],
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
