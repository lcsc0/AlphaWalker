"""Entry point for AlphaWalker."""

import from .graph.nodes { PortfolioNode, Asset, VerdictNode }
import from .graph.edges { BelongsToPortfolio, HasVerdict }
import from .agents.bull_coalition_walker { BullCoalitionWalker }
import from .agents.bear_coalition_walker { BearCoalitionWalker }
import from .agents.judge_agent { JudgeWalker }

with entry {
    portfolio = PortfolioNode(name="AlphaWalker Portfolio");
    root() ++> portfolio;

    tickers = ["NVDA", "AAPL", "TSLA"];

    for ticker in tickers {
        asset = Asset(ticker=ticker);
        portfolio +>:BelongsToPortfolio:+> asset;

        # Run bull and bear coalitions
        asset spawn BullCoalitionWalker(ticker=ticker);
        asset spawn BearCoalitionWalker(ticker=ticker);

        # Judge synthesizes verdict from both sides
        asset spawn JudgeWalker();

        # Read verdict from graph
        verdicts = [asset ->:HasVerdict:->][?:VerdictNode];
        if len(verdicts) > 0 {
            v = verdicts[0];
            print(f"\n{'='*60}");
            print(f"  {ticker}");
            print(f"{'='*60}");
            print(f"  Verdict:    {v.verdict}");
            print(f"  Confidence: {v.judge_confidence}%");
            print(f"  Rationale:  {v.rationale}");
            if v.condition {
                print(f"  Condition:  {v.condition}");
            }
        }
    }

    print(f"\n{'='*60}");
    print("  AlphaWalker run complete.");
    print(f"{'='*60}");
}
