"""Bull Quant Agent — reads price action, technicals, and fundamentals for bullish signals."""

import from graph.nodes { BullNode }
import from prompts.bull_prompts { analyze_bull_quant }

walker BullQuantAgent {
    has ticker: str;

    can analyze with BullNode entry {
        result = analyze_bull_quant(ticker=self.ticker);
        here.quant_finding = result.findings;
        here.quant_confidence = result.confidence;
        report result;
        disengage;
    }
}
