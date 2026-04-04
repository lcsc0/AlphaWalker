# AlphaWalker Graph Schema

The graph layer is the data backbone of AlphaWalker. It defines every node type and edge type that agent walkers traverse and populate during a research run.

---

## Nodes

### `PortfolioNode`

The root-level node for a portfolio. The `PortfolioMetaAgent` traverses outward from here to reason across all assets simultaneously — surfaces concentration risk, correlated bull signals, and hedging gaps that individual asset walkers cannot see.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `"default"` | Portfolio identifier |

---

### `Asset`

One node per ticker. The central hub for each stock — bull and bear coalition nodes attach to it on opposing sides, and the judge's verdict attaches after both coalitions complete.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ticker` | `str` | required | Ticker symbol, e.g. `"NVDA"` |
| `price` | `float` | `0.0` | Latest price (populated at run time) |
| `sector` | `str` | `""` | Sector label used by `PortfolioMetaAgent` for concentration analysis |

---

### `BullNode`

Stores the bull coalition's full research output for one asset. Each of the three bull sub-agents (news, quant, macro) deposits its finding and confidence score directly onto this node. After all three deposit, the coalition synthesizes a combined `argument` and overall `confidence`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `argument` | `str` | `""` | Synthesized bull case (populated by `BullWalker` after sub-agents complete) |
| `confidence` | `int` | `0` | Overall coalition confidence, 0–100 |
| `news_finding` | `str` | `""` | `BullNewsAgent` deposit — positive catalysts, analyst upgrades |
| `news_confidence` | `int` | `0` | `BullNewsAgent` confidence, 0–100 |
| `quant_finding` | `str` | `""` | `BullQuantAgent` deposit — bullish technicals, earnings momentum |
| `quant_confidence` | `int` | `0` | `BullQuantAgent` confidence, 0–100 |
| `macro_finding` | `str` | `""` | `BullMacroAgent` deposit — sector tailwinds, favorable macro |
| `macro_confidence` | `int` | `0` | `BullMacroAgent` confidence, 0–100 |

---

### `BearNode`

Identical structure to `BullNode` but carries the bear coalition's case. Populated by `BearNewsAgent`, `BearQuantAgent`, and `BearMacroAgent`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `argument` | `str` | `""` | Synthesized bear case |
| `confidence` | `int` | `0` | Overall coalition confidence, 0–100 |
| `news_finding` | `str` | `""` | `BearNewsAgent` deposit — negative headlines, regulatory risk |
| `news_confidence` | `int` | `0` | `BearNewsAgent` confidence, 0–100 |
| `quant_finding` | `str` | `""` | `BearQuantAgent` deposit — overvaluation, broken technicals |
| `quant_confidence` | `int` | `0` | `BearQuantAgent` confidence, 0–100 |
| `macro_finding` | `str` | `""` | `BearMacroAgent` deposit — macro headwinds, rate sensitivity |
| `macro_confidence` | `int` | `0` | `BearMacroAgent` confidence, 0–100 |

---

### `TemporalSnapshot`

An append-only record of a coalition's state at a specific run. Rather than overwriting `BullNode` or `BearNode` each run, a new `TemporalSnapshot` is created and connected via `HasSnapshot`. This gives the `JudgeAgent` a full history to detect momentum shifts — a bear coalition accelerating from weak to strong across four runs is itself a signal, independent of the current value.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timestamp` | `str` | `""` | ISO date of this run, e.g. `"2026-04-04"` |
| `run_number` | `int` | `0` | Sequential run counter |
| `side` | `str` | `""` | `"bull"` or `"bear"` |
| `argument` | `str` | `""` | Synthesized argument at time of snapshot |
| `confidence` | `int` | `0` | Overall coalition confidence at time of snapshot |
| `news_confidence` | `int` | `0` | News agent confidence at time of snapshot |
| `quant_confidence` | `int` | `0` | Quant agent confidence at time of snapshot |
| `macro_confidence` | `int` | `0` | Macro agent confidence at time of snapshot |

---

### `VerdictNode`

Stores the `JudgeAgent`'s ruling for one asset after reading both coalitions. Possible verdicts: `conviction buy`, `buy with conditions`, `hold`, `avoid with conditions`, `conviction avoid`, `split decision`, `INSUFFICIENT DATA`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `verdict` | `str` | `""` | Verdict string, e.g. `"BUY WITH CONDITIONS"` |
| `judge_confidence` | `int` | `0` | Judge's confidence in the ruling, 0–100 |
| `rationale` | `str` | `""` | Prose explanation of the ruling |
| `condition` | `str` | `""` | Watch conditions attached to the verdict (if any) |

---

## Edges

### `BelongsToPortfolio`

Connects an `Asset` to the `PortfolioNode`. The `PortfolioMetaAgent` traverses all assets by following these edges outward from `PortfolioNode`.

```
PortfolioNode --[BelongsToPortfolio]--> Asset
```

---

### `HasCoalition`

Connects an `Asset` to its `BullNode` and `BearNode`. The `side` field allows walkers to filter for one coalition specifically without visiting both.

```
Asset --[HasCoalition(side="bull")]--> BullNode
Asset --[HasCoalition(side="bear")]--> BearNode
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `side` | `str` | `""` | `"bull"` or `"bear"` — identifies which coalition this edge leads to |

---

### `HasSnapshot`

Connects a `BullNode` or `BearNode` to its `TemporalSnapshot` history. New snapshots are appended each run — existing ones are never mutated. The `JudgeAgent` traverses this chain across runs to detect directional acceleration.

```
BullNode --[HasSnapshot]--> TemporalSnapshot (run 1)
BullNode --[HasSnapshot]--> TemporalSnapshot (run 2)
BullNode --[HasSnapshot]--> TemporalSnapshot (run N)
```

---

### `HasVerdict`

Connects an `Asset` to its `VerdictNode` after the `JudgeAgent` completes traversal.

```
Asset --[HasVerdict]--> VerdictNode
```

---

## Full Graph Topology

```
root
└── PortfolioNode
    └──[BelongsToPortfolio]── Asset (e.g. NVDA)
                               ├──[HasCoalition(side="bull")]── BullNode
                               │                                 ├──[HasSnapshot]── TemporalSnapshot (run 1)
                               │                                 └──[HasSnapshot]── TemporalSnapshot (run N)
                               ├──[HasCoalition(side="bear")]── BearNode
                               │                                 ├──[HasSnapshot]── TemporalSnapshot (run 1)
                               │                                 └──[HasSnapshot]── TemporalSnapshot (run N)
                               └──[HasVerdict]── VerdictNode
```
