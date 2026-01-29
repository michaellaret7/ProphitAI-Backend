"""Risk analysis tools for agents."""

from .asset_risk_contrib import (
    risk_contribution,
    RISK_CONTRIBUTION_TOOL,
)
from .cov_matrix import (
    calculate_covariance_matrix,
    CALCULATE_COVARIANCE_MATRIX_TOOL,
)
from .drawdown_profile import (
    drawdown_profile,
    DRAWDOWN_PROFILE_TOOL,
)
from .pairwise_corr_analysis import (
    run_pairwise_correlation_analysis,
    PAIRWISE_CORR_ANALYSIS_TOOL,
)
from .stress_test import (
    stress_test,
    STRESS_TEST_TOOL,
)
from .vol_es import (
    vol_es,
    VOL_ES_TOOL,
)

__all__ = [
    # Functions
    "risk_contribution",
    "calculate_covariance_matrix",
    "drawdown_profile",
    "run_pairwise_correlation_analysis",
    "stress_test",
    "vol_es",
    # Tool definitions
    "RISK_CONTRIBUTION_TOOL",
    "CALCULATE_COVARIANCE_MATRIX_TOOL",
    "DRAWDOWN_PROFILE_TOOL",
    "PAIRWISE_CORR_ANALYSIS_TOOL",
    "STRESS_TEST_TOOL",
    "VOL_ES_TOOL",
]
