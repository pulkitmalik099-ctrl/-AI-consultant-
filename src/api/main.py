import json
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.loader import load_documents, chunk_documents
from src.ingestion.models import TicketSource
from src.retrieval.vector_store import build_store, get_indexed_docs
from src.rag.pipeline import ask, ask_stream, summarize
from src.rag.memory import clear_session, list_sessions
from src.analytics.logger import log_ingest, log_error, read_log
from src.analytics.metrics import get_metrics
from src.api.auth import require_api_key
from src.api.upload import router as upload_router

STATIC_DIR = Path(__file__).parent.parent / "static"

app = FastAPI(
    title="AI Consultant Knowledge Copilot",
    description="RAG-powered copilot for Benefits Administration consultants.",
    version="0.4.0",
)

app.include_router(upload_router)
_auth = Depends(require_api_key)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class IngestRequest(BaseModel):
    ticket_sources: Optional[list[TicketSource]] = None


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
# UI
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
def serve_ui():
    return FileResponse(str(STATIC_DIR / "index.html"))


# ---------------------------------------------------------------------------
# Core API
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "version": "0.4.0", "indexed_documents": len(get_indexed_docs())}


@app.post("/ingest", dependencies=[_auth])
def ingest(request: IngestRequest = IngestRequest()):
    try:
        docs = load_documents(ticket_sources=request.ticket_sources)
    except Exception as exc:
        log_error("ingest", str(exc))
        raise HTTPException(status_code=502, detail=f"Failed to load tickets: {exc}")

    if not docs:
        raise HTTPException(
            status_code=404,
            detail="No documents found. Add files to data/documents/, data/zendesk/, or data/jira/.",
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


@app.get("/chat/stream")
async def chat_stream(question: str, session_id: str = "default", api_key: str = None):
    """Streaming chat via Server-Sent Events. API key accepted as query param for EventSource compat."""
    expected = os.getenv("API_KEY")
    if expected and api_key != expected:
        async def denied():
            yield f"data: {json.dumps({'error': 'Invalid or missing API key'})}\n\n"
        return StreamingResponse(denied(), media_type="text/event-stream")

    async def stream():
        try:
            async for payload in ask_stream(question, session_id):
                yield f"data: {payload}\n\n"
        except RuntimeError as exc:
            yield f"data: {json.dumps({'error': str(exc)})}\n\n"
        except Exception as exc:
            log_error("chat/stream", str(exc))
            yield f"data: {json.dumps({'error': f'Server error: {exc}'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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
    return get_metrics()


@app.get("/audit-log", dependencies=[_auth])
def audit_log(limit: int = 100):
    return {"records": read_log(limit=min(limit, 500))}
