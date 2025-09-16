from __future__ import annotations

import numpy as np
import pandas as pd
from app.core.calculations.core.config import DEFAULT_CONFIDENCE


def _to_psd(cov: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    """Make covariance matrix positive semi-definite in a numerically stable way.

    Strategy:
    - Sanitize inputs and enforce symmetry
    - Scale to correlation space (unit diagonal) to avoid extreme magnitudes
    - Floor eigenvalues to small positive and cap at n (corr eigvals ≤ n)
    - Reconstruct correlation, fix diagonal to 1, then scale back to covariance
    - Fallback to diagonal if anything becomes non-finite
    """
    cov = np.asarray(cov, dtype=float)
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    cov = (cov + cov.T) / 2.0

    n = cov.shape[0]
    if n == 0:
        return cov

    # Build scale factors from diagonal, guard against non-positive/NaN
    diag_cov = np.diag(cov)
    diag_cov = np.nan_to_num(diag_cov, nan=floor, posinf=floor, neginf=floor)
    diag_cov = np.clip(diag_cov, a_min=floor, a_max=None)
    std = np.sqrt(diag_cov)
    inv_std = 1.0 / np.where(std > 0.0, std, 1.0)

    # Convert to correlation space
    corr = (cov * inv_std[:, None]) * inv_std[None, :]
    corr = (corr + corr.T) / 2.0

    # Eigendecomposition with robust clipping in correlation space
    try:
        vals, vecs = np.linalg.eigh(corr)
    except np.linalg.LinAlgError:
        # Fall back to identity correlation (diagonal covariance)
        return np.diag(diag_cov)

    # Floor negative/invalid eigenvalues and cap excessively large ones
    vals = np.nan_to_num(vals, nan=floor, posinf=floor, neginf=floor)
    vals = np.clip(vals, a_min=floor, a_max=float(n))

    # Reconstruct correlation matrix and enforce unit diagonal
    corr_psd = vecs @ np.diag(vals) @ vecs.T
    corr_psd = np.nan_to_num(corr_psd, nan=0.0, posinf=0.0, neginf=0.0)
    corr_psd = (corr_psd + corr_psd.T) / 2.0
    np.fill_diagonal(corr_psd, 1.0)

    # Scale back to covariance space
    cov_psd = (corr_psd * std[:, None]) * std[None, :]
    cov_psd = np.nan_to_num(cov_psd, nan=0.0, posinf=0.0, neginf=0.0)
    cov_psd = (cov_psd + cov_psd.T) / 2.0
    # Ensure non-negative diagonal
    final_diag = np.clip(np.diag(cov_psd), a_min=floor, a_max=None)
    cov_psd[np.diag_indices_from(cov_psd)] = final_diag

    if not np.all(np.isfinite(cov_psd)):
        return np.diag(final_diag)

    return cov_psd


class RiskCalculator:
    """Basic risk utilities used broadly across the system."""

    @staticmethod
    def annualized_volatility(daily_returns: pd.Series, trading_days: int = 252) -> float:
        r = pd.Series(daily_returns).dropna().astype(float)
        if len(r) < 2:
            return np.nan
        return float(r.std(ddof=1) * np.sqrt(trading_days))

    @staticmethod
    def max_drawdown(close: pd.Series) -> float:
        c = pd.Series(close).dropna().astype(float)
        if c.empty:
            return np.nan
        # Compute drawdown from normalized equity curve (price proxy)
        equity = c / c.iloc[0]
        running_max = equity.cummax()
        drawdown = (equity / running_max) - 1.0
        return float(drawdown.min())

    @staticmethod
    def parametric_var(annual_vol: float, confidence: float = DEFAULT_CONFIDENCE, trading_days: int = 252, mean_daily: float | None = None) -> float:
        from scipy.stats import norm

        z = norm.ppf(confidence)
        daily_vol = annual_vol / np.sqrt(trading_days)
        if mean_daily is None:
            return float(z * daily_vol)
        # Include mean: positive magnitude VaR defined as minus the quantile approximation
        return float(-(mean_daily + z * daily_vol))

    @staticmethod
    def historical_var(portfolio_daily_returns: pd.Series, confidence: float = DEFAULT_CONFIDENCE) -> float:
        """Historical (non-parametric) VaR for 1-day horizon (positive magnitude)."""
        r = pd.Series(portfolio_daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        alpha_pct = (1 - confidence) * 100
        return float(-np.nanpercentile(r, alpha_pct))

    @staticmethod
    def expected_shortfall(portfolio_daily_returns: pd.Series, confidence: float = DEFAULT_CONFIDENCE) -> float:
        """Expected shortfall (CVaR) from historical distribution (positive magnitude)."""
        r = pd.Series(portfolio_daily_returns).dropna().astype(float)
        if r.empty:
            return np.nan
        alpha_pct = (1 - confidence) * 100
        q = np.nanpercentile(r, alpha_pct)
        tail = r[r <= q]
        return float(-tail.mean()) if not tail.empty else float(-q)

    @staticmethod
    def beta(asset_daily_returns: pd.Series, market_daily_returns: pd.Series) -> float:
        """CAPM beta using aligned daily returns (covariance/variance)."""
        df = pd.concat([asset_daily_returns, market_daily_returns], axis=1).dropna()
        if len(df) < 2:
            return np.nan
        cov = df.iloc[:, 0].cov(df.iloc[:, 1])
        var_mkt = df.iloc[:, 1].var(ddof=1)
        if var_mkt == 0 or np.isnan(var_mkt):
            return np.nan
        return float(cov / var_mkt)

    @staticmethod
    def correlation_matrix(returns_df: pd.DataFrame) -> pd.DataFrame:
        """Pairwise Pearson correlation of daily returns (handles NaN via drop)."""
        if returns_df.empty:
            return pd.DataFrame()
        return returns_df.corr(method="pearson")

    @staticmethod
    def covariance_matrix(returns_df: pd.DataFrame, annualize: bool = False, trading_days: int = 252) -> pd.DataFrame:
        """Covariance matrix of returns. Annualize if requested."""
        if returns_df.empty:
            return pd.DataFrame()
        cov = returns_df.cov()
        return cov * trading_days if annualize else cov

    @staticmethod
    def monte_carlo_var(
        weights: np.ndarray | pd.Series,
        returns_df: pd.DataFrame,
        confidence: float = DEFAULT_CONFIDENCE,
        n_simulations: int = 10000,
        use_mean: bool = True,
        random_state: int | None = None,
    ) -> float:
        """Monte Carlo 1-day VaR via MVN(μ, Σ) using daily covariance.

        - Align weights Series to returns_df.columns
        - Ensure Σ is PSD via eigenvalue floor
        - No tail clipping to avoid bias
        """
        if returns_df is None or returns_df.empty:
            return np.nan
        R = returns_df.astype(float)
        cols = list(R.columns)

        # Align weights
        if isinstance(weights, pd.Series):
            w = weights.reindex(cols).fillna(0.0).to_numpy(dtype=float)
        else:
            w = np.asarray(weights, dtype=float)
            if w.shape[0] != len(cols):
                raise ValueError("weights length must match returns_df.columns length")

        mu = R.mean(skipna=True).to_numpy(dtype=float)
        if not use_mean:
            mu = np.zeros_like(mu)
        Sigma = R.cov(min_periods=2).to_numpy(dtype=float)
        Sigma = _to_psd(Sigma)

        rng = np.random.default_rng(random_state)
        try:
            sims = rng.multivariate_normal(mean=mu, cov=Sigma, size=n_simulations, check_valid='raise')
        except np.linalg.LinAlgError:
            # Fallback: diagonal-only covariance
            Sigma = np.diag(np.clip(np.diag(Sigma), a_min=0.0, a_max=None))
            sims = rng.multivariate_normal(mean=mu, cov=Sigma, size=n_simulations)

        port = sims @ w
        port = port[np.isfinite(port)]
        if port.size == 0:
            return np.nan
        alpha_pct = (1 - confidence) * 100
        return float(-np.percentile(port, alpha_pct))

    @staticmethod
    def marginal_var(
        weights: np.ndarray | pd.Series,
        cov_daily: pd.DataFrame | np.ndarray,
        confidence: float = DEFAULT_CONFIDENCE,
        as_percent_of_portfolio_var: bool = False,
    ) -> tuple[pd.Series, pd.Series]:
        """Marginal and component VaR using daily covariance matrix."""
        from scipy.stats import norm

        # Build Sigma and index
        if isinstance(cov_daily, pd.DataFrame):
            Sigma = cov_daily.to_numpy(dtype=float)
            idx = list(cov_daily.index)
        else:
            Sigma = np.asarray(cov_daily, dtype=float)
            idx = None

        # Align weights to covariance order
        if isinstance(weights, pd.Series):
            if idx is None:
                idx = list(weights.index)
            w_series = weights if idx is None else weights.reindex(idx)
            w = w_series.fillna(0.0).to_numpy(dtype=float)
            idx = list(w_series.index)
        else:
            w = np.asarray(weights, dtype=float)
            if idx is None:
                idx = list(range(len(w)))
            if w.shape[0] != len(idx) or Sigma.shape[0] != len(idx) or Sigma.shape[1] != len(idx):
                raise ValueError("Dimensions of weights and covariance do not match")

        # Symmetrize & ensure PSD
        Sigma = _to_psd((Sigma + Sigma.T) / 2.0)

        z = float(norm.ppf(confidence))
        port_var_daily = float(w @ Sigma @ w)
        port_vol_daily = np.sqrt(max(port_var_daily, 0.0))
        if port_vol_daily == 0.0:
            mv = np.zeros_like(w)
            cv = np.zeros_like(w)
            return pd.Series(mv, index=idx), pd.Series(cv, index=idx)

        mv = (z * (Sigma @ w)) / port_vol_daily
        cv = w * mv

        if as_percent_of_portfolio_var:
            port_var_scalar = z * port_vol_daily
            if port_var_scalar != 0:
                cv = cv / port_var_scalar

        return pd.Series(mv, index=idx), pd.Series(cv, index=idx)

    @staticmethod
    def position_size_from_var_budget(
        var_budget_dollars: float,
        annual_vol: float,
        confidence: float = DEFAULT_CONFIDENCE,
        trading_days: int = 252,
    ) -> float:
        """Compute maximum position size (dollars) given a VaR dollar budget."""
        from scipy.stats import norm

        z = norm.ppf(confidence)
        daily_vol = annual_vol / np.sqrt(trading_days)
        if daily_vol == 0 or np.isnan(daily_vol):
            return 0.0
        return float(var_budget_dollars / (z * daily_vol))

    @staticmethod
    def diversification_ratio(weights: pd.Series, cov: pd.DataFrame) -> float:
        """Diversification ratio = weighted_avg_vol / portfolio_vol."""
        if weights.empty or cov.empty:
            return np.nan
        vols = np.sqrt(np.diag(cov.values))
        weighted_avg_vol = np.dot(np.abs(weights.values), vols)
        portfolio_vol = np.sqrt(weights.values @ cov.values @ weights.values)
        if portfolio_vol == 0:
            return np.inf
        return float(weighted_avg_vol / portfolio_vol)

    @staticmethod
    def up_down_beta(asset_daily_returns: pd.Series, market_daily_returns: pd.Series) -> tuple[float, float]:
        """Calculate separate up and down market betas."""
        df = pd.concat([asset_daily_returns, market_daily_returns], axis=1).dropna()
        if df.empty:
            return (np.nan, np.nan)
        asset = df.iloc[:, 0]
        market = df.iloc[:, 1]
        
        up_mask = market >= 0
        down_mask = market < 0
        
        up_beta = np.nan
        down_beta = np.nan
        
        if up_mask.sum() > 1:
            up_cov = asset[up_mask].cov(market[up_mask])
            up_var = market[up_mask].var(ddof=1)
            up_beta = float(up_cov / up_var) if up_var != 0 else np.nan
        
        if down_mask.sum() > 1:
            down_cov = asset[down_mask].cov(market[down_mask])
            down_var = market[down_mask].var(ddof=1)
            down_beta = float(down_cov / down_var) if down_var != 0 else np.nan
        
        return (up_beta, down_beta)

    @staticmethod
    def parametric_cvar(annual_vol: float, confidence: float = DEFAULT_CONFIDENCE, trading_days: int = 252) -> float:
        """Parametric CVaR assuming normal distribution."""
        from scipy.stats import norm
        alpha = 1 - confidence
        daily_vol = annual_vol / np.sqrt(trading_days)
        z = norm.ppf(alpha)
        cvar = daily_vol * norm.pdf(z) / alpha
        return float(cvar)

    @staticmethod
    def ulcer_index(close: pd.Series) -> float:
        """Ulcer Index - RMS of drawdowns."""
        c = pd.Series(close).dropna().astype(float)
        if c.empty:
            return np.nan
        equity = c / c.iloc[0]  # Normalize to start at 1 (prefer total-return equity if available)
        running_max = equity.cummax()
        drawdowns = (equity / running_max) - 1.0
        return float(np.sqrt(np.mean(np.square(drawdowns))))


