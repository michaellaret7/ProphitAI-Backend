from __future__ import annotations

import numpy as np
import pandas as pd


class RiskCalculator:
    """Basic risk utilities used broadly across the system."""

    @staticmethod
    def annualized_volatility(daily_returns: pd.Series, trading_days: int = 252) -> float:
        if daily_returns.empty:
            return 0.0
        return float(daily_returns.std(ddof=1) * np.sqrt(trading_days))

    @staticmethod
    def max_drawdown(close: pd.Series) -> float:
        if close.empty:
            return 0.0
        cumulative_max = close.expanding().max()
        safe_cum_max = cumulative_max.replace(0, np.nan)
        drawdown = (close - safe_cum_max) / safe_cum_max
        mdd = drawdown.min()
        return float(mdd if not np.isnan(mdd) else 0.0)

    @staticmethod
    def parametric_var(annual_vol: float, confidence: float = 0.99, trading_days: int = 252) -> float:
        from scipy.stats import norm

        z = norm.ppf(confidence)
        daily_vol = annual_vol / np.sqrt(trading_days)
        return float(z * daily_vol)

    @staticmethod
    def historical_var(portfolio_daily_returns: pd.Series, confidence: float = 0.99) -> float:
        """Historical (non-parametric) VaR for 1-day horizon (positive magnitude)."""
        if portfolio_daily_returns.empty:
            return 0.0
        alpha_pct = (1 - confidence) * 100
        var = -np.percentile(portfolio_daily_returns.dropna(), alpha_pct)
        return float(var)

    @staticmethod
    def expected_shortfall(portfolio_daily_returns: pd.Series, confidence: float = 0.99) -> float:
        """Expected shortfall (CVaR) from historical distribution (positive magnitude)."""
        if portfolio_daily_returns.empty:
            return 0.0
        threshold = -RiskCalculator.historical_var(portfolio_daily_returns, confidence)
        tail_losses = portfolio_daily_returns[portfolio_daily_returns <= threshold]
        if tail_losses.empty:
            return float(-threshold)
        return float(-tail_losses.mean())

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
        confidence: float = 0.99,
        n_simulations: int = 10000,
    ) -> float:
        """Monte Carlo 1-day VaR using multivariate normal with daily covariance.

        Improves numerical stability by sanitizing inputs, enforcing symmetry,
        jittering the covariance if needed, and using numpy's multivariate_normal.
        """
        if returns_df.empty:
            return 0.0
        # Sanitize inputs
        if isinstance(weights, pd.Series):
            weights = weights.values
        weights = np.asarray(weights, dtype=float)
        weights = np.nan_to_num(weights, nan=0.0, posinf=0.0, neginf=0.0)
        returns_df = returns_df.dropna().astype(float)
        mu = returns_df.mean().values.astype(float)
        cov = returns_df.cov().values.astype(float)  # daily covariance
        # Force symmetry
        cov = (cov + cov.T) / 2.0
        # Ensure finite values
        if not np.isfinite(cov).all():
            cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
        # Attempt simulation with increasing jitter if needed
        alpha_pct = (1 - confidence) * 100
        jitter = 1e-12
        for _ in range(5):
            try:
                sims = np.random.multivariate_normal(mean=mu, cov=cov, size=n_simulations, check_valid='raise', tol=1e-8)
                # Keep only finite rows to avoid runtime warnings in matmul
                finite_rows = np.isfinite(sims).all(axis=1)
                sims = sims[finite_rows]
                # Clip extreme tails to maintain numerical stability
                sims = np.clip(sims, -1.0, 1.0)
                port = np.dot(sims, weights)
                # Remove non-finite just in case
                port = port[np.isfinite(port)]
                if port.size == 0:
                    raise ValueError("No finite simulated returns")
                var = -np.percentile(port, alpha_pct)
                return float(var)
            except (np.linalg.LinAlgError, ValueError):
                # Add jitter to the diagonal and retry
                cov = cov + np.eye(cov.shape[0]) * jitter
                jitter *= 10
        # Last resort: diagonal-only covariance
        diag_cov = np.diag(np.clip(np.diag(cov), a_min=0.0, a_max=None))
        sims = np.random.multivariate_normal(mean=mu, cov=diag_cov, size=n_simulations)
        finite_rows = np.isfinite(sims).all(axis=1)
        sims = sims[finite_rows]
        sims = np.clip(sims, -1.0, 1.0)
        port = np.dot(sims, weights)
        port = port[np.isfinite(port)]
        if port.size == 0:
            return 0.0
        var = -np.percentile(port, alpha_pct)
        return float(var)

    @staticmethod
    def marginal_var(
        weights: np.ndarray | pd.Series,
        cov_daily: pd.DataFrame | np.ndarray,
        confidence: float = 0.99,
    ) -> tuple[pd.Series, pd.Series]:
        """Marginal and component VaR using daily covariance matrix.

        Returns (marginal_var_series, component_var_series) as proportions.
        """
        from scipy.stats import norm

        if isinstance(weights, pd.Series):
            w = weights.values
            idx = list(weights.index)
        else:
            w = np.asarray(weights)
            idx = list(range(len(w)))

        if isinstance(cov_daily, pd.DataFrame):
            Sigma = cov_daily.values
            idx = list(cov_daily.index)
        else:
            Sigma = np.asarray(cov_daily)

        z = norm.ppf(confidence)
        port_var_daily = float(w @ Sigma @ w)
        port_vol_daily = np.sqrt(max(port_var_daily, 0.0))
        if port_vol_daily == 0:
            mv = np.zeros_like(w)
        else:
            mv = (z * (Sigma @ w)) / port_vol_daily
        cv = w * mv
        return pd.Series(mv, index=idx), pd.Series(cv, index=idx)

    @staticmethod
    def position_size_from_var_budget(
        var_budget_dollars: float,
        annual_vol: float,
        confidence: float = 0.99,
        trading_days: int = 252,
    ) -> float:
        """Compute maximum position size (dollars) given a VaR dollar budget."""
        from scipy.stats import norm

        z = norm.ppf(confidence)
        daily_vol = annual_vol / np.sqrt(trading_days)
        if daily_vol == 0 or np.isnan(daily_vol):
            return 0.0
        return float(var_budget_dollars / (z * daily_vol))


