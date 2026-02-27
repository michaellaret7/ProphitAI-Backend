"""Individual calculation functions for combined ETF beta-shock stress testing.

Methodology: Multi-factor OLS regression (Barra's canonical approach).
    portfolio_impact = Σᵢ wᵢ × Σⱼ Bᵢⱼ × Δfⱼ

Each ticker's sensitivity to each ETF is estimated via OLS, shocks are applied,
and results are aggregated by portfolio weight.

Reuses `align_returns` from risk/benchmark.py for date alignment.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.core.calculations.models.stress_test import EtfContribution, TickerStressResult


# ================================
# --> Helper funcs
# ================================

@dataclass
class OlsDiagnostics:
    """Return type for _calc_ols_with_diagnostics."""

    betas: dict[str, float]
    std_errors: dict[str, float]
    residual_std: float
    r_squared: float


def calc_factor_vif(
    etf_returns_map: dict[str, pd.Series],
    min_obs: int = 30,
) -> dict[str, float] | None:
    """Compute Variance Inflation Factor for each ETF factor.

    VIF_j = 1 / (1 - R²_j), where R²_j comes from regressing factor j on all
    other factors. Detects multicollinearity that makes OLS betas unreliable.

    Interpretation:
        VIF < 5  → acceptable
        VIF 5-10 → moderate collinearity, betas may be unstable
        VIF > 10 → severe collinearity, betas are unreliable

    Args:
        etf_returns_map: {ETF: daily return Series} for each factor.
        min_obs: Minimum overlapping observations required.

    Returns:
        {ETF: VIF} or None if < 2 factors or insufficient data.
    """
    etf_order = list(etf_returns_map.keys())
    if len(etf_order) < 2:
        return None

    df = pd.DataFrame(etf_returns_map).dropna()
    if len(df) < min_obs:
        return None

    vif: dict[str, float] = {}
    for etf in etf_order:
        others = [e for e in etf_order if e != etf]
        y = df[etf].to_numpy(dtype=float)
        X = np.column_stack([np.ones(len(y)), df[others].to_numpy(dtype=float)])

        try:
            beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        except np.linalg.LinAlgError:
            vif[etf] = float("inf")
            continue

        residuals = y - X @ beta
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y - np.mean(y)) ** 2))
        r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        vif[etf] = 1.0 / (1.0 - r2) if r2 < 1.0 else float("inf")

    return vif


def _build_aligned_matrix(
    target_returns: pd.Series,
    etf_returns_map: dict[str, pd.Series],
    min_obs: int = 30,
) -> tuple[np.ndarray, np.ndarray, list[str]] | None:
    """Align target returns with all ETF returns, dropping NaNs across all series.

    Returns (y_vector, X_matrix_with_intercept, etf_order) or None if insufficient data.
    """
    # Reason: align_returns only handles 2 series; here we need N+1 alignment.
    combined = {'target': target_returns}
    for etf, series in etf_returns_map.items():
        combined[etf] = series

    df = pd.DataFrame(combined).dropna()
    if len(df) < min_obs:
        return None

    etf_order = list(etf_returns_map.keys())
    y = df['target'].to_numpy(dtype=float)
    x_raw = df[etf_order].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(y)), x_raw])

    return y, X, etf_order


def _calc_ols_with_diagnostics(
    y: np.ndarray,
    X: np.ndarray,
    etf_order: list[str],
) -> OlsDiagnostics | None:
    """Run OLS and return betas, standard errors, residual_std, R².

    Standard errors: se(β) = sqrt(σ²_ε × diag((X'X)⁻¹))
    Residual std uses correct n - k denominator (degrees of freedom adjustment).
    """
    n, k = X.shape

    try:
        beta_vec, *_ = np.linalg.lstsq(X, y, rcond=None)
    except np.linalg.LinAlgError:
        return None

    residuals = y - X @ beta_vec
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))

    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    if np.isnan(r_squared):
        return None

    # Reason: correct degrees-of-freedom denominator is n - k (not n - 1)
    dof = n - k
    if dof <= 0:
        return None
    sigma2_eps = ss_res / dof
    residual_std = float(np.sqrt(sigma2_eps))

    # Reason: standard errors from (X'X)⁻¹ diagonal
    try:
        xtx_inv = np.linalg.inv(X.T @ X)
    except np.linalg.LinAlgError:
        return None
    beta_variances = sigma2_eps * np.diag(xtx_inv)
    # Reason: clamp negative variances from numerical noise to zero before sqrt
    beta_se = np.sqrt(np.maximum(beta_variances, 0.0))

    # Reason: beta_vec[0] is the intercept (α); betas/SEs start at index 1
    betas = {etf: float(beta_vec[i + 1]) for i, etf in enumerate(etf_order)}
    std_errors = {etf: float(beta_se[i + 1]) for i, etf in enumerate(etf_order)}

    return OlsDiagnostics(
        betas=betas,
        std_errors=std_errors,
        residual_std=residual_std,
        r_squared=r_squared,
    )


# ================================
# --> Ticker-level calculations
# ================================

def calc_ticker_factor_betas(
    ticker_returns: pd.Series,
    etf_returns_map: dict[str, pd.Series],
) -> tuple[dict[str, float], dict[str, float], float] | None:
    """Compute multi-factor OLS betas for a single ticker against multiple ETFs.

    R_ticker = α + β₁×R_ETF₁ + β₂×R_ETF₂ + ... + ε

    Returns:
        (betas, std_errors, residual_std) or None if insufficient data.
    """
    aligned = _build_aligned_matrix(ticker_returns, etf_returns_map)
    if aligned is None:
        return None

    y, X, etf_order = aligned
    diag = _calc_ols_with_diagnostics(y, X, etf_order)
    if diag is None:
        return None

    return diag.betas, diag.std_errors, diag.residual_std


def calc_ticker_stress_result(
    ticker: str,
    weight: float,
    ticker_returns: pd.Series,
    etf_returns_map: dict[str, pd.Series],
    shocks: dict[str, float],
) -> TickerStressResult:
    """Compute stress result for a single ticker.

    Runs multi-factor OLS to get betas, then applies shocks:
        expected_return = Σ(βᵢ × shockᵢ)
        weighted_pnl = weight × expected_return
    """
    result = calc_ticker_factor_betas(ticker_returns, etf_returns_map)

    if result is None:
        return TickerStressResult(
            ticker=ticker,
            weight=weight,
            factor_betas={},
        )

    betas, std_errors, _ = result

    expected = sum(betas.get(etf, 0.0) * shock for etf, shock in shocks.items())
    weighted_pnl = weight * expected

    return TickerStressResult(
        ticker=ticker,
        weight=weight,
        expected_return=expected,
        weighted_pnl=weighted_pnl,
        factor_betas=betas,
        factor_beta_std_errors=std_errors,
    )


# ================================
# --> Portfolio-level calculations
# ================================

def calc_portfolio_ols(
    portfolio_returns: pd.Series,
    etf_returns_map: dict[str, pd.Series],
) -> tuple[dict[str, float], float, float] | None:
    """Run portfolio-level multi-factor OLS for R², residual_std, and per-ETF sensitivities.

    R_portfolio = α + Σ(βᵢ × R_ETFᵢ) + ε

    Returns:
        (factor_betas, r_squared, residual_std) or None if insufficient data.
    """
    aligned = _build_aligned_matrix(portfolio_returns, etf_returns_map)
    if aligned is None:
        return None

    y, X, etf_order = aligned
    diag = _calc_ols_with_diagnostics(y, X, etf_order)
    if diag is None:
        return None

    return diag.betas, diag.r_squared, diag.residual_std


def calc_total_stressed_vol(
    portfolio_betas: dict[str, float],
    etf_returns_map: dict[str, pd.Series],
    residual_std: float,
) -> float | None:
    """Compute total stressed volatility (annualized) from factor + idiosyncratic decomposition.

    total_stressed_vol = sqrt(β' @ Cov(ETF) @ β + σ²_ε) × sqrt(252)

    Args:
        portfolio_betas: {ETF: beta} from portfolio OLS.
        etf_returns_map: {ETF: daily return Series} for factor covariance.
        residual_std: Daily residual standard deviation from portfolio OLS.

    Returns:
        Annualized total stressed volatility, or None if computation fails.
    """
    etf_order = list(portfolio_betas.keys())
    if not etf_order:
        return None

    # Reason: build aligned ETF returns matrix for covariance estimation
    etf_df = pd.DataFrame({e: etf_returns_map[e] for e in etf_order if e in etf_returns_map}).dropna()
    if len(etf_df) < 30:
        return None

    beta_vec = np.array([portfolio_betas[e] for e in etf_order])
    factor_cov = etf_df[etf_order].cov().to_numpy()

    systematic_var = float(beta_vec @ factor_cov @ beta_vec)
    idiosyncratic_var = residual_std ** 2
    total_daily_var = systematic_var + idiosyncratic_var

    if total_daily_var < 0:
        return None

    return float(np.sqrt(total_daily_var) * np.sqrt(252))


# ================================
# --> ETF contribution
# ================================

def calc_etf_contribution(
    etf: str,
    shock: float,
    portfolio_sensitivity: float | None,
    total_expected: float | None,
) -> EtfContribution:
    """Calculate how much of the portfolio stress comes from a single ETF shock.

    contribution = portfolio_sensitivity × shock
    pct_of_total = contribution / total_expected
    """
    if portfolio_sensitivity is None:
        return EtfContribution(etf=etf, shock=shock)

    contribution = portfolio_sensitivity * shock

    pct_of_total: float | None = None
    if total_expected is not None and total_expected != 0.0:
        pct_of_total = contribution / total_expected

    return EtfContribution(
        etf=etf,
        shock=shock,
        portfolio_sensitivity=portfolio_sensitivity,
        contribution=contribution,
        pct_of_total=pct_of_total,
    )
