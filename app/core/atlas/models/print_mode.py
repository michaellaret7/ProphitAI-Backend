"""Print mode configuration for agent output verbosity.

- production: Minimal output (only tool calls)
- verbose: Standard output (iteration status, tool calls, results)
- debug: Maximum output (full LLM responses + all verbose output)
"""

from enum import Enum


class PrintMode(str, Enum):
    """Agent print mode for controlling output verbosity."""

    PRODUCTION = "production"
    VERBOSE = "verbose"
    DEBUG = "debug"
    SUBAGENT = "subagent"
