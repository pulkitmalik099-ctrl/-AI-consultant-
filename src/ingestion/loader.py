import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.ingestion.models import TicketProvider, TicketMode, TicketSource, ZendeskOnlineConfig, JiraOnlineConfig
from src.ingestion.tickets import load_all_zendesk, load_all_jira

DOCS_DIR = Path(__file__).parents[2] / "data" / "documents"

_LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
}


def _load_ticket_source(source: TicketSource) -> list:
    if source.provider == TicketProvider.ZENDESK:
        if source.mode == TicketMode.OFFLINE:
            return load_all_zendesk()
        # online — use provided config or fall back to env vars
        from src.ingestion.online.zendesk_api import fetch_zendesk_tickets
        config = source.zendesk_config or ZendeskOnlineConfig(
            subdomain=os.getenv("ZENDESK_SUBDOMAIN", ""),
            email=os.getenv("ZENDESK_EMAIL", ""),
            api_token=os.getenv("ZENDESK_API_TOKEN", ""),
        )
        return fetch_zendesk_tickets(config)

    if source.provider == TicketProvider.JIRA:
        if source.mode == TicketMode.OFFLINE:
            return load_all_jira()
        from src.ingestion.online.jira_api import fetch_jira_issues
        config = source.jira_config or JiraOnlineConfig(
            server_url=os.getenv("JIRA_SERVER_URL", ""),
            username=os.getenv("JIRA_USERNAME", ""),
            api_token=os.getenv("JIRA_API_TOKEN", ""),
            project_key=os.getenv("JIRA_PROJECT_KEY") or None,
        )
        return fetch_jira_issues(config)

    return []


def load_documents(
    directory: Path = DOCS_DIR,
    ticket_sources: list[TicketSource] | None = None,
) -> list:
    """Load business documents and tickets.

    Args:
        directory: folder containing PDF/DOCX/TXT files.
        ticket_sources: which providers + modes to include.
                        None = load all offline (Zendesk + Jira CSVs).
                        [] = skip tickets entirely.
    """
    docs = []

    for path in directory.rglob("*"):
        loader_cls = _LOADERS.get(path.suffix.lower())
        if loader_cls:
            docs.extend(loader_cls(str(path)).load())

    if ticket_sources is None:
        docs.extend(load_all_zendesk())
        docs.extend(load_all_jira())
    else:
        for source in ticket_sources:
            docs.extend(_load_ticket_source(source))

    return docs


def chunk_documents(docs: list, chunk_size: int = 1000, chunk_overlap: int = 150) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    return splitter.split_documents(docs)
