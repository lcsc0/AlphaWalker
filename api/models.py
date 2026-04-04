"""Core data models for the AlphaWalker analysis service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_now_iso() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class Holding:
    ticker: str
    weight: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PortfolioInput:
    holdings: list[Holding]
    as_of_date: str = field(default_factory=lambda: date.today().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "holdings": [holding.to_dict() for holding in self.holdings],
            "as_of_date": self.as_of_date,
        }


@dataclass(slots=True)
class AnalysisOptions:
    include_sentiment: bool = True
    include_rebalancing: bool = True
    include_graph: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ClientContext:
    source: str = "base44"
    session_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AnalysisRequest:
    portfolio: PortfolioInput
    options: AnalysisOptions = field(default_factory=AnalysisOptions)
    client_context: ClientContext = field(default_factory=ClientContext)

    def to_dict(self) -> dict[str, Any]:
        return {
            "portfolio": self.portfolio.to_dict(),
            "options": self.options.to_dict(),
            "client_context": self.client_context.to_dict(),
        }


@dataclass(slots=True)
class AnalysisError:
    code: str
    message: str
    retryable: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Recommendation:
    ticker: str
    action: str
    reason: str
    target_weight: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class HoldingAnalysis:
    ticker: str
    weight: float
    risk_score: int
    sentiment: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GraphNode:
    id: str
    label: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GraphEdge:
    source: str
    target: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GraphData:
    nodes: list[GraphNode] = field(default_factory=list)
    edges: list[GraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }


@dataclass(slots=True)
class AnalysisResult:
    overall_risk_score: int
    risk_band: str
    sentiment_summary: str
    rebalancing_suggestions: list[Recommendation]
    holdings: list[HoldingAnalysis]
    graph: GraphData = field(default_factory=GraphData)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_risk_score": self.overall_risk_score,
            "risk_band": self.risk_band,
            "sentiment_summary": self.sentiment_summary,
            "rebalancing_suggestions": [
                suggestion.to_dict() for suggestion in self.rebalancing_suggestions
            ],
            "holdings": [holding.to_dict() for holding in self.holdings],
            "graph": self.graph.to_dict(),
        }


@dataclass(slots=True)
class AnalysisEvent:
    seq: int
    timestamp: str
    agent: str
    stage: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PortfolioSummary:
    holdings_count: int
    total_weight: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RunRecord:
    run_id: str
    status: str
    progress: float
    portfolio_summary: PortfolioSummary
    request_payload: dict[str, Any]
    normalized_holdings: list[dict[str, Any]]
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "progress": self.progress,
            "portfolio_summary": self.portfolio_summary.to_dict(),
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "result": self.result,
            "error": self.error,
            "request_payload": self.request_payload,
            "normalized_holdings": self.normalized_holdings,
        }
