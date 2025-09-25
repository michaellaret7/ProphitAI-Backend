"""Portfolio build module (v2).

Holds orchestrator, optimizer, reporter, and visualizer for correlation-aware
portfolio construction.
"""

from .allocator import SimplePortfolioAllocator

__all__ = [
    'SimplePortfolioAllocator',
]


