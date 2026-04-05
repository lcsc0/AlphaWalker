# AlphaWalker API Deployment

## Local run

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
cd frontend && npm install && cd ..
```

2. Set environment variables (copy the block below into a `.env` or export directly):

```bash
export OPENAI_API_KEY=sk-...          # required for Jac LLM calls
export ALPHAWALKER_API_KEY=dev-secret # shared secret for X-API-Key header
# Optional:
# export ALPHAWALKER_DB_PATH=data/analysis_runs.db
# export ALPHAWALKER_USE_JAC=1
# export ALPHAWALKER_JAC_FALLBACK=1
# export ALPHAWALKER_JAC_TIMEOUT=900
```

3. Start everything with one command:

```bash
./start.sh
```

Or start the API and frontend separately:

```bash
# Terminal 1
ALPHAWALKER_API_KEY=dev-secret uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2
cd frontend && npm run dev -- --port 3000
```

**Backend only** (no Node required):

```bash
ALPHAWALKER_API_KEY=dev-secret uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Most of `api` is implemented in `.jac` files; `jaclang` registers an import hook so `api.main:app` resolves to the compiled FastAPI app. `api/__init__.py` imports `jaclang` first so `import api.*` works from any entrypoint. The Jac graph subprocess is spawned from `api/jac_bridge.py` (Python; avoids a Jac codegen bug with `subprocess.run` kwargs) by running `api/_jac_worker_main.py`.

4. Health check:

```bash
curl http://localhost:8000/health
```

5. **Synchronous ticker verdicts** (same Jac graph as async runs; can take minutes per ticker — increase proxy timeouts on hosted platforms):

```bash
curl -sS -X POST http://localhost:8000/v1/analyze-tickers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"tickers":["NVDA","AAPL"]}'
```

`POST /analyze` is an alias for the same handler. Response shape:

```json
{
  "status": "success",
  "data": [
    {
      "ticker": "NVDA",
      "verdict": "buy with conditions",
      "confidence": 67,
      "rationale": "...",
      "condition": "...",
      "judge_confidence": 67,
      "bull_argument": "...",
      "bull_confidence": 81,
      "bear_argument": "...",
      "bear_confidence": 61
    }
  ],
  "portfolio_meta": { "annotation": "...", "correlated_theme": "...", "hedging_gaps": "...", "portfolio_conviction": "..." }
}
```

`portfolio_meta` is `null` if the portfolio meta agent fails or is unavailable.

## Additional API endpoints

6. **Portfolio-level analysis** (async with polling):

```bash
# Submit a run
curl -sS -X POST http://localhost:8000/v1/analysis-runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{
    "portfolio": {
      "holdings": [{"ticker": "NVDA", "weight": 0.4}, {"ticker": "AAPL", "weight": 0.6}],
      "as_of_date": "2026-04-05"
    }
  }'
# Returns: {"run_id": "...", "status": "queued", "created_at": "..."}

# Poll for results
curl -sS http://localhost:8000/v1/analysis-runs/{run_id} \
  -H "X-API-Key: dev-secret"
# Returns: {"run_id", "status", "progress", "portfolio_summary", "result", "error", "started_at", "finished_at"}

# Poll event stream (cursor-based)
curl -sS "http://localhost:8000/v1/analysis-runs/{run_id}/events?cursor=0" \
  -H "X-API-Key: dev-secret"
# Returns: {"run_id", "events": [...], "next_cursor": 5}
```

7. **Natural language Q&A** over analysis results:

```bash
curl -sS -X POST http://localhost:8000/v1/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"question": "Why should I avoid TSLA?", "results": [...]}'
# Returns: {"status": "success", "data": "..."}
```

Pass the `results` array from a prior `/v1/analyze-tickers` response. The query walker traverses the analysis data to answer freeform questions.

8. **Historical prices** (yfinance):

```bash
curl -sS "http://localhost:8000/v1/historical-prices/NVDA?period=1y" \
  -H "X-API-Key: dev-secret"
# Returns: {"ticker": "NVDA", "prices": [...]}
```

Valid `period` values: `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y` (default: `1y`).

## Environment variables

- `ALPHAWALKER_API_KEY`: shared secret expected in the `X-API-Key` header
- `ALPHAWALKER_DB_PATH`: optional path for SQLite persistence, defaults to `data/analysis_runs.db`
- `ALPHAWALKER_USE_JAC`: `1` (default) runs the real Jac graph via `alphawalker_pipeline.jac` in a subprocess; set `0` to use the lightweight rule-based engine only (good for CI or demos without LLM keys)
- `ALPHAWALKER_JAC_FALLBACK`: `1` (default) falls back to the rule engine if the Jac subprocess errors (missing `jaclang`, LLM auth, timeout)
- `ALPHAWALKER_JAC_TIMEOUT`: seconds for the Jac worker (default `900`)
- `OPENAI_API_KEY`: required for LLM calls when Jac is enabled. Works with OpenAI, OpenRouter, or any OpenAI-compatible provider. The `.env.example` defaults to OpenRouter (`https://openrouter.ai/api/v1`)
- `OPENAI_BASE_URL` / `OPENAI_API_BASE`: optional; set to the provider’s OpenAI-compatible endpoint (OpenRouter, Ollama, etc.)
- `OPENAI_MODEL`: optional model identifier (e.g., `openai/gpt-5.4-mini`); useful when routing through OpenRouter or specifying a non-default model
- `INSFORGE_URL`: optional; base URL for the Insforge cloud database (e.g., `https://your-project.us-east.insforge.app`). When set along with `INSFORGE_SERVICE_KEY`, analysis runs and ticker verdicts are persisted to the cloud for the History tab
- `INSFORGE_SERVICE_KEY`: optional; service-level API key for Insforge write operations. If either Insforge var is missing, the backend operates in local-only mode

### Ollama instead of OpenAI

1. Install [Ollama](https://ollama.com/) and pull a model, e.g. `ollama pull llama3.2`.
2. Ensure the API server can reach Ollama (same machine: `http://127.0.0.1:11434`; Docker: use host networking or the service URL).
3. Point the OpenAI-compatible client at Ollama (typical pattern):

```bash
export OPENAI_BASE_URL=http://127.0.0.1:11434/v1
export OPENAI_API_KEY=ollama
```

Local Ollama usually ignores the key; **Ollama Cloud** (if you use it) may require a real key—set whatever that product documents (e.g. `OLLAMA_API_KEY`) in the same environment as `uvicorn`.

4. If outputs still hit the wrong model, check [Jac byLLM usage](https://jac-lang.org/learn/jac-byllm/usage) for how to pin an `ollama/...` model for your `jaclang` version.

Do not commit `.env` or any file containing secrets.

## Managed host notes

- Railway, Render, and Fly.io can run: `uvicorn api.main:app --host 0.0.0.0 --port $PORT` (use `$PORT` where the platform provides it).
- Set **the same** env vars on the host as locally (`ALPHAWALKER_API_KEY`, LLM/Ollama vars, optional `ALPHAWALKER_DB_PATH`).
- Jac runs are slow; raise HTTP/proxy timeouts on the host (often 60s+ default is too low for `/v1/analyze-tickers`).
- Persist `data/analysis_runs.db` on a mounted volume if you want SQLite run history across deploys.
- For the React frontend, run `npm run build` inside `frontend/` and serve `frontend/dist/` as static files, or deploy it separately (Netlify, Vercel, etc.) pointed at the hosted API URL.
