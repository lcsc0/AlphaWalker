# AlphaWalker — Features

---

## Temporal Graph — Signal Evolution Over Time

The graph is not a snapshot — it has a time dimension. Every walker pass timestamps its findings as a **new node** rather than overwriting the previous one. This means the graph accumulates a full history of how sentiment and signals evolved for each asset across runs.

This unlocks a qualitatively different class of reasoning. The `JudgeAgent` can detect **momentum shifts** across time, not just evaluate the current state:

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

Each `TemporalSnapshot` node captures: run number, timestamp, side (bull/bear), argument text, confidence score, and sub-agent breakdowns.

---

## Quantitative Technical Signals (yfinance)

Before quant agents run, AlphaWalker computes real technical signals from market data via `api/technical_signals.py` using `yfinance` (1-year of daily price history per ticker):

- **RSI (14-day)** with overbought (>70) / oversold (<30) labels
- **50-day and 200-day moving averages** with crossover detection (golden cross, death cross, bullish/bearish alignment)
- **Realized volatility** (30-day annualized)
- **Price momentum** (1-month, 3-month, 6-month returns)

These signals are injected into the `quant_signals` field on each `Asset` node and passed to both `BullQuantAgent` and `BearQuantAgent` as factual foundation data. This ensures quant agents argue from computed numbers rather than relying on LLM training data for market prices.

The rebalance agent also uses yfinance signals when evaluating candidate securities — it prefers RSI 40–60 for entry timing and checks moving average alignment before recommending a position.

---

## Portfolio Rebalancing

The `POST /v1/rebalance` endpoint runs a two-phase pipeline that suggests new securities to address gaps in the current portfolio.

**Phase 1 — Gap identification and candidate generation:** The agent reads the `PortfolioAnnotation` (correlated themes, hedging gaps, portfolio conviction) and generates 8–10 candidate securities (stocks or ETFs) that address the identified weaknesses.

**Phase 2 — Signal fetch and ranking:** Real yfinance signals are fetched for each candidate. The agent ranks the top 3 picks with rationales, entry timing recommendations, fit scores, and the underlying technical signals.

Request body:
```json
{
  "portfolio_annotation": {
    "annotation": "...",
    "correlated_theme": "AI infrastructure capex",
    "hedging_gaps": "No defensive or rate-sensitive exposure",
    "portfolio_conviction": "high"
  }
}
```

Response includes a `gap_summary` and `top_picks` array with ticker, rationale, fit score, entry timing, and signals for each recommendation.

---

## Portfolio Meta Agent

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

The meta agent's output (`annotation`, `correlated_theme`, `hedging_gaps`, `portfolio_conviction`) is returned as the `portfolio_meta` field in the `/v1/analyze-tickers` response and feeds directly into the rebalance pipeline.

---

## Agent Confidence and Dissent Scoring

When bull and bear agents deposit their findings, they also output a **confidence score** alongside their argument. This score reflects how much supporting evidence they were able to find — a news agent with three corroborating sources scores higher than one working from a single ambiguous headline.

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

## Natural Language Portfolio Q&A

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

Endpoint: `POST /v1/query` with `{ "question": "..." }`.

---

## Insforge Integration

AlphaWalker uses [Insforge](https://insforge.app) as its cloud database backend for persisting analysis history across sessions and deployments.

**What gets stored:**
- Each analysis run is inserted into the `analysis_runs` table with timestamp, ticker list, and run metadata
- Each ticker verdict is inserted into the `ticker_verdicts` table with the full bull argument, bear argument, judge ruling, confidence scores, and temporal snapshot data

**How it connects:**
The `InsforgeClient` in `api/insforge_client.py` communicates with the Insforge REST API using two environment variables:

```bash
export INSFORGE_URL=https://your-project.insforge.app
export INSFORGE_SERVICE_KEY=your-service-key
```

**Graceful fallback:**
If `INSFORGE_URL` or `INSFORGE_SERVICE_KEY` are not set, AlphaWalker runs in local-only mode. Analysis results are still persisted to the local SQLite database (`data/analysis_runs.db`) and all features work normally. Insforge is required only for the **History tab** in the React frontend, which pulls past runs from the cloud database.

**History tab:**
The History tab in the React dashboard calls the Insforge `ticker_verdicts` table directly to display a searchable log of past analyses across sessions. Without Insforge configured, the History tab will be empty.

**Setting up Insforge:**
See [DEPLOYMENT.md](DEPLOYMENT.md) for the full Insforge setup walkthrough, including table schema and service key configuration.

---

## 12-Hour Verdict Cache

Repeated analysis of the same ticker within 12 hours returns cached results without re-running the agent pipeline. The cache is in-memory (per-process) and implemented in `api/verdict_cache.py`. This avoids redundant LLM calls during iterative portfolio exploration.
