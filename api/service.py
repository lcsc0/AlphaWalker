"""Application service layer for AlphaWalker analysis runs."""

from __future__ import annotations

import math
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from .engine import EngineEvent, RuleBasedAnalysisEngine
from .models import (
    AnalysisError,
    AnalysisEvent,
    AnalysisRequest,
    ClientContext,
    Holding,
    PortfolioInput,
    PortfolioSummary,
    RunRecord,
    utc_now_iso,
)
from .storage import RunStorage


@dataclass(slots=True)
class SubmittedRun:
    run_id: str
    status: str
    created_at: str


class AnalysisService:
    def __init__(self, storage: RunStorage, engine: RuleBasedAnalysisEngine | None = None) -> None:
        self.storage = storage
        self.engine = engine or RuleBasedAnalysisEngine()
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="alphawalker")
        self._run_locks: dict[str, threading.Lock] = {}

    def recover_incomplete_runs(self) -> int:
        return self.storage.mark_incomplete_runs_failed(
            AnalysisError(
                code="run_interrupted",
                message="The service restarted before this run completed.",
                retryable=True,
            ).to_dict()
        )

    def submit_run(self, request: AnalysisRequest) -> SubmittedRun:
        normalized_holdings, normalization_message = self._normalize_holdings(request.portfolio.holdings)
        created_at = utc_now_iso()
        run_id = f"run_{uuid.uuid4().hex[:12]}"

        normalized_request = AnalysisRequest(
            portfolio=PortfolioInput(
                holdings=normalized_holdings,
                as_of_date=request.portfolio.as_of_date,
            ),
            options=request.options,
            client_context=request.client_context or ClientContext(),
        )
        total_weight = round(sum(holding.weight for holding in normalized_holdings), 6)

        record = RunRecord(
            run_id=run_id,
            status="queued",
            progress=0.0,
            portfolio_summary=PortfolioSummary(
                holdings_count=len(normalized_holdings),
                total_weight=total_weight,
            ),
            request_payload=normalized_request.to_dict(),
            normalized_holdings=[holding.to_dict() for holding in normalized_holdings],
            created_at=created_at,
        )
        self.storage.create_run(record)

        if normalization_message:
            self.storage.append_event(
                run_id,
                AnalysisEvent(
                    seq=self.storage.next_seq(run_id),
                    timestamp=utc_now_iso(),
                    agent="portfolio_ingestor",
                    stage="completed",
                    message=normalization_message,
                ),
            )

        self.executor.submit(self._execute_run, run_id, normalized_request)
        return SubmittedRun(run_id=run_id, status="queued", created_at=created_at)

    def get_run(self, run_id: str) -> RunRecord | None:
        return self.storage.get_run(run_id)

    def get_events(self, run_id: str, after_seq: int = 0) -> tuple[list[AnalysisEvent], int]:
        events = self.storage.list_events(run_id, after_seq)
        next_cursor = (events[-1].seq + 1) if events else after_seq + 1
        return events, next_cursor

    def _execute_run(self, run_id: str, request: AnalysisRequest) -> None:
        run_lock = self._run_locks.setdefault(run_id, threading.Lock())
        with run_lock:
            self.storage.update_run(run_id, status="running", progress=0.05, started_at=utc_now_iso())
            try:
                result = self.engine.analyze(request, emit=lambda event: self._emit_event(run_id, event))
                self.storage.update_run(
                    run_id,
                    status="completed",
                    progress=1.0,
                    finished_at=utc_now_iso(),
                    result=result.to_dict(),
                )
            except Exception as exc:  # pragma: no cover
                error = AnalysisError(
                    code="analysis_failed",
                    message=str(exc),
                    retryable=False,
                ).to_dict()
                self._emit_event(
                    run_id,
                    EngineEvent(
                        agent="judge_agent",
                        stage="failed",
                        message="The analysis run failed before producing a result",
                        progress=0.99,
                    ),
                )
                self.storage.update_run(
                    run_id,
                    status="failed",
                    progress=0.99,
                    finished_at=utc_now_iso(),
                    error=error,
                )

    def _emit_event(self, run_id: str, event: EngineEvent) -> None:
        seq = self.storage.next_seq(run_id)
        self.storage.append_event(
            run_id,
            AnalysisEvent(
                seq=seq,
                timestamp=utc_now_iso(),
                agent=event.agent,
                stage=event.stage,
                message=event.message,
            ),
        )
        if event.progress is not None:
            self.storage.update_run(run_id, progress=min(max(event.progress, 0.0), 1.0))

    def _normalize_holdings(self, holdings: list[Holding]) -> tuple[list[Holding], str | None]:
        merged: dict[str, float] = {}
        original_count = 0
        for holding in holdings:
            ticker = holding.ticker.strip().upper()
            if not ticker:
                continue
            original_count += 1
            if holding.weight < 0:
                raise ValueError(f"Negative weight is not allowed for {ticker}.")
            merged[ticker] = merged.get(ticker, 0.0) + holding.weight

        normalized = [Holding(ticker=ticker, weight=weight) for ticker, weight in sorted(merged.items())]
        if not normalized:
            raise ValueError("Portfolio must contain at least one holding.")

        total_weight = sum(holding.weight for holding in normalized)
        if math.isclose(total_weight, 1.0, rel_tol=1e-6, abs_tol=1e-6):
            if len(normalized) != original_count:
                return normalized, f"Merged duplicate tickers into {len(normalized)} normalized holdings."
            return normalized, None

        if math.isclose(total_weight, 0.0, abs_tol=1e-9):
            raise ValueError("Portfolio weights must sum to more than zero.")

        for holding in normalized:
            holding.weight = round(holding.weight / total_weight, 6)

        correction_kind = "Merged duplicate tickers and normalized weights" if len(normalized) != original_count else "Normalized weights"
        return (
            normalized,
            f"{correction_kind} to total 1.0 across {len(normalized)} holdings.",
        )
