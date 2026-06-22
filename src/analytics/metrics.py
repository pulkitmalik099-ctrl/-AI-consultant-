"""In-memory metrics derived from the audit log.

Returns aggregated stats for the /analytics endpoint.
"""

from collections import Counter
from src.analytics.logger import read_log


def get_metrics() -> dict:
    records = read_log(limit=10_000)

    queries = [r for r in records if r.get("event") == "query"]
    ingests = [r for r in records if r.get("event") == "ingest"]
    errors = [r for r in records if r.get("event") == "error"]

    source_counter: Counter = Counter()
    session_counter: Counter = Counter()
    latencies: list[float] = []

    for q in queries:
        for src in q.get("sources", []):
            source_counter[src] += 1
        session_counter[q.get("session_id", "unknown")] += 1
        if "latency_ms" in q:
            latencies.append(q["latency_ms"])

    avg_latency = round(sum(latencies) / len(latencies), 1) if latencies else 0.0
    p95_latency = round(sorted(latencies)[int(len(latencies) * 0.95)], 1) if len(latencies) >= 20 else None

    return {
        "total_queries": len(queries),
        "total_ingests": len(ingests),
        "total_errors": len(errors),
        "unique_sessions": len(session_counter),
        "avg_latency_ms": avg_latency,
        "p95_latency_ms": p95_latency,
        "top_sources": source_counter.most_common(10),
        "top_sessions": session_counter.most_common(5),
    }
