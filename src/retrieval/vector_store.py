import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

_store: FAISS | None = None
_indexed_docs: list[str] = []


def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))


def build_store(chunks: list) -> FAISS:
    global _store, _indexed_docs
    _store = FAISS.from_documents(chunks, _embeddings())
    _indexed_docs = sorted({chunk.metadata.get("source", "unknown") for chunk in chunks})
    return _store


def add_to_store(chunks: list) -> None:
    """Add new chunks to the existing store, or build one if none exists."""
    global _store, _indexed_docs
    if _store is None:
        build_store(chunks)
    else:
        _store.add_documents(chunks)
        new_sources = {chunk.metadata.get("source", "unknown") for chunk in chunks}
        _indexed_docs = sorted(set(_indexed_docs) | new_sources)


def get_store() -> FAISS:
    if _store is None:
        raise RuntimeError("Vector store not initialized. POST /ingest first.")
    return _store


def get_indexed_docs() -> list[str]:
    return _indexed_docs


def search(query: str, k: int = 5) -> list:
    return get_store().similarity_search(query, k=k)
