# agents/portfolio_meta_agent.jac
# Walker: Portfolio Meta Agent
# Operates one level above individual asset agents. Traverses all Asset nodes
# simultaneously via the PortfolioNode. Reasons about:
#   - Sector and factor concentration risk
#   - Correlated bull signals (single macro bet expressed across multiple holdings)
#   - Hedging gaps between positions
#   - Portfolio-level conviction given per-ticker judge rulings
# Appends a portfolio-level annotation to the output memo — does not modify
# individual asset verdicts.
