import os
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

_store: FAISS | None = None


def _embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small"))


def build_store(chunks: list) -> FAISS:
    global _store
    _store = FAISS.from_documents(chunks, _embeddings())
    return _store


def get_store() -> FAISS:
    if _store is None:
        raise RuntimeError("Vector store not initialized. POST /ingest first.")
    return _store


def search(query: str, k: int = 5) -> list:
    return get_store().similarity_search(query, k=k)
