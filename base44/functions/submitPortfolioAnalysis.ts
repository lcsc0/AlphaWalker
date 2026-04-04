type HoldingInput = {
  ticker: string;
  weight: number;
};

type SubmitPayload = {
  portfolioName?: string;
  holdings: HoldingInput[];
  sourceType?: "manual" | "csv";
  rawCsvFileUrl?: string | null;
  sessionId?: string | null;
};

function normalizeHoldings(holdings: HoldingInput[]): HoldingInput[] {
  const merged = new Map<string, number>();

  for (const holding of holdings) {
    const ticker = holding.ticker.trim().toUpperCase();
    if (!ticker) continue;
    if (holding.weight < 0) {
      throw new Error(`Negative weight is not allowed for ${ticker}`);
    }
    merged.set(ticker, (merged.get(ticker) ?? 0) + Number(holding.weight));
  }

  const values = [...merged.entries()].map(([ticker, weight]) => ({ ticker, weight }));
  if (values.length === 0) {
    throw new Error("Portfolio must contain at least one holding");
  }

  const total = values.reduce((sum, item) => sum + item.weight, 0);
  if (total <= 0) {
    throw new Error("Portfolio weights must sum to more than zero");
  }

  return values.map((item) => ({
    ticker: item.ticker,
    weight: Number((item.weight / total).toFixed(6)),
  }));
}

export default async function submitPortfolioAnalysis(payload: SubmitPayload) {
  const holdings = normalizeHoldings(payload.holdings);
  const apiBaseUrl = process.env.ALPHAWALKER_API_BASE_URL;
  const apiKey = process.env.ALPHAWALKER_API_KEY;

  if (!apiBaseUrl || !apiKey) {
    throw new Error("Missing AlphaWalker API configuration");
  }

  const response = await fetch(`${apiBaseUrl}/v1/analysis-runs`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify({
      portfolio: {
        holdings,
        as_of_date: new Date().toISOString().slice(0, 10),
      },
      options: {
        include_sentiment: true,
        include_rebalancing: true,
        include_graph: true,
      },
      client_context: {
        source: "base44",
        session_id: payload.sessionId ?? null,
      },
    }),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`AlphaWalker submit failed: ${errorText}`);
  }

  const run = await response.json();

  const analysisRun = await base44.entities.AnalysisRun.create({
    run_id: run.run_id,
    status: run.status,
    user_id: base44.auth.user?.id ?? null,
    portfolio_name: payload.portfolioName ?? "Untitled portfolio",
    holdings_count: holdings.length,
    submitted_input: { holdings },
    result: null,
    error: null,
  });

  await base44.entities.PortfolioSnapshot.create({
    analysis_run_id: analysisRun.id,
    holdings,
    source_type: payload.sourceType ?? "manual",
    raw_csv_file_url: payload.rawCsvFileUrl ?? null,
  });

  return {
    analysisRunId: analysisRun.id,
    runId: run.run_id,
    status: run.status,
    createdAt: run.created_at,
  };
}
