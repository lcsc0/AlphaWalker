# graph/edges.jac
# All edge definitions for the AlphaWalker graph.
#
# Edges:
#   HasCoalition        - Asset -> BullNode / BearNode
#   HasSnapshot         - BullNode/BearNode -> TemporalSnapshot (append-only per run)
#   BelongsToPortfolio  - Asset -> PortfolioNode
