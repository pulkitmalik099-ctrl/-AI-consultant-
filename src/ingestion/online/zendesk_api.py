"""Online Zendesk ticket fetcher via Zendesk REST API."""

import requests
from langchain.schema import Document
from src.ingestion.models import ZendeskOnlineConfig


def fetch_zendesk_tickets(config: ZendeskOnlineConfig) -> list[Document]:
    """Fetch tickets from a live Zendesk instance.

    Auth: email/token + API token (Basic auth).
    Paginates automatically up to config.limit tickets.
    """
    base_url = f"https://{config.subdomain}.zendesk.com/api/v2/tickets.json"
    auth = (f"{config.email}/token", config.api_token)
    docs: list[Document] = []
    url: str | None = base_url

    while url and len(docs) < config.limit:
        batch = min(100, config.limit - len(docs))
        resp = requests.get(url, auth=auth, params={"per_page": batch}, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        for ticket in data.get("tickets", []):
            ticket_id = str(ticket["id"])
            content = (
                f"[Zendesk] Ticket #{ticket_id}: {ticket.get('subject', '')}\n"
                f"Status: {ticket.get('status', '')}\n\n"
                f"{ticket.get('description', '')}"
            )
            docs.append(
                Document(
                    page_content=content,
                    metadata={
                        "source": f"zendesk://ticket/{ticket_id}",
                        "provider": "zendesk",
                        "mode": "online",
                        "ticket_id": ticket_id,
                        "subject": ticket.get("subject", ""),
                        "status": ticket.get("status", ""),
                    },
                )
            )

        url = data.get("next_page") if len(docs) < config.limit else None

    return docs
