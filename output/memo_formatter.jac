# output/memo_formatter.jac
# Formats structured verdict data from JudgeAgent and PortfolioMetaAgent into the
# investment committee memo output format:
#   - Ticker header
#   - Bull case with per-agent annotations and coalition confidence score
#   - Bear case with per-agent annotations and coalition confidence score
#   - Signal trend across last N temporal snapshots
#   - Judge's ruling: verdict, confidence, rationale, conditions
#   - Portfolio-level annotation (from PortfolioMetaAgent)
