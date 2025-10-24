"""
Reasoning system for Base Agent V2

This module handles the Think → Act → Observe → Reason cycle:

- prompts.py: Build reasoning prompts for agent
  - Thinking prompts (before action) - THINK
  - Observation prompts (after tool calls) - OBSERVE
  - Reasoning prompts (synthesis and decision-making) - REASON
  - Task context prompts (show current position)
  - Advancement reminders (agent control)
  - Comprehensive iteration prompts (phase-aware)

Tool outputs are already formatted as YAML by the tools themselves.
ReasoningPrompter just builds prompts - agent does all analytical work.

Following KISS and YAGNI principles:
- One class for all prompting needs
- No redundant formatting layers
- Trust agent's analytical capability
"""

from .prompts import ReasoningPrompter

__all__ = ["ReasoningPrompter"]
