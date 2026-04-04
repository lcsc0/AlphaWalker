# agents/judge_agent.jac
# Walker: Judge Agent
# Neutral synthesis walker. Does not conduct its own research.
# Reads BullNode and BearNode structured arguments, traverses TemporalSnapshot
# history to detect momentum shifts, weights arguments by coalition confidence scores,
# and produces a structured verdict.
# Flags INSUFFICIENT DATA when both sides fall below confidence threshold.
#
# Possible verdicts:
#   conviction buy | buy with conditions | hold |
#   avoid with conditions | conviction avoid | split decision | insufficient data
