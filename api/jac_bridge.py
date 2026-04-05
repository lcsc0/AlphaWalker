"""Subprocess bridge to the Jac graph pipeline (avoids sharing JacRuntime across FastAPI threads).

Each ticker is run in its own isolated subprocess so all tickers are analysed
concurrently. Results are merged and returned in the original ticker order.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

logger = logging.getLogger("api.jac_bridge")


def _default_repo_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def _run_single_ticker(
    ticker: str,
    repo_root: str,
    timeout: float,
) -> dict[str, Any]:
    """Run the Jac pipeline for one ticker in a subprocess and return its result dict."""
    here = os.path.dirname(__file__)
    worker_py = os.path.join(here, "_jac_worker_main.py")
    payload = json.dumps([ticker])
    cmd = [sys.executable, worker_py, payload]
    new_env = os.environ.copy()
    new_env["PYTHONUTF8"] = "1"

    proc = subprocess.run(
        cmd,
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=new_env,
        check=False,
    )

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        err = err[:2000] if len(err) > 2000 else err
        if not err:
            err = f"exit {proc.returncode}"
        logger.error("Jac worker failed for %s: %s", ticker, err)
        raise RuntimeError(f"Jac pipeline failed for {ticker}: {err[:500]}")

    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError(f"Jac pipeline produced empty stdout for {ticker}")

    # Worker may print graph node reprs before the JSON line — grab the last JSON array line.
    data = None
    for line in reversed(raw.splitlines()):
        s = line.strip()
        if s.startswith("["):
            data = json.loads(s)
            break
    if data is None:
        data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError(f"Jac pipeline must return a JSON array (got {type(data)})")

    return data[0] if data else {}


def run_jac_pipeline(
    tickers: list[str],
    repo_root: str | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    """Run the Jac bull/bear pipeline for all tickers, concurrently one subprocess per ticker."""
    root = repo_root if repo_root is not None else _default_repo_root()
    to = timeout if timeout is not None else float(os.getenv("ALPHAWALKER_JAC_TIMEOUT", "900"))

    tickers_norm: list[str] = [t.strip().upper() for t in tickers if t and t.strip()]
    if not tickers_norm:
        return []

    # Single ticker — skip thread overhead
    if len(tickers_norm) == 1:
        result = _run_single_ticker(tickers_norm[0], root, to)
        return [result] if result else []

    # Multiple tickers — run each in its own subprocess concurrently, preserve order
    results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    max_workers = min(len(tickers_norm), int(os.getenv("ALPHAWALKER_MAX_PARALLEL", "6")))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        future_to_ticker = {
            pool.submit(_run_single_ticker, ticker, root, to): ticker
            for ticker in tickers_norm
        }
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            try:
                results[ticker] = future.result()
            except Exception as exc:
                logger.error("Ticker %s failed: %s", ticker, exc)
                errors.append(f"{ticker}: {exc}")
                results[ticker] = {
                    "ticker": ticker,
                    "verdict": "error",
                    "judge_confidence": 0,
                    "rationale": str(exc),
                    "condition": "",
                    "bull_argument": "",
                    "bull_confidence": 0,
                    "bear_argument": "",
                    "bear_confidence": 0,
                }

    if errors:
        logger.warning("Some tickers failed: %s", "; ".join(errors))

    # Return in original request order
    return [results[t] for t in tickers_norm if t in results]
