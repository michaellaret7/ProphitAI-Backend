"""Covariance matrix calculations and portfolio risk decomposition."""

import numpy as np
import pandas as pd

from app.core.calculations.config import TRADING_DAYS
from app.core.calculations.models.covariance import (
    AssetRiskContribution,
    CovarianceMetrics,
)


# =============================================================================
# Ticker-Group Level (no weights needed)
# =============================================================================

def calc_covariance_matrix(
    asset_returns: pd.DataFrame,
    annualize: bool = False,
) -> pd.DataFrame:
    """Calculate the sample covariance matrix from asset daily returns.

    Args:
        asset_returns: DataFrame of daily returns with ticker columns.
        annualize: If True, scale by 252 trading days.
    """
    cov = asset_returns.cov()
    return cov * TRADING_DAYS if annualize else cov


# =============================================================================
# Portfolio Level (requires weights)
# =============================================================================

def calc_portfolio_variance(
    weights: np.ndarray,
    cov_matrix: pd.DataFrame,
) -> float:
    """Calculate portfolio variance: w' * Σ * w."""
    w = np.asarray(weights)
    return float(w @ cov_matrix.values @ w)


# This func is used to calc individual asset risk contributions to the portfolio
def calc_risk_contributions(
    tickers: list[str],
    weights: np.ndarray,
    cov_matrix: pd.DataFrame,
) -> list[AssetRiskContribution]:
    """Calculate marginal, component, and percentage risk contributions per asset.

    - Marginal Contribution to Risk (MCR_i): (Σ * w)_i / σ_p
      Sensitivity of portfolio volatility to a change in weight_i.
    - Component Contribution (CCR_i): w_i * MCR_i
      Absolute risk contribution of asset i.
    - Percentage Contribution (%CR_i): CCR_i / σ_p
      Share of total portfolio volatility attributable to asset i.
    """
    w = np.asarray(weights)
    sigma = cov_matrix.values

    port_var = float(w @ sigma @ w)
    port_vol = np.sqrt(port_var) if port_var > 0 else 0.0

    if port_vol == 0:
        return [
            AssetRiskContribution(
                ticker=t, weight=float(w[i]),
                marginal_contribution=0.0,
                component_contribution=0.0,
                pct_contribution=0.0,
            )
            for i, t in enumerate(tickers)
        ]

    # Reason: (Σ * w) gives each asset's covariance with the portfolio.
    # Dividing by σ_p converts from variance units to volatility units.
    sigma_w = sigma @ w
    mcr = sigma_w / port_vol

    contributions = []
    for i, ticker in enumerate(tickers):
        component = float(w[i] * mcr[i])
        contributions.append(AssetRiskContribution(
            ticker=ticker,
            weight=float(w[i]),
            marginal_contribution=float(mcr[i]),
            component_contribution=component,
            pct_contribution=component / port_vol,
        ))

    return contributions


# =============================================================================
# Combined Calculation
# =============================================================================

def calc_all_covariance_metrics(
    asset_returns: pd.DataFrame,
    tickers: list[str],
    weights: np.ndarray,
) -> CovarianceMetrics:
    """Calculate all covariance-derived metrics for a portfolio."""
    cov_daily = calc_covariance_matrix(asset_returns, annualize=False)

    port_var_daily = calc_portfolio_variance(weights, cov_daily)
    contributions = calc_risk_contributions(tickers, weights, cov_daily)

    return CovarianceMetrics(
        portfolio_variance_daily=port_var_daily,
        asset_risk_contributions=contributions,
    )
