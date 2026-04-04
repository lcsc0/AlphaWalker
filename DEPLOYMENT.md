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

Most of `api` is implemented in `.jac` files; `jaclang` registers an import hook so `api.main:app` resolves to the compiled FastAPI app. `api/__init__.py` imports `jaclang` first so `import api.*` works from any entrypoint. The Jac graph subprocess is spawned from `api/jac_bridge.py` (Python; avoids a Jac codegen bug with `subprocess.run` kwargs) by running `api/_jac_worker_main.py`.

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
- `OPENAI_API_KEY`: required for **OpenAI** (or other providers your Jac `by llm()` stack expects) when Jac is enabled
- `OPENAI_BASE_URL` / `OPENAI_API_BASE`: optional; set to Ollama’s OpenAI-compatible endpoint when using local Ollama (see below)

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

Copy [.env.example](.env.example) to `.env`, fill in values, and **do not commit** `.env`.

## Managed host notes (step 2 — public URL)

- Railway, Render, and Fly.io can run: `uvicorn api.main:app --host 0.0.0.0 --port $PORT` (use `$PORT` where the platform provides it).
- Set **the same** env vars on the host as locally (`ALPHAWALKER_API_KEY`, LLM/Ollama vars, optional `ALPHAWALKER_DB_PATH`).
- Jac runs are slow; raise HTTP/proxy timeouts on the host (often 60s+ default is too low for `/v1/analyze-tickers`).
- Persist `data/analysis_runs.db` on a mounted volume if you want SQLite run history across deploys.
- **Base44 (step 3):** in the Base44 project, set secrets `ALPHAWALKER_API_BASE_URL` (your public `https://...` with **no** trailing slash) and `ALPHAWALKER_API_KEY` (must match `ALPHAWALKER_API_KEY` on the API host). See [base44/README.md](base44/README.md).

## Base44 code: keep in repo vs only in Base44

The TypeScript in [base44/functions/](base44/functions/) is already in this repo as a **template** you can version and edit in git. Base44 still needs a **copy** of those functions inside the Base44 app to execute them; the platform does not pull from GitHub automatically unless you set that up. Practical approach: treat this folder as source of truth, then paste or sync into Base44 when you change behavior—**copying the whole generated Base44 app** into this monorepo is optional and mainly helps if you want one git tree for UI + API; it does not replace deploying both sides.
