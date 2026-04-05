"""Subprocess bridge for the portfolio meta agent."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger("api.meta_bridge")


def _default_repo_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def run_meta(
    results: list[dict[str, Any]],
    repo_root: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any] | None:
    """Run the portfolio meta agent in a subprocess and return the annotation dict."""
    if len(results) < 2:
        return None  # Cross-asset analysis requires at least 2 tickers

    root = repo_root if repo_root is not None else _default_repo_root()
    to = timeout if timeout is not None else float(os.getenv("ALPHAWALKER_META_TIMEOUT", "120"))

    here = os.path.dirname(__file__)
    worker_py = os.path.join(here, "_jac_meta_worker.py")
    payload = json.dumps(results)
    cmd = [sys.executable, worker_py, payload]
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
        logger.error("Meta worker failed: %s", err)
        return None  # Non-fatal — analysis still succeeds without meta insight

    raw = (proc.stdout or "").strip()
    if not raw:
        logger.warning("Meta worker produced empty stdout")
        return None

    # Grab the last JSON object line in case there's debug output before it
    data = None
    for line in reversed(raw.splitlines()):
        s = line.strip()
        if s.startswith("{"):
            data = json.loads(s)
            break
    if data is None:
        try:
            data = json.loads(raw)
        except Exception:
            logger.warning("Meta worker output was not valid JSON")
            return None

    return data
