# Backend Writes to Insforge (Replace SQLite as Source of Truth)

**Date**: 2026-04-04
**Status**: Approved
**Priority**: #1 in Insforge integration roadmap

## Problem

The application has two independent persistence layers:
- **Frontend**: Writes analysis results to Insforge (`analysis_runs`, `ticker_verdicts`) after receiving them from the API
- **Backend**: Writes the same data to SQLite (`data/analysis_runs.db`) during execution

These are completely unaware of each other. Runs triggered via CLI, `curl`, or direct API calls never appear in Insforge, so the History tab only shows browser-triggered runs. The Insforge anon key (with write access) is also exposed in client-side JS.

## Solution

Move Insforge writes to the FastAPI backend. The backend becomes the single writer for analysis data. The frontend becomes a read-only layer for analysis runs and verdicts. SQLite stays only for the ephemeral event stream (agent progress updates during a run).

## Architecture

```
Frontend (React)                    Backend (FastAPI/Jac)
  |                                   |
  |-- reads analysis_runs ----------> Insforge (cloud)
  |-- reads ticker_verdicts --------> Insforge (cloud)
  |-- reads/writes portfolios ------> Insforge (cloud)
  |                                   |
  |-- POST /v1/analyze-tickers -----> runs analysis
  |                                   |-- writes analysis_runs --> Insforge
  |                                   |-- writes ticker_verdicts -> Insforge
  |                                   |-- writes events ----------> SQLite (ephemeral)
  |                                   |
  |-- GET /v1/analysis-runs/{id}/events -> SQLite (polling)
```

## New Module: `api/insforge_client.jac`

Thin `httpx`-based client for the Insforge REST API.

### Configuration

| Env Var | Purpose |
|---------|---------|
| `INSFORGE_URL` | Project base URL (e.g. `https://57pqpigm.us-east.insforge.app`) |
| `INSFORGE_SERVICE_KEY` | Admin/service key for write access |

If either is missing, the client is `None` and the backend operates in local-only mode.

### Class: `InsforgeClient`

- `__init__(base_url: str, service_key: str)`: Creates `httpx.Client` with base URL `{base_url}/api/database/records` and `Authorization: Bearer {service_key}` header. Default 10-second timeout.
- `insert_analysis_run(run_data: dict) -> dict | None`: POST to `/analysis_runs`. Returns created row with Insforge-generated `id`.
- `update_analysis_run(id: str, updates: dict) -> None`: PATCH to `/analysis_runs/{id}` for status transitions.
- `insert_ticker_verdicts(verdicts: list[dict]) -> None`: POST to `/ticker_verdicts`.

## Integration into `AnalysisService`

`AnalysisService.__init__` gains an optional `insforge: InsforgeClient | None = None` parameter.

### Write points

1. **`submit_run`**: Insert row into Insforge `analysis_runs` with `status: "queued"`, `tickers`, `created_at`. Store returned Insforge `id`.
2. **`_execute_run` status transitions**:
   - `queued -> running`: Update Insforge row status
   - `running -> completed`: Update status, write results, insert `ticker_verdicts` with Insforge `run_id` as FK
   - `running -> failed`: Update status with error info
3. **`/v1/analyze-tickers` endpoint**: This endpoint calls `run_jac_pipeline` directly and bypasses `AnalysisService`. After getting results, it calls `InsforgeClient` directly (not through the service) to insert the run and verdicts to Insforge. This ensures the frontend's Analyze button populates history.

### Dependency injection

If `INSFORGE_URL` / `INSFORGE_SERVICE_KEY` are not set, `InsforgeClient` is `None`. All write paths guard with `if self.insforge is not None`. Zero overhead in local-only mode.

## Frontend Changes (`App.jsx`)

### Removed
- `insforge.database.from('analysis_runs').insert(...)` call in `analyzeTickers()`
- `insforge.database.from('ticker_verdicts').insert(...)` call in `analyzeTickers()`

### Kept (unchanged)
- All reads: `RunHistory` reads `analysis_runs`, `MomentumSparkline` reads `ticker_verdicts`, `loadPortfolios` reads `portfolios`
- Portfolio writes: `AddPortfolioDrawer.save()` and seed insert stay client-side
- `insforge` client initialization (hardcoded credentials stay as-is; moving to env vars is a separate step)

### Result
`analyzeTickers()` simplifies from ~30 lines to ~15. After the API call returns, it just sets the results state. No post-call Insforge write logic.

## SQLite (`RunStorage`) — No Changes

SQLite continues handling:
- Event streaming: `append_event`, `list_events`, `next_seq`
- Fast polling: `/v1/analysis-runs/{run_id}/events` endpoint
- Run state for the `AnalysisService` execution lifecycle

These are high-frequency, ephemeral data that don't need cloud persistence.

## Error Handling

**Principle**: Insforge writes are non-blocking. A cloud write failure never prevents a successful analysis from being returned.

| Scenario | Behavior |
|----------|----------|
| Insforge unreachable | Logged as warning. Run proceeds via SQLite. Result returned to caller. |
| Write fails mid-run | Logged with run_id and error. Analysis continues. History tab won't show this run. |
| Partial write (run OK, verdicts fail) | Run appears in History but detail incomplete. Error logged. |
| `httpx` timeout | 10-second default. Generous for write operations. |
| No credentials configured | `InsforgeClient` is `None`. All write paths skipped silently. |

## Environment Variables

### Backend (new)
| Var | Required | Default |
|-----|----------|---------|
| `INSFORGE_URL` | No | None (disables Insforge) |
| `INSFORGE_SERVICE_KEY` | No | None (disables Insforge) |

### Existing (unchanged)
| Var | Purpose |
|-----|---------|
| `ALPHAWALKER_DB_PATH` | SQLite path for event stream |
| `ALPHAWALKER_API_KEY` | API authentication |

### Frontend
No changes in this phase. Hardcoded credentials remain; moving to `VITE_*` env vars is Priority #3.

## Out of Scope

- Real-time subscriptions for run status (Priority #2)
- Moving frontend credentials to env vars (Priority #3)
- Foreign key / schema constraints in Insforge (Priority #4)
- Error surfacing in the frontend UI (Priority #5)
- Portfolio CRUD migration to backend
- Retry/backfill mechanism for failed Insforge writes
