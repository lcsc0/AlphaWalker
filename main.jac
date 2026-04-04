# main.jac
# Entry point for AlphaWalker.
# Accepts a list of tickers, seeds an Asset node per ticker, attaches Bull and Bear
# coalition nodes, and spawns BullWalker and BearWalker concurrently. After both
# complete, spawns JudgeWalker per asset, then PortfolioMetaAgent across all assets.
