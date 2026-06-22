"""Audit logger — writes every query and response to a JSONL file.

Each line is a self-contained JSON record for easy parsing / export.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path(__file__).parents[2] / "logs"
LOG_FILE = LOG_DIR / "audit.jsonl"

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_query(
    session_id: str,
    question: str,
    answer: str,
    sources: list[str],
    latency_ms: float,
) -> None:
    record = {
        "ts": _now(),
        "event": "query",
        "session_id": session_id,
        "question": question,
        "answer_length": len(answer),
        "sources": sources,
        "latency_ms": round(latency_ms, 1),
    }
    _append(record)


def log_ingest(documents_loaded: int, chunks_created: int, ticket_sources: object) -> None:
    record = {
        "ts": _now(),
        "event": "ingest",
        "documents_loaded": documents_loaded,
        "chunks_created": chunks_created,
        "ticket_sources": ticket_sources,
    }
    _append(record)


def log_error(event: str, detail: str) -> None:
    record = {"ts": _now(), "event": "error", "context": event, "detail": detail}
    _append(record)


def _append(record: dict) -> None:
    LOG_DIR.mkdir(exist_ok=True)
    with _lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")


def read_log(limit: int = 500) -> list[dict]:
    if not LOG_FILE.exists():
        return []
    records = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records[-limit:]
