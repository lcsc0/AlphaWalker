"""Thin httpx wrapper for Insforge REST API writes."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("api.insforge_client")


class InsforgeClient:
    """Client for writing analysis data to Insforge REST API."""

    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self._http = httpx.Client(
            base_url=self.base_url + "/api/database/records",
            headers={
                "Authorization": f"Bearer {service_key}",
                "Content-Type": "application/json",
                "Prefer": "return=representation",
            },
            timeout=10.0,
        )

    def close(self) -> None:
        self._http.close()

    def insert_analysis_run(self, run_data: dict) -> dict | None:
        """Insert a row into analysis_runs. Returns the created row or None on failure."""
        try:
            resp = self._http.post("/analysis_runs", json=[run_data])
            resp.raise_for_status()
            rows = resp.json()
            if isinstance(rows, list) and len(rows) > 0:
                return rows[0]
            return None
        except Exception as exc:
            logger.warning("Failed to insert analysis_run: %s", exc)
            return None

    def update_analysis_run(self, id: str, updates: dict) -> None:
        """Update an analysis_runs row by id. Logs and swallows errors."""
        try:
            resp = self._http.patch(
                f"/analysis_runs?id=eq.{id}",
                json=updates,
            )
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to update analysis_run %s: %s", id, exc)

    def insert_ticker_verdicts(self, verdicts: list[dict]) -> None:
        """Insert rows into ticker_verdicts. Logs and swallows errors."""
        if len(verdicts) == 0:
            return
        try:
            resp = self._http.post("/ticker_verdicts", json=verdicts)
            resp.raise_for_status()
        except Exception as exc:
            logger.warning("Failed to insert %d ticker_verdicts: %s", len(verdicts), exc)


def create_insforge_client(
    base_url: str | None, service_key: str | None
) -> InsforgeClient | None:
    """Factory: returns an InsforgeClient if both env vars are set, else None."""
    if not base_url or not service_key:
        logger.info("Insforge credentials not configured; cloud writes disabled.")
        return None
    logger.info("Insforge client initialized for %s", base_url)
    return InsforgeClient(base_url=base_url, service_key=service_key)
