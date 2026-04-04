"""Analysis engines for AlphaWalker."""

from __future__ import annotations

from dataclasses import dataclass

from .models import (
    AnalysisRequest,
    AnalysisResult,
    GraphData,
    GraphEdge,
    GraphNode,
    HoldingAnalysis,
    Recommendation,
)


@dataclass(slots=True)
class EngineEvent:
    agent: str
    stage: str
    message: str
    progress: float | None = None


class RuleBasedAnalysisEngine:
    """Deterministic fallback engine used until a deployable Jac runtime is available."""

    POSITIVE_TICKERS = {"NVDA", "MSFT", "AAPL", "AMZN", "META", "GOOGL"}
    NEGATIVE_TICKERS = {"TSLA", "SMCI", "COIN", "MSTR", "PLTR"}

    def analyze(
        self,
        request: AnalysisRequest,
        emit: callable,
    ) -> AnalysisResult:
        holdings = request.portfolio.holdings

        emit(
            EngineEvent(
                agent="portfolio_ingestor",
                stage="started",
                message=f"Normalized {len(holdings)} holdings for analysis",
                progress=0.1,
            )
        )

        emit(
            EngineEvent(
                agent="researcher",
                stage="running",
                message="Scanning the portfolio for concentration and crowding risk",
                progress=0.25,
            )
        )

        holding_results: list[HoldingAnalysis] = []
        recommendations: list[Recommendation] = []
        graph_nodes: list[GraphNode] = []
        graph_edges: list[GraphEdge] = []

        weighted_risk_total = 0.0
        sentiment_scores: list[int] = []

        for index, holding in enumerate(holdings, start=1):
            ticker = holding.ticker.upper()
            concentration_penalty = min(int(holding.weight * 100), 35)
            base_risk = 35 + concentration_penalty + ((sum(ord(ch) for ch in ticker) % 17) * 2)

            sentiment = "neutral"
            sentiment_score = 0
            if ticker in self.POSITIVE_TICKERS:
                base_risk -= 8
                sentiment = "positive"
                sentiment_score = 1
            elif ticker in self.NEGATIVE_TICKERS:
                base_risk += 10
                sentiment = "negative"
                sentiment_score = -1

            risk_score = max(5, min(base_risk, 95))
            weighted_risk_total += risk_score * holding.weight
            sentiment_scores.append(sentiment_score)

            summary = self._build_summary(
                ticker=ticker,
                weight=holding.weight,
                risk_score=risk_score,
                sentiment=sentiment,
            )
            holding_results.append(
                HoldingAnalysis(
                    ticker=ticker,
                    weight=round(holding.weight, 4),
                    risk_score=risk_score,
                    sentiment=sentiment,
                    summary=summary,
                )
            )

            if holding.weight >= 0.2 or risk_score >= 70:
                target_weight = round(max(holding.weight * 0.7, 0.05), 4)
                recommendations.append(
                    Recommendation(
                        ticker=ticker,
                        action="reduce",
                        reason="position concentration and volatility",
                        target_weight=target_weight,
                    )
                )

            if request.options.include_graph:
                asset_id = f"asset:{ticker}"
                graph_nodes.extend(
                    [
                        GraphNode(id=asset_id, label=ticker, kind="asset"),
                        GraphNode(id=f"bull:{ticker}", label=f"{ticker} Bull", kind="bull"),
                        GraphNode(id=f"bear:{ticker}", label=f"{ticker} Bear", kind="bear"),
                        GraphNode(id=f"judge:{ticker}", label=f"{ticker} Judge", kind="judge"),
                    ]
                )
                graph_edges.extend(
                    [
                        GraphEdge(source=asset_id, target=f"bull:{ticker}", label="analyzed_by"),
                        GraphEdge(source=asset_id, target=f"bear:{ticker}", label="analyzed_by"),
                        GraphEdge(source=f"bull:{ticker}", target=f"judge:{ticker}", label="debated"),
                        GraphEdge(source=f"bear:{ticker}", target=f"judge:{ticker}", label="debated"),
                    ]
                )

            emit(
                EngineEvent(
                    agent="risk_analyzer",
                    stage="running",
                    message=f"Evaluated {ticker} with risk score {risk_score}",
                    progress=min(0.25 + (0.4 * index / max(len(holdings), 1)), 0.65),
                )
            )

        emit(
            EngineEvent(
                agent="sentiment_agent",
                stage="running",
                message="Synthesizing cross-holding sentiment and allocation pressure",
                progress=0.8,
            )
        )

        overall_risk_score = int(round(weighted_risk_total))
        risk_band = self._risk_band(overall_risk_score)
        sentiment_summary = self._sentiment_summary(sentiment_scores)

        if request.options.include_rebalancing and not recommendations:
            lowest = min(holding_results, key=lambda item: item.risk_score)
            recommendations.append(
                Recommendation(
                    ticker=lowest.ticker,
                    action="maintain",
                    reason="portfolio looks balanced relative to current signals",
                    target_weight=round(lowest.weight, 4),
                )
            )

        emit(
            EngineEvent(
                agent="judge_agent",
                stage="completed",
                message="Finished portfolio verdict and rebalancing recommendations",
                progress=1.0,
            )
        )

        graph = GraphData()
        if request.options.include_graph:
            graph = GraphData(nodes=graph_nodes, edges=graph_edges)

        return AnalysisResult(
            overall_risk_score=overall_risk_score,
            risk_band=risk_band,
            sentiment_summary=sentiment_summary,
            rebalancing_suggestions=recommendations if request.options.include_rebalancing else [],
            holdings=holding_results,
            graph=graph,
        )

    def _build_summary(self, *, ticker: str, weight: float, risk_score: int, sentiment: str) -> str:
        if sentiment == "positive":
            tone = "favorable momentum with manageable downside"
        elif sentiment == "negative":
            tone = "elevated downside sensitivity and headline risk"
        else:
            tone = "mixed signals with no decisive catalyst"
        return (
            f"{ticker} is {round(weight * 100, 1)}% of the portfolio with a "
            f"{risk_score}/100 risk score, suggesting {tone}."
        )

    def _risk_band(self, score: int) -> str:
        if score >= 70:
            return "high"
        if score >= 45:
            return "moderate"
        return "low"

    def _sentiment_summary(self, scores: list[int]) -> str:
        score = sum(scores)
        if score > 0:
            return "Positive skew across core holdings"
        if score < 0:
            return "Mixed to negative across the portfolio"
        return "Mixed"
