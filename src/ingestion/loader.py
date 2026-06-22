from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

DOCS_DIR = Path(__file__).parents[2] / "data" / "documents"

_LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
}


def load_documents(directory: Path = DOCS_DIR) -> list:
    docs = []
    for path in directory.rglob("*"):
        loader_cls = _LOADERS.get(path.suffix.lower())
        if loader_cls:
            loader = loader_cls(str(path))
            docs.extend(loader.load())
    return docs


def chunk_documents(docs: list, chunk_size: int = 1000, chunk_overlap: int = 150) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(docs)
