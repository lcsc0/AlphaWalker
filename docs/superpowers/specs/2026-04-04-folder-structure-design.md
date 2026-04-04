# AlphaWalker — Folder Structure Design

**Date:** 2026-04-04
**Status:** Approved

---

## Context

AlphaWalker is a multi-agent investment research system built in Jac (Object Spatial Programming). The system runs two adversarial agent coalitions (Bull and Bear) against each portfolio asset, surfaces their structured arguments to a Judge Agent, and outputs an investment committee memo. Additional layers include a Portfolio Meta Agent for cross-asset reasoning, temporal graph snapshots for signal evolution tracking, agent confidence scoring, and a natural language Query Walker.

No code exists yet. This spec defines only the folder and file structure.

---

## Decisions

| Question | Decision |
|---|---|
| Language | Pure Jac (.jac only, no Python) |
| File granularity | One file per agent |
| Structure approach | Hybrid: coalition-grouped agents + separate graph/, prompts/, output/ top-level folders |
| Tests | Scaffolded now, mirroring agents/ structure |

---

## Approved Structure

```
AlphaWalker/
├── README.md
├── main.jac                              # Entry point — loads portfolio, seeds graph, spawns walkers
│
├── graph/
│   ├── nodes.jac                         # node Asset, BullNode, BearNode, PortfolioNode, TemporalSnapshot
│   └── edges.jac                         # edge types: HasCoalition, HasSnapshot, BelongsToPortfolio
│
├── agents/
│   ├── bull/
│   │   ├── bull_news_agent.jac           # walker: positive news catalysts, analyst upgrades
│   │   ├── bull_quant_agent.jac          # walker: bullish technicals, earnings momentum
│   │   └── bull_macro_agent.jac          # walker: sector tailwinds, favorable macro conditions
│   ├── bear/
│   │   ├── bear_news_agent.jac           # walker: negative headlines, insider selling, risk events
│   │   ├── bear_quant_agent.jac          # walker: overvaluation, broken technicals, margin compression
│   │   └── bear_macro_agent.jac          # walker: macro headwinds, rate sensitivity, sector rotation
│   ├── judge_agent.jac                   # walker: reads both sides, weights by confidence, renders verdict
│   ├── portfolio_meta_agent.jac          # walker: traverses all assets, surfaces concentration & correlation
│   └── query_walker.jac                  # walker: NL Q&A — traverses graph to answer freeform questions
│
├── prompts/
│   ├── bull_prompts.jac                  # by llm() directives: "build strongest possible buy case"
│   ├── bear_prompts.jac                  # by llm() directives: "find every reason to avoid this asset"
│   ├── judge_prompts.jac                 # synthesis prompts, confidence weighting, verdict formatting
│   └── query_prompts.jac                 # NL answer generation from graph node annotations
│
├── output/
│   └── memo_formatter.jac                # formats verdict data into investment committee memo structure
│
└── tests/
    ├── bull/
    │   ├── test_bull_news_agent.jac
    │   ├── test_bull_quant_agent.jac
    │   └── test_bull_macro_agent.jac
    ├── bear/
    │   ├── test_bear_news_agent.jac
    │   ├── test_bear_quant_agent.jac
    │   └── test_bear_macro_agent.jac
    ├── test_judge_agent.jac
    ├── test_portfolio_meta_agent.jac
    └── test_query_walker.jac
```

---

## File Responsibilities

### `main.jac`
Entry point. Accepts a list of tickers, seeds an Asset node per ticker, attaches Bull and Bear coalition nodes, and spawns the BullWalker and BearWalker concurrently. After both complete, spawns JudgeWalker per asset, then PortfolioMetaAgent across all assets. Outputs final memos.

### `graph/nodes.jac`
All `node` definitions:
- `Asset` — ticker, price, current and historical coalition findings
- `BullNode` / `BearNode` — coalition attachment points, store structured arguments and confidence scores
- `TemporalSnapshot` — timestamped copy of coalition state per run (enables momentum detection)
- `PortfolioNode` — root node connecting all assets, used by PortfolioMetaAgent

### `graph/edges.jac`
All `edge` definitions:
- `HasCoalition` — Asset → BullNode / BearNode
- `HasSnapshot` — BullNode/BearNode → TemporalSnapshot (append-only history)
- `BelongsToPortfolio` — Asset → PortfolioNode

### `agents/bull/` and `agents/bear/`
Six sub-agent walkers (three per coalition). Each uses `by llm()` with prompts imported from `prompts/`. Each deposits findings + a confidence score (0–100) onto its coalition node before disengaging.

### `agents/judge_agent.jac`
Reads BullNode and BearNode findings, traverses TemporalSnapshot history for momentum detection, weights arguments by confidence score, and produces a structured verdict. Flags `INSUFFICIENT DATA` when both coalition confidence scores fall below threshold.

### `agents/portfolio_meta_agent.jac`
Traverses all Asset nodes via the PortfolioNode. Reasons about sector concentration, correlated bull signals, and hedging gaps. Does not modify individual asset verdicts — appends a portfolio-level annotation.

### `agents/query_walker.jac`
Accepts a natural language question string, identifies relevant Asset and coalition nodes, traverses them, and generates a plain English explanation using `by llm()` with context from graph annotations.

### `prompts/`
All `by llm()` prompt strings live here, separated from agent logic. This keeps agent files focused on traversal behavior and makes prompt iteration fast without touching walker code.

### `output/memo_formatter.jac`
Takes structured verdict data from JudgeAgent and PortfolioMetaAgent and formats it into the investment committee memo output (bull case, bear case, signal trend, ruling, confidence score, conditions).
