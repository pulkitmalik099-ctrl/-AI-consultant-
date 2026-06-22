import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from src.ingestion.loader import chunk_documents
from src.retrieval.vector_store import add_to_store
from src.api.auth import require_api_key

DOCS_DIR = Path(__file__).parents[2] / "data" / "documents"
SUPPORTED = {".pdf", ".docx", ".txt"}

router = APIRouter()
_auth = Depends(require_api_key)


@router.post("/upload", dependencies=[_auth])
async def upload_document(file: UploadFile = File(...)):
    """Upload a document and index it immediately into the vector store."""
    suffix = Path(file.filename).suffix.lower()
    if suffix not in SUPPORTED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported type '{suffix}'. Accepted: {', '.join(SUPPORTED)}",
        )

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    dest = DOCS_DIR / file.filename

    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    from src.ingestion.loader import _LOADERS
    docs = _LOADERS[suffix](str(dest)).load()
    chunks = chunk_documents(docs)

    indexed = False
    try:
        add_to_store(chunks)
        indexed = True
    except Exception:
        pass  # store not yet built — file is saved, run /ingest to index

    return {
        "status": "ok",
        "filename": file.filename,
        "chunks_created": len(chunks),
        "indexed": indexed,
        "note": None if indexed else "Run POST /ingest to index this file.",
    }
