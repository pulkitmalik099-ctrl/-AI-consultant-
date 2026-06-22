"""
Ticketing system ingestion — supports Zendesk and Jira CSV exports.

Usage:
  - Zendesk exports: place CSV files in  data/zendesk/
  - Jira exports:    place CSV files in  data/jira/

Both directories are loaded automatically on /ingest.
Mixed environments (Zendesk + Jira) are fully supported.

Zendesk CSV required columns:  id, subject, description
Jira CSV required columns:      Issue key, Summary, Description
"""

import csv
from enum import Enum
from pathlib import Path
from langchain.schema import Document

DATA_DIR = Path(__file__).parents[2] / "data"
ZENDESK_DIR = DATA_DIR / "zendesk"
JIRA_DIR = DATA_DIR / "jira"


class TicketProvider(str, Enum):
    ZENDESK = "zendesk"
    JIRA = "jira"


# ---------------------------------------------------------------------------
# Zendesk
# ---------------------------------------------------------------------------

_ZENDESK_REQUIRED = {"id", "subject", "description"}


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
                        "ticket_id": ticket_id,
                        "subject": subject,
                        "status": status,
                    },
                )
            )
    return docs


# ---------------------------------------------------------------------------
# Jira
# ---------------------------------------------------------------------------

_JIRA_REQUIRED = {"Issue key", "Summary", "Description"}


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
                        "issue_key": issue_key,
                        "summary": summary,
                        "status": status,
                        "issue_type": issue_type,
                    },
                )
            )
    return docs


# ---------------------------------------------------------------------------
# Bulk loaders
# ---------------------------------------------------------------------------

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


def load_all_tickets(
    providers: list[TicketProvider] | None = None,
) -> list[Document]:
    """Load tickets from all enabled providers.

    Args:
        providers: list of TicketProvider values to include.
                   Defaults to all providers (Zendesk + Jira).
    """
    if providers is None:
        providers = list(TicketProvider)
    docs = []
    if TicketProvider.ZENDESK in providers:
        docs.extend(load_all_zendesk())
    if TicketProvider.JIRA in providers:
        docs.extend(load_all_jira())
    return docs
