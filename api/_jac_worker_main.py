"""Run `alphawalker_pipeline.run_pipeline_for_tickers` in an isolated process (one invocation per analysis).

Jac source of truth for review: `api/_jac_worker_main.jac`. This small Python module is kept so
`python -m api._jac_worker_main` works reliably with `os`/`pathlib` interop from CPython.

Usage: python -m api._jac_worker_main '["NVDA","AAPL"]'
Stdout: JSON array of per-ticker agent outputs.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("[]", end="")
        sys.exit(2)
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    tickers: list[str] = json.loads(sys.argv[1])
    if not tickers:
        print("[]", end="")
        return

    import jaclang  # noqa: F401 — registers .jac import hook

    from jaclang.jac0core.runtime import JacRuntime as Jac

    Jac.setup()
    import importlib

    mod = importlib.import_module("alphawalker_pipeline")
    raw: str = mod.run_pipeline_for_tickers(tickers)
    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
