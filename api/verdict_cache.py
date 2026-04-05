"""In-process TTL cache for ticker verdicts.

Keyed by ticker symbol. Survives across requests within the same uvicorn process.
Safe for single-worker deployments (default uvicorn behavior).
"""

from __future__ import annotations

import time
from typing import Any

_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_TTL = 12 * 3600  # 12 hours in seconds


def get(ticker: str) -> dict[str, Any] | None:
    """Return cached verdict dict if present and not expired, else None."""
    entry = _cache.get(ticker)
    if entry is None:
        return None
    ts, data = entry
    if time.time() - ts > _TTL:
        del _cache[ticker]
        return None
    return data


def set_verdict(ticker: str, data: dict[str, Any]) -> None:
    """Store a verdict dict for ticker."""
    _cache[ticker] = (time.time(), data)


def invalidate(ticker: str) -> None:
    """Remove a ticker from the cache (e.g. on forced refresh)."""
    _cache.pop(ticker, None)
