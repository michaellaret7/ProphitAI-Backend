"""Portfolio utilities (correlation, builder submodule)."""

from .correlation import CorrelationAnalysis

# Re-export build submodule for ergonomic imports: portfolio.build
from . import build  # noqa: F401

__all__ = ["CorrelationAnalysis", "build"]

