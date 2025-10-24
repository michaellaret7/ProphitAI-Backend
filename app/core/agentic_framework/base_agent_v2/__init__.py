"""
Base Agent V2 - Autonomous Reasoning Agent with Analytical Guardrails

This is the next-generation agent architecture that implements:
- Comprehensive analytical structure (prevents gaps in analysis)
- Agent-controlled task progression (no automatic advancement)
- High reasoning density (30-40% of iterations)
- Think → Act → Observe → Reason cycle
- Structured analytical guardrails with execution autonomy

Key Philosophy:
- Tasks as analytical objectives (WHAT to analyze, not HOW)
- Subtasks as systematic checkpoints (ensure comprehensive coverage)
- Agent decides tool usage, approach, and when to advance
- More structure is good when it's analytical structure (not meta-work)

See .claude/AGENT_WORKFLOW_ANALYSIS.md for design philosophy.
See .claude/BASE_AGENT_V2_IMPLEMENTATION_PLAN.md for implementation details.
"""

__version__ = "2.0.0"

from .agent_v2 import BaseAgentV2

__all__ = ["BaseAgentV2"]