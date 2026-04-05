"""Run `api.meta_runner.run_meta_for_results` in an isolated process.

Usage: python -m api._jac_meta_worker '["result1", "result2", ...]'
Stdout: JSON object {"annotation": "...", "correlated_theme": "...", "hedging_gaps": "...", "portfolio_conviction": "..."}
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        print("{}", end="")
        sys.exit(2)

    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    results: list = json.loads(sys.argv[1])
    results_json: str = json.dumps(results)

    import jaclang  # noqa: F401 — registers .jac import hook

    from jaclang.jac0core.runtime import JacRuntime as Jac

    Jac.setup()
    import importlib

    mod = importlib.import_module("api.meta_runner")
    raw: str = mod.run_meta_for_results(results_json)
    sys.stdout.write(raw)


if __name__ == "__main__":
    main()
