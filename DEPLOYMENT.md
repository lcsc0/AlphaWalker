# AlphaWalker API Deployment

## Local run

1. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

2. Start the API:

```bash
ALPHAWALKER_API_KEY=dev-secret uvicorn api.main:app --host 0.0.0.0 --port 8000
```

The `api` package is implemented in `.jac` files; `jaclang` (pulled in by `requirements.txt`) registers an import hook so `api.main:app` resolves to the compiled FastAPI app. `api/__init__.py` imports `jaclang` first so `import api.*` works from any entrypoint. The Jac graph subprocess runs `api/_jac_worker_main.py` as a script (invoked by absolute path from `api/jac_bridge.jac`) so `os`/`pathlib` and `__main__` behave like normal CPython.

3. Health check:

```bash
curl http://localhost:8000/health
```

4. **Synchronous ticker verdicts** (same Jac graph as async runs; can take minutes per ticker — increase proxy timeouts on hosted platforms):

```bash
curl -sS -X POST http://localhost:8000/v1/analyze-tickers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: dev-secret" \
  -d '{"tickers":["NVDA","AAPL"]}'
```

`POST /analyze` is an alias for the same handler. Response shape: `{"status":"success","data":[{ "ticker", "verdict", "confidence", "rationale", "condition", "judge_confidence", ... }]}`.

## Environment variables

- `ALPHAWALKER_API_KEY`: shared secret expected in the `X-API-Key` header
- `ALPHAWALKER_DB_PATH`: optional path for SQLite persistence, defaults to `data/analysis_runs.db`
- `ALPHAWALKER_USE_JAC`: `1` (default) runs the real Jac graph via `alphawalker_pipeline.jac` in a subprocess; set `0` to use the lightweight rule-based engine only (good for CI or demos without LLM keys)
- `ALPHAWALKER_JAC_FALLBACK`: `1` (default) falls back to the rule engine if the Jac subprocess errors (missing `jaclang`, LLM auth, timeout)
- `ALPHAWALKER_JAC_TIMEOUT`: seconds for the Jac worker (default `900`)
- `OPENAI_API_KEY`: required for LLM-backed agents when Jac is enabled (same as `jac run main.jac`)

## Managed host notes

- Railway, Render, and Fly.io can all run this service with `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Persist `data/analysis_runs.db` on a mounted volume if you want run history to survive redeploys
- **Base44** calls this API from backend functions (`base44/functions/`); keep `ALPHAWALKER_API_BASE_URL` pointed at this deployment
