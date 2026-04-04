# graph/nodes.jac
# All node definitions for the AlphaWalker graph.
#
# Nodes:
#   Asset            - ticker, price data, coalition attachment point
#   BullNode         - stores bull coalition arguments and confidence score
#   BearNode         - stores bear coalition arguments and confidence score
#   TemporalSnapshot - timestamped copy of coalition state per run (append-only history)
#   PortfolioNode    - root node connecting all assets for PortfolioMetaAgent traversal
