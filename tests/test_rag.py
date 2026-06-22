import pytest
from langchain_core.documents import Document
from src.ingestion.loader import chunk_documents
from src.ingestion.models import TicketProvider, TicketMode, JiraOnlineConfig, TicketSource
from src.retrieval import vector_store as vs
from src.rag.memory import get_session_history, clear_session


# ---------------------------------------------------------------------------
# Ingestion — chunking
# ---------------------------------------------------------------------------

def test_chunk_splits_large_text():
    docs = [Document(page_content="word " * 500, metadata={"source": "test.pdf"})]
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1


def test_chunk_preserves_metadata():
    docs = [Document(page_content="sample benefit information", metadata={"source": "brd.pdf"})]
    chunks = chunk_documents(docs)
    assert all(c.metadata["source"] == "brd.pdf" for c in chunks)


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------

def test_get_store_raises_before_ingest():
    vs._store = None
    with pytest.raises(RuntimeError, match="POST /ingest first"):
        vs.get_store()


def test_get_indexed_docs_empty_before_ingest():
    vs._indexed_docs = []
    assert vs.get_indexed_docs() == []


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_ticket_mode_values():
    assert TicketMode.ONLINE == "online"
    assert TicketMode.OFFLINE == "offline"


def test_jira_config_strips_trailing_slash():
    config = JiraOnlineConfig(
        server_url="https://company.atlassian.net/",
        username="admin",
        api_token="token",
    )
    assert not config.server_url.endswith("/")


def test_ticket_source_offline_zendesk():
    source = TicketSource(provider=TicketProvider.ZENDESK, mode=TicketMode.OFFLINE)
    assert source.provider == TicketProvider.ZENDESK
    assert source.mode == TicketMode.OFFLINE
    assert source.zendesk_config is None


# ---------------------------------------------------------------------------
# Offline CSV loaders
# ---------------------------------------------------------------------------

def test_load_zendesk_csv(tmp_path):
    from src.ingestion.tickets import load_zendesk_csv
    csv_file = tmp_path / "tickets.csv"
    csv_file.write_text(
        "id,subject,description,status\n"
        "101,Dental claim query,How do I submit a dental claim?,open\n",
        encoding="utf-8",
    )
    docs = load_zendesk_csv(csv_file)
    assert len(docs) == 1
    assert "Ticket #101" in docs[0].page_content
    assert docs[0].metadata["ticket_id"] == "101"
    assert docs[0].metadata["source"] == "zendesk://ticket/101"
    assert docs[0].metadata["mode"] == "offline"


def test_load_zendesk_csv_missing_columns(tmp_path):
    from src.ingestion.tickets import load_zendesk_csv
    csv_file = tmp_path / "bad.csv"
    csv_file.write_text("id,subject\n1,test\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing Zendesk columns"):
        load_zendesk_csv(csv_file)


def test_load_jira_csv(tmp_path):
    from src.ingestion.tickets import load_jira_csv
    csv_file = tmp_path / "jira.csv"
    csv_file.write_text(
        "Issue key,Summary,Description,Status,Issue Type\n"
        "BEN-42,Vision coverage,Employee asking about vision coverage.,Open,Story\n",
        encoding="utf-8",
    )
    docs = load_jira_csv(csv_file)
    assert len(docs) == 1
    assert "BEN-42" in docs[0].page_content
    assert docs[0].metadata["source"] == "jira://issue/BEN-42"
    assert docs[0].metadata["mode"] == "offline"


def test_load_jira_csv_missing_columns(tmp_path):
    from src.ingestion.tickets import load_jira_csv
    csv_file = tmp_path / "bad_jira.csv"
    csv_file.write_text("Issue key,Summary\nBEN-1,test\n", encoding="utf-8")
    with pytest.raises(ValueError, match="missing Jira columns"):
        load_jira_csv(csv_file)


def test_load_all_zendesk_skips_missing_dir(tmp_path):
    from src.ingestion.tickets import load_all_zendesk
    docs = load_all_zendesk(directory=tmp_path / "nonexistent")
    assert docs == []


def test_load_all_jira_skips_missing_dir(tmp_path):
    from src.ingestion.tickets import load_all_jira
    docs = load_all_jira(directory=tmp_path / "nonexistent")
    assert docs == []


# ---------------------------------------------------------------------------
# Conversation memory
# ---------------------------------------------------------------------------

def test_session_history_is_isolated():
    clear_session("session-a")
    clear_session("session-b")
    hist_a = get_session_history("session-a")
    hist_b = get_session_history("session-b")
    assert hist_a is not hist_b


def test_clear_session_removes_history():
    get_session_history("temp-session")
    clear_session("temp-session")
    new_hist = get_session_history("temp-session")
    # After clearing, a fresh history object is created
    assert len(new_hist.messages) == 0
