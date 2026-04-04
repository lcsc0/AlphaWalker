# AlphaWalker

> Two AI agent teams debate every stock in your portfolio — one tries to convince you to buy, one tries to convince you to sell, and a judge agent makes the final call.

---

## Overview

AlphaWalker is a multi-agent investment research system built on [Jac](https://www.jac-lang.org/). It takes a portfolio or watchlist of tickers and runs them through a structured adversarial debate between two opposing AI agent coalitions. Rather than producing a simple buy/sell signal, it produces an investment committee memo — the bull case, the bear case, and a reasoned ruling from a neutral judge.

The core insight is that LLMs are better at *arguing a position* than at hedging one. By forcing two coalitions to build the strongest possible opposing cases, the system surfaces real risk/reward asymmetry that a single balanced prompt would flatten out.

---

## Agent Architecture

### The Two Coalitions

AlphaWalker spawns two coalitions simultaneously. They are structurally identical — same internal agents, same graph positions — but prompted with directly opposing directives.

#### Bull Coalition
*Directive: Build the strongest possible case for buying this asset.*

| Agent | Role |
|---|---|
| `BullNewsAgent` | Scans recent news for positive catalysts — earnings beats, product launches, partnerships, analyst upgrades |
| `BullQuantAgent` | Reads price action, momentum indicators, and earnings trends for bullish technicals and fundamental signals |
| `BullMacroAgent` | Identifies favorable macro conditions — rate environment, sector tailwinds, capital flow trends |

#### Bear Coalition
*Directive: Find every reason to avoid or sell this asset.*

| Agent | Role |
|---|---|
| `BearNewsAgent` | Surfaces negative headlines — regulatory risk, litigation, insider selling, management turnover |
| `BearQuantAgent` | Flags valuation excess, deteriorating margins, earnings misses, or broken technicals |
| `BearMacroAgent` | Identifies macro headwinds — sector rotation out, rate sensitivity, geopolitical exposure |

#### Judge Agent
*Directive: Read both arguments. Weigh evidence quality. Render a verdict.*

The `JudgeAgent` is a neutral synthesis walker. It does not conduct its own research — it reads the structured arguments deposited by both coalitions and evaluates:
- Which side made the stronger evidentiary case
- Whether the risks cited by the bear are already priced in
- Whether the bull's thesis depends on assumptions that could fail

**Possible verdicts:** `conviction buy` | `buy with conditions` | `hold` | `avoid with conditions` | `conviction avoid` | `split decision`

---

## Agent Relationship Diagram

```
                        ┌─────────────────┐
          Input ──────► │   Asset Node    │ ◄─────── Input
                        │   (e.g. NVDA)   │
                        └────────┬────────┘
                                 │
               ┌─────────────────┼─────────────────┐
               │                                   │
        ┌──────▼──────┐                     ┌──────▼──────┐
        │  Bull Node  │                     │  Bear Node  │
        └──────┬──────┘                     └──────┬──────┘
               │                                   │
    ┌──────────┼──────────┐           ┌────────────┼────────────┐
    │          │          │           │            │            │
┌───▼───┐ ┌───▼───┐ ┌────▼───┐  ┌───▼───┐  ┌────▼───┐ ┌──────▼──┐
│ Bull  │ │ Bull  │ │  Bull  │  │ Bear  │  │  Bear  │ │  Bear   │
│ News  │ │ Quant │ │ Macro  │  │ News  │  │  Quant │ │  Macro  │
│ Agent │ │ Agent │ │ Agent  │  │ Agent │  │  Agent │ │  Agent  │
└───────┘ └───────┘ └────────┘  └───────┘  └────────┘ └─────────┘
               │                                   │
               └─────────────────┬─────────────────┘
                                 │
                         ┌───────▼───────┐
                         │  Judge Agent  │
                         │  (synthesis   │
                         │   walker)     │
                         └───────┬───────┘
                                 │
                         ┌───────▼───────┐
                         │    Verdict    │
                         │  + Memo Out   │
                         └───────────────┘
```

Both coalitions traverse the graph **simultaneously and independently**. The `JudgeAgent` only traverses after both coalitions have deposited their findings onto the asset node.

---

## The Debate Flow

```
1. INPUT
   User provides a list of tickers (e.g. NVDA, AAPL, TSLA)

2. GRAPH SPAWN
   An Asset node is created for each ticker
   Bull and Bear nodes are attached on opposing sides of each Asset node

3. PARALLEL COALITION SWEEP
   BullWalker and BearWalker traverse simultaneously
   Each sub-agent (news, quant, macro) researches its domain
   Findings are deposited onto the coalition's node

4. ARGUMENT CONSTRUCTION
   Each coalition synthesizes its sub-agent findings into a
   structured argument using `by llm()` with argumentative prompting

   Bull on NVDA:
   "Forward P/E is justified by the AI infrastructure supercycle.
    Data center revenue up 400% YoY. No credible near-term competitor
    in GPU compute. Margin expansion trajectory intact..."

   Bear on NVDA:
   "Valuation is pricing in perfection. Export restrictions to China
    remain unresolved. Hyperscaler capex growth may slow in H2.
    Customer concentration risk in top 3 cloud providers..."

5. JUDGE TRAVERSAL
   JudgeAgent walks the graph, reads both structured arguments,
   evaluates evidence quality, and renders a verdict

6. OUTPUT
   Investment committee memo per ticker (see Output Format below)
```

---

## Output Format

AlphaWalker produces an **investment committee memo** rather than a signal table. Each ticker gets:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TICKER: NVDA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BULL CASE
─────────
[BullNewsAgent]  Analyst upgrades from 3 major banks this week.
                 Jensen Huang keynote confirmed new Blackwell ramp.
[BullQuantAgent] RSI reset from overbought; EPS growth 265% YoY.
[BullMacroAgent] AI capex still in early innings; sovereign wealth
                 funds increasing tech allocation.

BEAR CASE
─────────
[BearNewsAgent]  DOJ antitrust inquiry opened. Taiwan strait
                 tension elevated this quarter.
[BearQuantAgent] P/S ratio at 25x — 2 std deviations above 3yr mean.
                 Options market implying 8% weekly moves.
[BearMacroAgent] Fed holding rates higher for longer compresses
                 long-duration tech multiples.

JUDGE'S RULING
──────────────
Verdict:         BUY WITH CONDITIONS
Confidence:      67%
Rationale:       Bull thesis rests on durable structural tailwinds
                 that bear has not credibly refuted. Valuation risk
                 is real but secondary to earnings trajectory.
                 Recommended sizing: reduced vs. full conviction.
Condition:       Revisit if hyperscaler capex guidance cuts >15%
                 in next earnings cycle.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Persistent Learning

AlphaWalker's graph is persistent across runs. Each week the system:

1. Records the coalition positions (bull/bear) and the judge's verdict per ticker
2. Tracks subsequent price performance as ground truth
3. Scores each coalition on prediction accuracy over a rolling window

Over time, the coalition with the better historical track record **per ticker** gets weighted more heavily by the judge. A bull coalition that has been right on NVDA 7 of the last 10 times carries more credibility than one that has been right 4 of 10.

This creates a system that doesn't just reason — it learns which side to trust.

---

## Jac / OSP Architecture

AlphaWalker maps cleanly onto Jac's Object Spatial Programming model:

| Concept | Jac Implementation |
|---|---|
| Asset node | `node asset` with ticker, price data, and attached coalition findings |
| Bull/Bear positioning | Bull and Bear nodes on opposite edges of each Asset node |
| Coalition research | Walkers (`BullWalker`, `BearWalker`) traversing simultaneously |
| LLM-powered argumentation | `by llm()` with directed argumentative system prompts |
| Judge synthesis | `JudgeWalker` as a final traversal that reads both sides before disengaging |
| Historical learning | Persisted edge weights updated after each weekly run |

The declarative nature of Jac means agent roles and graph topology are defined structurally — orchestration is handled by the runtime, not imperative control flow.

---

## The Pitch

> "Two AI agent teams debate every stock in your portfolio — one tries to convince you to buy, one tries to convince you to sell, and a judge agent makes the final call."
