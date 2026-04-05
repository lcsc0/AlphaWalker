"""FastAPI application exposing AlphaWalker analysis runs.

Analysis executes the Jac multi-agent graph (`alphawalker_pipeline.jac`) by default,
with SQLite-backed run state for polling. See `DEPLOYMENT.md` for env vars.
"""

import os;
import from pathlib { Path }
import from typing { Annotated }
import from fastapi { Depends, FastAPI, Header, HTTPException, Query }
import from fastapi.middleware.cors { CORSMiddleware }
import from pydantic { BaseModel }

import from api.models {
    AnalysisOptions,
    AnalysisRequest,
    ClientContext,
    Holding,
    PortfolioInput
}
import from api.jac_bridge { run_jac_pipeline }
import from api.prices { fetch_historical_prices }
import from api.service { AnalysisService }
import from api.storage { RunStorage }
import from api.insforge_client { create_insforge_client }

class HoldingIn(BaseModel) {
    has ticker: str;
    has weight: float;
}

class PortfolioInputIn(BaseModel) {
    has holdings: list[HoldingIn];
    has as_of_date: str;
}

class AnalysisOptionsIn(BaseModel) {
    has include_sentiment: bool = True;
    has include_rebalancing: bool = True;
    has include_graph: bool = True;
}

class ClientContextIn(BaseModel) {
    has source: str = "alphawalker";
    has session_id: str | None = None;
}

class AnalysisRequestIn(BaseModel) {
    has portfolio: PortfolioInputIn;
    has options: AnalysisOptionsIn = AnalysisOptionsIn();
    has client_context: ClientContextIn = ClientContextIn();
}

class AnalyzeTickersIn(BaseModel) {
    has tickers: list[str];
}

glob APP_ROOT = Path(__file__).resolve().parent.parent;
glob DB_PATH = os.getenv("ALPHAWALKER_DB_PATH", str(APP_ROOT / "data" / "analysis_runs.db"));
glob API_KEY = os.getenv("ALPHAWALKER_API_KEY", "");
glob storage = RunStorage(DB_PATH);
glob insforge_client = create_insforge_client(
    os.getenv("INSFORGE_URL"),
    os.getenv("INSFORGE_SERVICE_KEY")
);
glob service = AnalysisService(storage, insforge=insforge_client);
glob startup_recover_count = service.recover_incomplete_runs();
glob app = FastAPI(title="AlphaWalker API", version="0.1.0");

with entry {
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    );
}

def require_api_key(x_api_key: Annotated[str | None, Header()] = None) {
    if API_KEY == "" {
        return;
    }
    if x_api_key != API_KEY {
        raise HTTPException(status_code=401, detail="Unauthorized");
    }
}

def _normalize_ticker_list(raw: list[str]) -> list[str] {
    out: list[str] = [];
    for t in raw {
        if t and t.strip() != "" {
            out.append(t.strip().upper());
        }
    }
    return out;
}

def _int_field(v: int | str | None) -> int {
    if v is None {
        return 0;
    }
    return int(v);
}

def _row_with_confidence(r: dict) -> dict {
    jc_i = _int_field(r.get("judge_confidence", 0));
    return {
        "ticker": str(r.get("ticker", "") or ""),
        "verdict": str(r.get("verdict", "") or ""),
        "confidence": jc_i,
        "rationale": str(r.get("rationale", "") or ""),
        "condition": str(r.get("condition", "") or ""),
        "judge_confidence": jc_i,
        "bull_argument": str(r.get("bull_argument", "") or ""),
        "bull_confidence": _int_field(r.get("bull_confidence", 0)),
        "bear_argument": str(r.get("bear_argument", "") or ""),
        "bear_confidence": _int_field(r.get("bear_confidence", 0))
    };
}

def _analyze_tickers_response(body: AnalyzeTickersIn) -> dict {
    tickers = _normalize_ticker_list(body.tickers);
    if len(tickers) == 0 {
        raise HTTPException(
            status_code=400,
            detail="Provide at least one non-empty ticker."
        );
    }
    try {
        rows_raw = run_jac_pipeline(tickers);
    } except Exception as exc {
        raise HTTPException(status_code=502, detail=str(exc));
    }
    data: list[dict] = [];
    for r in rows_raw {
        if isinstance(r, dict) {
            data.append(_row_with_confidence(r));
        }
    }
    if insforge_client is not None and len(data) > 0 {
        insforge_row = insforge_client.insert_analysis_run({
            "tickers": tickers,
            "status": "completed",
            "results": data
        });
        if insforge_row is not None and "id" in insforge_row {
            insforge_run_id = insforge_row["id"];
            verdicts: list[dict] = [];
            for d in data {
                verdicts.append({
                    "run_id": insforge_run_id,
                    "ticker": d.get("ticker", ""),
                    "verdict": d.get("verdict", ""),
                    "judge_confidence": d.get("judge_confidence", 0),
                    "bull_confidence": d.get("bull_confidence", 0),
                    "bear_confidence": d.get("bear_confidence", 0),
                    "rationale": d.get("rationale", ""),
                    "condition": d.get("condition", ""),
                    "bull_argument": d.get("bull_argument", ""),
                    "bear_argument": d.get("bear_argument", "")
                });
            }
            if len(verdicts) > 0 {
                insforge_client.insert_ticker_verdicts(verdicts);
            }
        }
    }
    return {"status": "success", "data": data};
}

def to_request(payload: AnalysisRequestIn) -> AnalysisRequest {
    hs: list[Holding] = [];
    for item in payload.portfolio.holdings {
        hs.append(Holding(ticker=item.ticker, weight=item.weight));
    }
    return AnalysisRequest(
        portfolio=PortfolioInput(holdings=hs, as_of_date=payload.portfolio.as_of_date),
        options=AnalysisOptions(**payload.options.model_dump()),
        client_context=ClientContext(**payload.client_context.model_dump())
    );
}

@app.get("/health")
def health() -> dict[str, str] {
    return {"status": "ok"};
}

@app.post("/v1/analyze-tickers", dependencies=[Depends(require_api_key)])
def analyze_tickers_v1(body: AnalyzeTickersIn) -> dict {
    return _analyze_tickers_response(body);
}

@app.post("/analyze", dependencies=[Depends(require_api_key)])
def analyze_tickers_alias(body: AnalyzeTickersIn) -> dict {
    return _analyze_tickers_response(body);
}

@app.post("/v1/analysis-runs", dependencies=[Depends(require_api_key)])
def create_analysis_run(payload: AnalysisRequestIn) -> dict[str, str] {
    for item in payload.portfolio.holdings {
        if item.ticker.strip() == "" {
            raise ValueError("Each holding must include a non-empty ticker.");
        }
        if item.weight <= 0 {
            raise ValueError("Holding weights must be greater than zero.");
        }
    }
    try {
        run = service.submit_run(to_request(payload));
    } except ValueError as exc {
        raise HTTPException(status_code=400, detail=str(exc));
    }
    return {
        "run_id": run.run_id,
        "status": run.status,
        "created_at": run.created_at
    };
}

@app.get("/v1/analysis-runs/{run_id}", dependencies=[Depends(require_api_key)])
def get_analysis_run(run_id: str) -> dict {
    run = service.get_run(run_id);
    if run is None {
        raise HTTPException(status_code=404, detail="Run not found");
    }
    return {
        "run_id": run.run_id,
        "status": run.status,
        "progress": run.progress,
        "portfolio_summary": run.portfolio_summary.to_dict(),
        "result": run.result,
        "error": run.error,
        "started_at": run.started_at,
        "finished_at": run.finished_at
    };
}

@app.get("/v1/analysis-runs/{run_id}/events", dependencies=[Depends(require_api_key)])
def get_analysis_events(
    run_id: str,
    cursor: Annotated[int, Query(ge=0)] = 0
) -> dict {
    run = service.get_run(run_id);
    if run is None {
        raise HTTPException(status_code=404, detail="Run not found");
    }
    after: int = int(cursor);
    (events, next_cursor) = service.get_events(run_id, after);
    return {
        "run_id": run_id,
        "events": [event.to_dict() for event in events],
        "next_cursor": next_cursor
    };
}

@app.get("/v1/historical-prices/{ticker}", dependencies=[Depends(require_api_key)])
def get_historical_prices(ticker: str, period: str = "1y") -> dict {
    allowed = ["1mo", "3mo", "6mo", "1y", "2y", "5y"];
    if period not in allowed {
        raise HTTPException(status_code=400, detail=f"period must be one of {allowed}");
    }
    try {
        prices = fetch_historical_prices(ticker, period);
    } except Exception as exc {
        raise HTTPException(status_code=502, detail=str(exc));
    }
    return {"ticker": ticker.upper(), "prices": prices};
}
