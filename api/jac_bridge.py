"""Subprocess bridge to the Jac graph pipeline (avoids sharing JacRuntime across FastAPI threads).

Implemented in Python because Jac currently miscompiles keyword arguments to subprocess.run
(`cwd=root` becomes a call to root()).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

logger = logging.getLogger("api.jac_bridge")


def _default_repo_root() -> str:
    here = os.path.dirname(__file__)
    return os.path.abspath(os.path.join(here, ".."))


def run_jac_pipeline(
    tickers: list[str],
    repo_root: str | None = None,
    timeout: float | None = None,
) -> list[dict[str, Any]]:
    root = repo_root if repo_root is not None else _default_repo_root()
    to = timeout if timeout is not None else float(os.getenv("ALPHAWALKER_JAC_TIMEOUT", "900"))
    tickers_norm: list[str] = []
    for t in tickers:
        if t and t.strip() != "":
            tickers_norm.append(t.strip().upper())
    if len(tickers_norm) == 0:
        return []

    payload = json.dumps(tickers_norm)
    here = os.path.dirname(__file__)
    worker_py = os.path.join(here, "_jac_worker_main.py")
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
        if err == "":
            err = "exit " + str(proc.returncode)
        err = err[:2000] if len(err) > 2000 else err
        logger.error("Jac worker failed: %s", err)
        msg = err[:500] if len(err) > 500 else err
        raise RuntimeError("Jac pipeline failed: " + msg)
    raw = (proc.stdout or "").strip()
    if raw == "":
        raise RuntimeError("Jac pipeline produced empty stdout")
    # Worker may print graph node reprs to stdout before the JSON line.
    data = None
    for line in reversed(raw.splitlines()):
        s = line.strip()
        if s.startswith("["):
            data = json.loads(s)
            break
    if data is None:
        data = json.loads(raw)
    if not isinstance(data, list):
        raise TypeError("Jac pipeline must return a JSON array")
    return data
