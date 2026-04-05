"""Run the two-phase rebalance pipeline in an isolated process.

Usage: python -m api._jac_rebalance_worker '<json>'
Input JSON: {
  "tickers": ["NVDA", "AMD", ...],
  "correlated_theme": "...",
  "hedging_gaps": "...",
  "portfolio_conviction": "...",
  "verdicts_summary": "..."
}
Stdout: JSON object {"gap_summary": "...", "picks": [...3 picks...]}
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

    payload: dict = json.loads(sys.argv[1])
    existing_tickers: list[str] = payload.get("tickers", [])
    correlated_theme: str = payload.get("correlated_theme", "")
    hedging_gaps: str = payload.get("hedging_gaps", "")
    portfolio_conviction: str = payload.get("portfolio_conviction", "")
    verdicts_summary: str = payload.get("verdicts_summary", "")

    import jaclang  # noqa: F401 — registers .jac import hook

    from jaclang.jac0core.runtime import JacRuntime as Jac

    Jac.setup()
    import importlib

    runner = importlib.import_module("api.rebalance_runner")

    # ── Phase 1: LLM generates candidate tickers ──────────────────────────────
    candidates_json_str: str = runner.run_generate_candidates(
        existing_tickers=", ".join(existing_tickers),
        correlated_theme=correlated_theme,
        hedging_gaps=hedging_gaps,
        portfolio_conviction=portfolio_conviction,
        verdicts_summary=verdicts_summary,
    )

    # Parse candidate list — LLM may wrap in markdown fences, strip them
    raw_candidates = candidates_json_str.strip()
    if raw_candidates.startswith("```"):
        lines = raw_candidates.splitlines()
        raw_candidates = "\n".join(
            l for l in lines if not l.startswith("```")
        ).strip()

    try:
        candidates: list[dict] = json.loads(raw_candidates)
    except Exception:
        # If LLM output is unparseable, return empty result
        print(json.dumps({"gap_summary": "", "picks": []}), end="")
        return

    # ── Phase 2: Fetch real yfinance signals for each candidate ───────────────
    from api.technical_signals import compute_signals_safe

    enriched_lines: list[str] = []
    for c in candidates:
        ticker = c.get("ticker", "").strip().upper()
        if not ticker:
            continue
        signals_str = compute_signals_safe(ticker)
        line = (
            f"TICKER: {ticker} | TYPE: {c.get('asset_type','?')} "
            f"| GAP: {c.get('gap_addressed','?')} "
            f"| SIGNALS: {signals_str or 'no data'}"
        )
        enriched_lines.append(line)

    candidates_with_signals = "\n\n".join(enriched_lines)

    # ── Phase 3: LLM ranks and selects top 3 ─────────────────────────────────
    rank_raw: str = runner.run_rank_recommendations(
        candidates_with_signals=candidates_with_signals
    )

    rank_data: dict = json.loads(rank_raw)
    gap_summary: str = rank_data.get("gap_summary", "")
    picks_json_str: str = rank_data.get("picks_json", "[]")

    raw_picks = picks_json_str.strip()
    if raw_picks.startswith("```"):
        lines = raw_picks.splitlines()
        raw_picks = "\n".join(
            l for l in lines if not l.startswith("```")
        ).strip()

    try:
        picks: list[dict] = json.loads(raw_picks)
    except Exception:
        picks = []

    # Attach the yfinance signals dict to each pick for the frontend
    signals_map: dict[str, dict] = {}
    for c in candidates:
        ticker = c.get("ticker", "").strip().upper()
        if ticker:
            from api.technical_signals import compute_signals

            try:
                signals_map[ticker] = compute_signals(ticker)
            except Exception:
                signals_map[ticker] = {}

    for pick in picks:
        t = (pick.get("ticker") or "").strip().upper()
        pick["ticker"] = t
        pick["signals"] = signals_map.get(t, {})

    result = {"gap_summary": gap_summary, "picks": picks}
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
