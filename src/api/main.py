from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from src.ingestion.loader import load_documents, chunk_documents
from src.retrieval.vector_store import build_store
from src.rag.pipeline import ask

app = FastAPI(
    title="AI Consultant Knowledge Copilot",
    description="RAG-powered copilot for Benefits Administration consultants.",
    version="0.1.0",
)


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str
    sources: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest():
    docs = load_documents()
    if not docs:
        raise HTTPException(
            status_code=404,
            detail="No documents found in data/documents/. Add PDF, DOCX, or TXT files and retry.",
        )
    chunks = chunk_documents(docs)
    build_store(chunks)
    return {
        "status": "ok",
        "documents_loaded": len(docs),
        "chunks_created": len(chunks),
    }


@app.post("/chat", response_model=AnswerResponse)
def chat(request: QuestionRequest):
    try:
        return ask(request.question)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
