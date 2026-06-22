import pytest
from langchain.schema import Document
from src.ingestion.loader import chunk_documents
from src.retrieval import vector_store as vs


def test_chunk_splits_large_text():
    docs = [Document(page_content="word " * 500, metadata={"source": "test.pdf"})]
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1


def test_chunk_preserves_metadata():
    docs = [Document(page_content="sample benefit information", metadata={"source": "brd.pdf"})]
    chunks = chunk_documents(docs)
    assert all(c.metadata["source"] == "brd.pdf" for c in chunks)


def test_get_store_raises_before_ingest():
    vs._store = None
    with pytest.raises(RuntimeError, match="POST /ingest first"):
        vs.get_store()
