"""API key authentication middleware.

Set API_KEY in .env to enable. If not set, auth is disabled (dev mode).
"""

import os
from fastapi import Request, HTTPException
from fastapi.security import APIKeyHeader

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(request: Request) -> None:
    """FastAPI dependency — raises 401 if API_KEY is set and not matched."""
    expected = os.getenv("API_KEY")
    if not expected:
        return  # auth disabled in dev mode

    provided = request.headers.get("X-API-Key")
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
