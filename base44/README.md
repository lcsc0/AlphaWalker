# Base44 Integration Assets

This folder contains the app-facing pieces for the AlphaWalker × Base44 flow.

**Flow:** Base44 UI → backend functions here → **FastAPI** (`api/`, OpenAPI) → **Jac** graph (`alphawalker_pipeline.jac`, spawned by `api/_jac_worker_main.py`) → JSON results back to Base44 entities and dashboard.

## What to create in Base44

Create these entities:

- `AnalysisRun`
- `AnalysisEvent`
- `PortfolioSnapshot`

Recommended fields:

- `AnalysisRun`: `run_id`, `status`, `user_id`, `portfolio_name`, `holdings_count`, `submitted_input`, `result`, `error`, `created_date`, `updated_date`, `completed_date`
- `AnalysisEvent`: `run_id`, `analysis_run_id`, `seq`, `agent`, `stage`, `message`, `event_time`
- `PortfolioSnapshot`: `analysis_run_id`, `holdings`, `source_type`, `raw_csv_file_url`

## Secrets

Configure these Base44 secrets:

- `ALPHAWALKER_API_BASE_URL`
- `ALPHAWALKER_API_KEY`

## Jac engine on the API host

The FastAPI service (`api/`) runs the real **Jac** multi-agent graph (bull/bear coalitions + judge) per analysis when `ALPHAWALKER_USE_JAC` is enabled (default). That path calls the LLM via your existing prompt modules, so the machine hosting the API needs:

- `OPENAI_API_KEY` (or whatever your `byllm` / LiteLLM setup expects)
- `jaclang` installed (`pip install -r requirements.txt`)

To force the older deterministic demo engine only (no Jac subprocess), set `ALPHAWALKER_USE_JAC=0` on the API server.

## Backend functions

Use the templates in `functions/`:

- `submitPortfolioAnalysis.ts`
- `syncPortfolioAnalysisRun.ts`

### Optional: quick watchlist (no run history / polling)

For a simple UI that only needs per-ticker judge output (e.g. a Repeating List), call the synchronous API:

- `POST ${ALPHAWALKER_API_BASE_URL}/v1/analyze-tickers` (or `/analyze`)
- Headers: `Content-Type: application/json`, `X-API-Key: ${ALPHAWALKER_API_KEY}`
- Body: `{ "tickers": ["NVDA", "AAPL"] }`
- Response: `status` and `data` array with `ticker`, `verdict`, `confidence`, `rationale`, `condition`, plus bull/bear fields.

Example backend function:

```typescript
type AnalyzePayload = { tickers: string[] };

export default async function analyzeTickersQuick(payload: AnalyzePayload) {
  const apiBaseUrl = process.env.ALPHAWALKER_API_BASE_URL;
  const apiKey = process.env.ALPHAWALKER_API_KEY;
  if (!apiBaseUrl || !apiKey) {
    throw new Error("Missing AlphaWalker API configuration");
  }
  const response = await fetch(`${apiBaseUrl}/v1/analyze-tickers`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({ tickers: payload.tickers }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}
```

## Suggested app prompt

Prompt Base44 with:

> Build a portfolio analysis dashboard for AlphaWalker. Users can enter stock tickers and weights manually or upload a CSV. On submit, call the `submitPortfolioAnalysis` backend function, redirect to a live analysis page, poll `syncPortfolioAnalysisRun` every 2-3 seconds, show a real-time agent activity feed, then render overall risk, per-holding risk and sentiment, rebalancing suggestions, and a run history view.
