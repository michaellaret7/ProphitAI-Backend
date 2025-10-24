"""
Memory systems for Base Agent V2

This module provides persistent and episodic memory for agents:

- domain_memory.py: Agent-specific knowledge and patterns
  - CIO portfolio construction patterns
  - Industry-specific insights
  - Best practices and heuristics

- episodic_memory.py: Recent successful tool executions
  - Learning from recent experiences
  - Pattern recognition from successful runs

- memory_store/: JSON-based storage for memories
  - domain_memory/: Industry-specific knowledge bases
  - episodic_memory.json: Recent execution history

Migrated from base_agent V1 with no changes (these work well).
"""

from .domain_memory import DomainMemory
from .episodic_memory import EpisodicMemory

__all__ = ["DomainMemory", "EpisodicMemory"]