# AlphaWalker

> Two AI agent teams debate every stock in your portfolio — one tries to convince you to buy, one tries to convince you to sell, and a judge agent makes the final call.

---

## Overview

AlphaWalker is a multi-agent investment research system built on [Jac](https://www.jac-lang.org/). It takes a portfolio or watchlist of tickers and runs them through a structured adversarial debate between two opposing AI agent coalitions. Rather than producing a simple buy/sell signal, it produces an investment committee memo — the bull case, the bear case, and a reasoned ruling from a neutral judge.

The core insight is that LLMs are better at *arguing a position* than at hedging one. By forcing two coalitions to build the strongest possible opposing cases, the system surfaces real risk/reward asymmetry that a single balanced prompt would flatten out.

---

## Quick Start

**Prerequisites:** Python 3.10+, Node 18+ (via nvm), an `OPENAI_API_KEY`.

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Install frontend dependencies
cd frontend && npm install && cd ..

# 3. Set your LLM key
export OPENAI_API_KEY=sk-...

# 4. Start everything
./start.sh
```

- Backend → `http://localhost:8000`
- Frontend → `http://localhost:3000`

**Manual start (two terminals):**

```bash
# Terminal 1 — backend
ALPHAWALKER_API_KEY=dev-secret uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev -- --port 3000
```

**CLI only (no frontend needed):**

```bash
jac run main.jac
```

---

## Web Dashboard

The React frontend (`frontend/`) provides a three-tab dashboard:

| Tab | Description |
|---|---|
| **Dashboard** | Compact verdict cards for all analyzed tickers — color-coded green/yellow/red |
| **Analysis** | Full breakdown: bull/bear confidence bar chart, judge radial gauge, expandable argument panels |
| **History** | Past analysis runs pulled from the Insforge database |

Enter a comma-separated list of tickers in the input bar (e.g. `NVDA, AAPL, TSLA`) and click **Analyze**. Results stream back from `POST /v1/analyze-tickers` and are persisted to an [Insforge](https://insforge.app) cloud database when `INSFORGE_URL` and `INSFORGE_SERVICE_KEY` are configured (see [DEPLOYMENT.md](DEPLOYMENT.md) for setup). The History tab reads from this database.

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

**Possible verdicts:** `conviction buy` | `buy with conditions` | `hold` | `avoid with conditions` | `conviction avoid` | `split decision` | `insufficient data`

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
   BullCoalitionWalker and BearCoalitionWalker traverse simultaneously
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

BULL CASE                                              [Coalition Confidence: 81%]
─────────
[BullNewsAgent  82%]  Analyst upgrades from 3 major banks this week.
                      Jensen Huang keynote confirmed new Blackwell ramp.
[BullQuantAgent 79%]  RSI reset from overbought; EPS growth 265% YoY.
[BullMacroAgent 83%]  AI capex still in early innings; sovereign wealth
                      funds increasing tech allocation.

BEAR CASE                                              [Coalition Confidence: 61%]
─────────
[BearNewsAgent  58%]  DOJ antitrust inquiry opened. Taiwan strait
                      tension elevated this quarter.
[BearQuantAgent 71%]  P/S ratio at 25x — 2 std deviations above 3yr mean.
                      Options market implying 8% weekly moves.
[BearMacroAgent 54%]  Fed holding rates higher for longer compresses
                      long-duration tech multiples.

SIGNAL TREND (last 4 runs)
──────────────────────────
Bull coalition: [strong → strong → strong → strong]  (stable)
Bear coalition: [weak   → weak   → moderate → strong] (accelerating ▲)

JUDGE'S RULING
──────────────
Verdict:         BUY WITH CONDITIONS
Confidence:      67%
Rationale:       Bull thesis rests on durable structural tailwinds
                 that bear has not credibly refuted. Valuation risk
                 is real but secondary to earnings trajectory.
                 Recommended sizing: reduced vs. full conviction.
Condition:       Bear momentum acceleration is a watch flag. Revisit
                 if bear coalition reaches strong for 2 consecutive runs
                 or hyperscaler capex guidance cuts >15%.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Advanced Features

### Temporal Graph — Signal Evolution Over Time

The graph is not a snapshot — it has a time dimension. Every walker pass timestamps its findings as a **new node** rather than overwriting the previous one. This means the graph accumulates a full history of how sentiment and signals evolved for each asset across runs.

This unlocks a qualitatively different class of reasoning. The `JudgeAgent` can now detect **momentum shifts** across time, not just evaluate the current state:

```
JudgeAgent on NVDA (run 7):
"Bear signals were weak and low-confidence 3 runs ago. They are now
 strong and high-confidence. That acceleration — independent of the
 current signal strength — is itself a sell signal. Deterioration
 in progress, not yet in price."
```

The temporal graph turns AlphaWalker from a point-in-time analyzer into a system that reasons about *direction and velocity* of sentiment change — a fundamentally richer data structure.

```
Asset Node (NVDA)
├── Run 1 (2026-03-14)  ──► BullNode [strong] / BearNode [weak]
├── Run 2 (2026-03-21)  ──► BullNode [strong] / BearNode [weak]
├── Run 3 (2026-03-28)  ──► BullNode [moderate] / BearNode [moderate]
├── Run 4 (2026-04-04)  ──► BullNode [weak] / BearNode [strong]  ◄── now
│
└── JudgeWalker reads the delta across runs, not just the latest state
```

---

### Portfolio-Level Meta Agent

Individual asset agents are blind to the portfolio as a whole. A ticker-level walker only sees one asset — it cannot know that you hold 7 semiconductor names, or that your bull signals are all correlated to the same macro factor.

The `PortfolioMetaAgent` is a walker that operates **one level up**, traversing all asset nodes simultaneously rather than diving into any single one. It reasons about:

- **Concentration risk** — sector, factor, or geographic clustering
- **Correlated bull signals** — when every holding is bullish for the same reason, that's a single bet, not a diversified portfolio
- **Hedging gaps** — assets that should offset each other but don't, given current signals
- **Portfolio-level conviction** — whether the judge's per-ticker rulings add up to a coherent allocation

```
PortfolioMetaAgent output:
"NVDA, AMD, AMAT, ASML, and TSM represent 61% of portfolio value.
 BullAgents across all five cite AI infrastructure capex as the
 primary thesis. This is not diversification — this is a single
 macro bet expressed five ways. A single hyperscaler capex miss
 would simultaneously invalidate the bull case for all five positions."
```

No individual asset agent can surface this. It is only visible to a walker that traverses the full portfolio graph.

---

### Agent Confidence and Dissent Scoring

When Bull and Bear agents deposit their findings, they also output a **confidence score** alongside their argument. This score reflects how much supporting evidence they were able to find — a news agent with three corroborating sources scores higher than one working from a single ambiguous headline.

The `JudgeAgent` uses these scores in two ways:

1. **Confidence-weighted ruling** — a high-confidence bull argument outweighs a low-confidence bear argument, even if the bear's prose sounds more alarming
2. **Epistemic humility flag** — when *both* sides return low confidence, the judge does not split the difference. It returns a distinct verdict:

```
JUDGE'S RULING
──────────────
Verdict:         INSUFFICIENT DATA — DO NOT TRADE
Bull Confidence: 28%  (limited recent coverage, thin data)
Bear Confidence: 31%  (no clear catalysts, speculation only)
Rationale:       Neither coalition found sufficient evidence to
                 build a credible case. Entering a position on
                 this data would be noise trading. Re-evaluate
                 after next earnings release.
```

This makes AlphaWalker feel production-grade rather than a system that always has an opinion. Knowing when *not* to act is as important as knowing when to act.

---

### Quantitative Technical Signals

Before quant agents run, AlphaWalker computes real technical signals from market data via `api/technical_signals.py` using yfinance:

- **RSI (14-day)** with overbought/oversold labels
- **50-day and 200-day moving averages** with crossover detection (golden cross, death cross, bullish/bearish alignment)
- **Realized volatility** (30-day annualized)
- **Price momentum** (1-month, 3-month, 6-month returns)

These signals are injected into the `quant_signals` field on each `Asset` node and passed to both `BullQuantAgent` and `BearQuantAgent` as factual foundation data. This ensures quant agents argue from computed numbers rather than relying on LLM training data for market prices.

---

### 12-Hour Verdict Cache

Repeated analysis of the same ticker within 12 hours returns cached results without re-running the agent pipeline. The cache is in-memory (per-process) and implemented in `api/verdict_cache.py`. This avoids redundant LLM calls during iterative portfolio exploration.

---

### Natural Language Portfolio Q&A

A `QueryWalker` accepts freeform natural language questions and answers them by traversing the live graph in real time. Rather than querying a static report, it reads the actual bull/bear annotations, temporal history, and judge rulings on demand.

```
User:  "Why does AlphaWalker think I should sell TSLA?"

QueryWalker traverses:
  ├── TSLA Asset Node
  ├── Bear Node (current run + 3 prior runs)
  ├── Bull Node (current run + confidence scores)
  └── Judge Node (verdict + rationale)

Response:
"The bear case on TSLA has strengthened over the last three runs.
 BearQuantAgent flags margin compression in the most recent quarter
 and an RSI that has failed to recover above 45 on two attempts.
 BearMacroAgent notes EV demand softness in Europe and China, where
 TSLA has meaningful revenue exposure. The bull case — brand loyalty
 and energy business optionality — was rated low confidence (33%)
 because supporting data is thin. The JudgeAgent ruled 'avoid with
 conditions' and flagged the bear momentum trend as the deciding factor."
```

This is the live demo moment: a judge or investor asks an unscripted question, and the system answers it by walking the graph in real time — not from a cached summary, but from the actual structured evidence each agent deposited.

---

## API

The FastAPI backend exposes the following endpoints (all accept an optional `X-API-Key` header):

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/v1/analyze-tickers` | POST | Synchronous ticker analysis (main endpoint) |
| `/analyze` | POST | Alias for `/v1/analyze-tickers` |
| `/v1/analysis-runs` | POST | Portfolio-level analysis with holdings and weights |
| `/v1/analysis-runs/{run_id}` | GET | Poll run status and results |
| `/v1/analysis-runs/{run_id}/events` | GET | Cursor-based event stream for progress updates |
| `/v1/query` | POST | Natural language Q&A over analysis results |
| `/v1/historical-prices/{ticker}` | GET | Historical price data via yfinance |

See [DEPLOYMENT.md](DEPLOYMENT.md) for request/response shapes, curl examples, and environment variable configuration.

---

## Persistent Learning (Roadmap)

> **Note:** The features described below are planned but not yet implemented.

AlphaWalker's graph is persistent across runs. Each run timestamps its findings as new nodes (see Temporal Graph above). Future planned enhancements include:

- Tracking subsequent price performance as ground truth
- Scoring each coalition on prediction accuracy over a rolling window
- Weighting judge verdicts by historical coalition accuracy per ticker

---

## Jac / OSP Architecture

AlphaWalker maps cleanly onto Jac's Object Spatial Programming model:

| Concept | Jac Implementation |
|---|---|
| Asset node | `Asset` node with ticker, price data, and attached coalition findings |
| Bull/Bear positioning | `BullNode` and `BearNode` on opposite edges of each `Asset` node |
| Coalition research | Walkers (`BullCoalitionWalker`, `BearCoalitionWalker`) traversing simultaneously |
| LLM-powered argumentation | `by llm()` with directed argumentative system prompts |
| Judge synthesis | `JudgeWalker` as a final traversal that reads both sides before disengaging |
| Temporal graph | Each walker pass appends a timestamped node rather than overwriting; history is preserved in the graph |
| Signal momentum detection | `JudgeWalker` traverses timestamped nodes across runs to detect directional acceleration |
| Portfolio meta-reasoning | `PortfolioMetaAgent` walker traverses all asset nodes to surface correlation and concentration risk |
| Confidence scoring | Each agent deposits a confidence score alongside its argument; judge weights verdicts accordingly |
| Epistemic humility | Judge emits `INSUFFICIENT DATA` verdict when both sides return low confidence |
| Live Q&A | `QueryWalker` traverses relevant nodes in real time to answer freeform natural language questions |
| Historical learning | **Planned** — persistent edge weights updated after each weekly run (not yet implemented) |

The declarative nature of Jac means agent roles and graph topology are defined structurally — orchestration is handled by the runtime, not imperative control flow.

---

## The Pitch

> "Two AI agent teams debate every stock in your portfolio — one tries to convince you to buy, one tries to convince you to sell, and a judge agent makes the final call."
