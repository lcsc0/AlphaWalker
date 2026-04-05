"""Subprocess bridge for the portfolio rebalance agent."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger("api.rebalance_bridge")


def _default_repo_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def run_rebalance(
    tickers: list[str],
    portfolio_annotation: dict[str, str],
    results: list[dict[str, Any]] | None = None,
    repo_root: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any] | None:
    """Run the rebalance agent in a subprocess and return the result dict.

    Returns a dict with keys:
      gap_summary: str
      picks: list of up to 3 pick dicts
    Returns None on any failure (non-fatal — caller handles gracefully).
    """
    root = repo_root if repo_root is not None else _default_repo_root()
    to = timeout if timeout is not None else float(
        os.getenv("ALPHAWALKER_REBALANCE_TIMEOUT", "180")
    )

    # Build verdicts summary from results for additional LLM context
    verdicts_summary = ""
    if results:
        lines = []
        for r in results:
            ticker = r.get("ticker", "")
            verdict = r.get("verdict", "no verdict")
            conf = r.get("judge_confidence", 0)
            lines.append(f"{ticker}: {verdict} ({conf}% confidence)")
        verdicts_summary = "; ".join(lines)

    payload = {
        "tickers": tickers,
        "correlated_theme": portfolio_annotation.get("correlated_theme", ""),
        "hedging_gaps": portfolio_annotation.get("hedging_gaps", ""),
        "portfolio_conviction": portfolio_annotation.get("portfolio_conviction", ""),
        "verdicts_summary": verdicts_summary,
    }

    here = os.path.dirname(__file__)
    worker_py = os.path.join(here, "_jac_rebalance_worker.py")
    cmd = [sys.executable, worker_py, json.dumps(payload)]
    new_env = os.environ.copy()
    new_env["PYTHONUTF8"] = "1"

    proc = subprocess.run(
        cmd,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=to,
        env=new_env,
        check=False,
    )

    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip()
        err = err[:2000] if len(err) > 2000 else err
        logger.error("Rebalance worker failed: %s", err)
        return None

    raw = (proc.stdout or "").strip()
    if not raw:
        logger.warning("Rebalance worker produced empty stdout")
        return None

    # Grab the last JSON object line in case there's debug output before it
    data = None
    for line in reversed(raw.splitlines()):
        s = line.strip()
        if s.startswith("{"):
            try:
                data = json.loads(s)
                break
            except Exception:
                continue
    if data is None:
        try:
            data = json.loads(raw)
        except Exception:
            logger.warning("Rebalance worker output was not valid JSON: %s", raw[:500])
            return None

    return data
