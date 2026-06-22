"""
Offline ticket ingestion — loads Zendesk and Jira CSV exports.

Place exports in:
  data/zendesk/   ← Zendesk CSV (columns: id, subject, description, status)
  data/jira/      ← Jira CSV    (columns: Issue key, Summary, Description, Status, Issue Type)
"""

import csv
from pathlib import Path
from langchain.schema import Document
from src.ingestion.models import TicketProvider

DATA_DIR = Path(__file__).parents[2] / "data"
ZENDESK_DIR = DATA_DIR / "zendesk"
JIRA_DIR = DATA_DIR / "jira"

_ZENDESK_REQUIRED = {"id", "subject", "description"}
_JIRA_REQUIRED = {"Issue key", "Summary", "Description"}


def load_zendesk_csv(path: Path) -> list[Document]:
    docs = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = _ZENDESK_REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing Zendesk columns {missing}")
        for row in reader:
            ticket_id = row.get("id", "unknown")
            subject = row.get("subject", "")
            description = row.get("description", "")
            status = row.get("status", "")
            content = f"[Zendesk] Ticket #{ticket_id}: {subject}\nStatus: {status}\n\n{description}"
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": f"zendesk://ticket/{ticket_id}",
                        "provider": TicketProvider.ZENDESK,
                        "mode": "offline",
                        "ticket_id": ticket_id,
                        "subject": subject,
                        "status": status,
                    },
                )
            )
    return docs


def load_jira_csv(path: Path) -> list[Document]:
    docs = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = _JIRA_REQUIRED - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path.name}: missing Jira columns {missing}")
        for row in reader:
            issue_key = row.get("Issue key", "unknown")
            summary = row.get("Summary", "")
            description = row.get("Description", "")
            status = row.get("Status", "")
            issue_type = row.get("Issue Type", "")
            content = (
                f"[Jira] {issue_key}: {summary}\n"
                f"Type: {issue_type} | Status: {status}\n\n{description}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": f"jira://issue/{issue_key}",
                        "provider": TicketProvider.JIRA,
                        "mode": "offline",
                        "issue_key": issue_key,
                        "summary": summary,
                        "status": status,
                        "issue_type": issue_type,
                    },
                )
            )
    return docs


def load_all_zendesk(directory: Path = ZENDESK_DIR) -> list[Document]:
    docs = []
    if directory.exists():
        for path in directory.glob("*.csv"):
            docs.extend(load_zendesk_csv(path))
    return docs


def load_all_jira(directory: Path = JIRA_DIR) -> list[Document]:
    docs = []
    if directory.exists():
        for path in directory.glob("*.csv"):
            docs.extend(load_jira_csv(path))
    return docs
