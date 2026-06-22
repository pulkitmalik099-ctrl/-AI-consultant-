# Kept for backwards compatibility — use tickets.py for new code.
from src.ingestion.tickets import load_zendesk_csv, load_all_zendesk

__all__ = ["load_zendesk_csv", "load_all_zendesk"]
