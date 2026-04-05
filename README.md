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
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm install && cd ..

# 4. Configure environment variables
cp .env.example .env   # then edit .env with your keys
```

At minimum, set `OPENAI_API_KEY` in `.env`. See `.env.example` for all available options.

```bash
# 5. Start everything
./start.sh
```

- Backend → `http://localhost:8000`
- Frontend → `http://localhost:3000`

> `start.sh` activates the virtual environment and loads `.env` automatically.

**Manual start (two terminals):**

```bash
# Terminal 1 — backend (with venv active)
source .venv/bin/activate
uvicorn api.main:app --host 0.0.0.0 --port 8000

# Terminal 2 — frontend
cd frontend && npm run dev -- --port 3000
```

**CLI only (no frontend needed):**

```bash
source .venv/bin/activate
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

## Features

AlphaWalker includes several capabilities beyond the core debate loop. See [features.md](features.md) for full documentation on:

- **Temporal graph** — signal momentum tracking across runs
- **Quantitative technical signals** — real market data via yfinance (RSI, moving averages, volatility, momentum)
- **Portfolio rebalancing** — LLM-generated candidate securities ranked by yfinance signals
- **Portfolio meta agent** — cross-asset concentration, correlation, and hedging gap analysis
- **Agent confidence and dissent scoring** — evidence-weighted verdicts and `INSUFFICIENT DATA` rulings
- **Natural language Q&A** — freeform questions answered by traversing the live graph
- **Insforge integration** — cloud database persistence for multi-session history
- **12-hour verdict cache** — avoids redundant LLM calls during iterative exploration

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
| `/v1/rebalance` | POST | Portfolio rebalancing recommendations |
| `/v1/historical-prices/{ticker}` | GET | Historical price data via yfinance |

See [DEPLOYMENT.md](DEPLOYMENT.md) for request/response shapes, curl examples, and environment variable configuration.

---

## Persistent Learning (Roadmap)

> **Note:** The features described below are planned but not yet implemented.

AlphaWalker's graph is persistent across runs. Each run timestamps its findings as new nodes (see [features.md — Temporal Graph](features.md)). Future planned enhancements include:

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
