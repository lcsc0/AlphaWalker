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

3. Health check:

```bash
curl http://localhost:8000/health
```

## Environment variables

- `ALPHAWALKER_API_KEY`: shared secret expected in the `X-API-Key` header
- `ALPHAWALKER_DB_PATH`: optional path for SQLite persistence, defaults to `data/analysis_runs.db`

## Managed host notes

- Railway, Render, and Fly.io can all run this service with `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Persist `data/analysis_runs.db` on a mounted volume if you want run history to survive redeploys
- The current engine is a deterministic fallback designed to keep the Base44 contract stable until a deployable Jac runtime adapter is wired in
