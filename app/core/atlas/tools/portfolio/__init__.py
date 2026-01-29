"""Portfolio analysis tools for agents."""

from .beta import (
    calculate_portfolio_beta_vs_index,
    CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
)
from .build_allocations import (
    build_allocations,
    BUILD_PORTFOLIO_TOOL,
)
from .concentration import (
    exposure_calculator,
    industry_concentration,
    VaR_calculator,
    EXPOSURE_CALCULATOR_TOOL,
    INDUSTRY_CONCENTRATION_TOOL,
    VAR_CALCULATOR_TOOL,
)
from .corr_matrix import (
    correlation_matrix,
    CORRELATION_MATRIX_TOOL,
)
from .factor_tilts import (
    factor_tilts_for_portfolio,
    FACTOR_TILTS_FOR_PORTFOLIO_TOOL,
)
from .group_performance import (
    calculate_group_performances,
    CALCULATE_GROUP_PERFORMANCES_TOOL,
)
from .performance import (
    calculate_portfolio_performance,
    CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
)
from .returns import (
    calculate_portfolio_returns_metrics,
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
)
from .ticker_performance import (
    calculate_ticker_performances,
    CALCULATE_TICKER_PERFORMANCES_TOOL,
)
from .get_user_portfolio import (
    get_user_portfolio,
    GET_USER_PORTFOLIO_TOOL,
)

__all__ = [
    # Functions
    "calculate_portfolio_beta_vs_index",
    "build_allocations",
    "exposure_calculator",
    "industry_concentration",
    "VaR_calculator",
    "correlation_matrix",
    "factor_tilts_for_portfolio",
    "calculate_group_performances",
    "calculate_portfolio_performance",
    "calculate_portfolio_returns_metrics",
    "calculate_ticker_performances",
    "get_user_portfolio",
    # Tool definitions
    "CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL",
    "BUILD_PORTFOLIO_TOOL",
    "EXPOSURE_CALCULATOR_TOOL",
    "INDUSTRY_CONCENTRATION_TOOL",
    "VAR_CALCULATOR_TOOL",
    "CORRELATION_MATRIX_TOOL",
    "FACTOR_TILTS_FOR_PORTFOLIO_TOOL",
    "CALCULATE_GROUP_PERFORMANCES_TOOL",
    "CALCULATE_PORTFOLIO_PERFORMANCE_TOOL",
    "CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL",
    "CALCULATE_TICKER_PERFORMANCES_TOOL",
    "GET_USER_PORTFOLIO_TOOL",
]
