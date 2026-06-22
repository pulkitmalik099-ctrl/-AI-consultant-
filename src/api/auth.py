"""API key authentication.

Set API_KEY in .env to enable. If not set, auth is disabled (dev mode).
Accepts the key via X-API-Key header OR ?api_key= query param
(query param is needed for EventSource / SSE connections).
"""

import os
from fastapi import Request, HTTPException


async def require_api_key(request: Request) -> None:
    expected = os.getenv("API_KEY")
    if not expected:
        return  # dev mode — no auth

    provided = (
        request.headers.get("X-API-Key")
        or request.query_params.get("api_key")
    )
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
