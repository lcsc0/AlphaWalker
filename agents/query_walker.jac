"""Query Walker — natural language Q&A over the live graph."""

import from ..graph.nodes {
    PortfolioNode, Asset, BullNode, BearNode,
    TemporalSnapshot, VerdictNode, PortfolioAnnotation
}
import from ..graph.edges {
    BelongsToPortfolio, HasCoalition, HasSnapshot,
    HasVerdict, HasAnnotation
}
import from ..prompts.query_prompts { QueryAnswer, answer_query }

def confidence_label(score: int) -> str {
    if score >= 70 {
        return "strong";
    } elif score >= 45 {
        return "moderate";
    }
    return "weak";
}

def build_momentum_string(snapshots: list[TemporalSnapshot], depth: int) -> str {
    if len(snapshots) == 0 {
        return "no prior data";
    }
    sorted_snaps = sorted(snapshots, key=lambda s: TemporalSnapshot: s.run_number);
    # Limit to most recent N snapshots
    if len(sorted_snaps) > depth {
        sorted_snaps = sorted_snaps[-depth:];
    }
    labels = [confidence_label(s.confidence) for s in sorted_snaps];
    return " -> ".join(labels);
}

def build_asset_context_block(
    ticker: str,
    sector: str,
    price: float,
    bull: BullNode | None,
    bear: BearNode | None,
    verdict: VerdictNode | None,
    bull_momentum: str,
    bear_momentum: str
) -> str {
    lines: list = [];
    lines.append(f"ASSET: {ticker} | sector={sector} | price={price}");

    if bull is not None {
        lines.append(f"BULL: {bull.argument} | confidence={bull.confidence}%");
        lines.append(f"  News: {bull.news_finding} ({bull.news_confidence}%) | Quant: {bull.quant_finding} ({bull.quant_confidence}%) | Macro: {bull.macro_finding} ({bull.macro_confidence}%)");
        lines.append(f"  Momentum: {bull_momentum}");
    } else {
        lines.append("BULL: no data");
    }

    if bear is not None {
        lines.append(f"BEAR: {bear.argument} | confidence={bear.confidence}%");
        lines.append(f"  News: {bear.news_finding} ({bear.news_confidence}%) | Quant: {bear.quant_finding} ({bear.quant_confidence}%) | Macro: {bear.macro_finding} ({bear.macro_confidence}%)");
        lines.append(f"  Momentum: {bear_momentum}");
    } else {
        lines.append("BEAR: no data");
    }

    if verdict is not None {
        lines.append(f"VERDICT: {verdict.verdict} | confidence={verdict.judge_confidence}%");
        lines.append(f"  Rationale: {verdict.rationale}");
        if verdict.condition {
            lines.append(f"  Condition: {verdict.condition}");
        }
    } else {
        lines.append("VERDICT: no verdict");
    }

    return "\n".join(lines);
}

walker QueryWalker {
    has question: str;
    has asset_contexts: list = [];
    has portfolio_context: str = "";
    has snapshot_depth: int = 4;

    can enter_portfolio with PortfolioNode entry {
        # Read portfolio-level annotations if available
        annotations = [->:HasAnnotation:->][?:PortfolioAnnotation];
        if len(annotations) > 0 {
            # Take the most recent annotation by run_number
            sorted_annots = sorted(annotations, key=lambda a: PortfolioAnnotation: a.run_number);
            latest = sorted_annots[-1];
            self.portfolio_context = (
                f"PORTFOLIO ANNOTATION:\n"
                f"  Summary: {latest.annotation}\n"
                f"  Correlated Theme: {latest.correlated_theme}\n"
                f"  Hedging Gaps: {latest.hedging_gaps}\n"
                f"  Portfolio Conviction: {latest.portfolio_conviction}"
            );
        }

        visit [->:BelongsToPortfolio:->][?:Asset];
    }

    can enter_asset with Asset entry {
        bull_nodes = [->:HasCoalition:side=="bull":->][?:BullNode];
        bear_nodes = [->:HasCoalition:side=="bear":->][?:BearNode];
        verdict_nodes = [->:HasVerdict:->][?:VerdictNode];

        bull: BullNode | None = None;
        bear: BearNode | None = None;
        verdict: VerdictNode | None = None;
        bull_momentum = "no prior data";
        bear_momentum = "no prior data";

        if len(bull_nodes) > 0 {
            bull = bull_nodes[0];
            bull_snapshots = [bull ->:HasSnapshot:->][?:TemporalSnapshot];
            bull_momentum = build_momentum_string(bull_snapshots, self.snapshot_depth);
        }
        if len(bear_nodes) > 0 {
            bear = bear_nodes[0];
            bear_snapshots = [bear ->:HasSnapshot:->][?:TemporalSnapshot];
            bear_momentum = build_momentum_string(bear_snapshots, self.snapshot_depth);
        }
        if len(verdict_nodes) > 0 {
            verdict = verdict_nodes[0];
        }

        block = build_asset_context_block(
            ticker=here.ticker,
            sector=here.sector,
            price=here.price,
            bull=bull,
            bear=bear,
            verdict=verdict,
            bull_momentum=bull_momentum,
            bear_momentum=bear_momentum
        );
        self.asset_contexts.append(block);
    }

    can exit_portfolio with PortfolioNode exit {
        if len(self.asset_contexts) == 0 and self.portfolio_context == "" {
            report QueryAnswer(
                answer="No data available in the portfolio to answer this question.",
                cited_tickers=[],
                confidence_note="Portfolio graph is empty — no assets or annotations found."
            );
            disengage;
        }

        # Assemble full graph context
        sections: list = [];
        if self.portfolio_context != "" {
            sections.append(self.portfolio_context);
        }
        for ctx in self.asset_contexts {
            sections.append(ctx);
        }
        full_context = "\n\n".join(sections);

        result = answer_query(
            question=self.question,
            graph_context=full_context
        );

        report result;
    }
}
