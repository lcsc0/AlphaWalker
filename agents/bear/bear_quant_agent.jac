"""Bear Quant Agent — flags valuation excess and bearish technicals."""

import from ...graph.nodes { BearNode }
import from ...prompts.bear_prompts { analyze_bear_quant }

walker BearQuantAgent {
    has ticker: str;

    can analyze with BearNode entry {
        result = analyze_bear_quant(ticker=self.ticker);
        here.quant_finding = result.findings;
        here.quant_confidence = result.confidence;
        report result;
        disengage;
    }
}
