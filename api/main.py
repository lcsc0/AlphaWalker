"""FastAPI application exposing AlphaWalker analysis runs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from .models import AnalysisOptions, AnalysisRequest, ClientContext, Holding, PortfolioInput
from .service import AnalysisService
from .storage import RunStorage


class HoldingIn(BaseModel):
    ticker: str = Field(min_length=1)
    weight: float = Field(gt=0)


class PortfolioInputIn(BaseModel):
    holdings: list[HoldingIn]
    as_of_date: str


class AnalysisOptionsIn(BaseModel):
    include_sentiment: bool = True
    include_rebalancing: bool = True
    include_graph: bool = True


class ClientContextIn(BaseModel):
    source: str = "base44"
    session_id: str | None = None


class AnalysisRequestIn(BaseModel):
    portfolio: PortfolioInputIn
    options: AnalysisOptionsIn = Field(default_factory=AnalysisOptionsIn)
    client_context: ClientContextIn = Field(default_factory=ClientContextIn)

    model_config = ConfigDict(extra="forbid")


APP_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = os.getenv("ALPHAWALKER_DB_PATH", str(APP_ROOT / "data" / "analysis_runs.db"))
API_KEY = os.getenv("ALPHAWALKER_API_KEY", "")

storage = RunStorage(DB_PATH)
service = AnalysisService(storage)
service.recover_incomplete_runs()

app = FastAPI(title="AlphaWalker API", version="0.1.0")


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def to_request(payload: AnalysisRequestIn) -> AnalysisRequest:
    return AnalysisRequest(
        portfolio=PortfolioInput(
            holdings=[Holding(ticker=item.ticker, weight=item.weight) for item in payload.portfolio.holdings],
            as_of_date=payload.portfolio.as_of_date,
        ),
        options=AnalysisOptions(**payload.options.model_dump()),
        client_context=ClientContext(**payload.client_context.model_dump()),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/analysis-runs", dependencies=[Depends(require_api_key)])
def create_analysis_run(payload: AnalysisRequestIn) -> dict[str, str]:
    try:
        run = service.submit_run(to_request(payload))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "run_id": run.run_id,
        "status": run.status,
        "created_at": run.created_at,
    }


@app.get("/v1/analysis-runs/{run_id}", dependencies=[Depends(require_api_key)])
def get_analysis_run(run_id: str) -> dict:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "run_id": run.run_id,
        "status": run.status,
        "progress": run.progress,
        "portfolio_summary": run.portfolio_summary.to_dict(),
        "result": run.result,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
    }


@app.get("/v1/analysis-runs/{run_id}/events", dependencies=[Depends(require_api_key)])
def get_analysis_events(
    run_id: str,
    cursor: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    events, next_cursor = service.get_events(run_id, after_seq=cursor)
    return {
        "run_id": run_id,
        "events": [event.to_dict() for event in events],
        "next_cursor": next_cursor,
    }
