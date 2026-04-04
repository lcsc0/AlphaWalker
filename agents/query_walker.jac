# agents/query_walker.jac
# Walker: Query Walker
# Accepts a freeform natural language question string. Identifies relevant Asset,
# BullNode, BearNode, and TemporalSnapshot nodes. Traverses them in real time
# and generates a plain English explanation using by llm() with graph annotation context.
# This is the live demo interface — queries answered by walking the graph, not a cache.
