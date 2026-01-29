"""Factor benchmark data tools.

This module provides tools for accessing factor benchmarks at different granularity levels:
- Industry-level factor benchmarks
- Sub-industry-level factor benchmarks

Supported factors: growth, value, momentum, quality, volatility
"""

from .industry import (
    get_industry_factor_benchmark,
    GET_INDUSTRY_FACTOR_BENCHMARK_TOOL,
)

from .sub_industry import (
    get_sub_industry_factor_benchmark,
    GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL,
)

__all__ = [
    # Industry-level factor benchmarks
    "get_industry_factor_benchmark",
    "GET_INDUSTRY_FACTOR_BENCHMARK_TOOL",
    # Sub-industry-level factor benchmarks
    "get_sub_industry_factor_benchmark",
    "GET_SUB_INDUSTRY_FACTOR_BENCHMARK_TOOL",
]
