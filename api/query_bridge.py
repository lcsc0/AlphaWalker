"""Subprocess bridge for the natural-language query pipeline."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger("api.query_bridge")


def _default_repo_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def run_query(
    question: str,
    results: list[dict[str, Any]],
    repo_root: str | None = None,
    timeout: float | None = None,
) -> dict[str, Any]:
    """Run the Jac query pipeline in a subprocess and return the answer dict."""
    root = repo_root if repo_root is not None else _default_repo_root()
    to = timeout if timeout is not None else float(os.getenv("ALPHAWALKER_QUERY_TIMEOUT", "120"))

    here = os.path.dirname(__file__)
    worker_py = os.path.join(here, "_jac_query_worker.py")
    payload = json.dumps({"question": question, "results": results})
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
        if not err:
            err = f"exit {proc.returncode}"
        logger.error("Query worker failed: %s", err)
        raise RuntimeError(f"Query pipeline failed: {err[:500]}")

    raw = (proc.stdout or "").strip()
    if not raw:
        raise RuntimeError("Query pipeline produced empty stdout")

    # Grab the last JSON object line in case there's debug output before it
    data = None
    for line in reversed(raw.splitlines()):
        s = line.strip()
        if s.startswith("{"):
            data = json.loads(s)
            break
    if data is None:
        data = json.loads(raw)

    return data
