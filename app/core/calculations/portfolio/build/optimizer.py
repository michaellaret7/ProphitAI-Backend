"""Portfolio optimization algorithms."""

from __future__ import annotations

from typing import Dict, Optional
import numpy as np
import pandas as pd
from scipy import optimize

from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.core.config import DEFAULT_RF_ANNUAL


class PortfolioOptimizer:
    """Portfolio weight optimization using various algorithms.
    
    This is a skeleton implementation. Methods will be filled in subsequent steps.
    """

    def optimize_weights_risk_parity(self, cov: pd.DataFrame) -> pd.Series:
        """Calculate risk parity weights where each asset contributes equally to risk.
        
        Args:
            cov: Covariance matrix
            
        Returns:
            Series of weights
        """
        if cov.empty:
            return pd.Series(dtype=float)
        
        n = len(cov)
        
        # Simple risk parity: weight inversely proportional to volatility
        vols = np.sqrt(np.diag(cov.values))
        inv_vols = 1.0 / vols
        weights = inv_vols / inv_vols.sum()
        
        return pd.Series(weights, index=cov.index)
    
    def optimize_weights_min_variance(self, cov: pd.DataFrame, 
                                     bounds: Optional[Dict[str, tuple[float, float]]] = None) -> pd.Series:
        """Calculate minimum variance weights using quadratic programming.
        
        Args:
            cov: Covariance matrix
            bounds: Optional weight bounds per ticker
            
        Returns:
            Series of weights
        """
        if cov.empty:
            return pd.Series(dtype=float)
        
        n = len(cov)
        P = cov.values
        
        # Objective: minimize w^T P w (portfolio variance)
        def objective(w):
            return w @ P @ w
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds: default 0 to 1 for each weight
        if bounds:
            bnds = [bounds.get(ticker, (0, 1)) for ticker in cov.index]
        else:
            bnds = [(0, 1) for _ in range(n)]
        
        # Initial guess: equal weights
        w0 = np.full(n, 1.0 / n)
        
        # Optimize
        result = optimize.minimize(objective, w0, method='SLSQP', 
                                  bounds=bnds, constraints=constraints)
        
        if result.success:
            return pd.Series(result.x, index=cov.index)
        else:
            # Fallback to equal weights
            return pd.Series(w0, index=cov.index)
    
    def optimize_weights_max_sharpe(self, expected_returns: pd.Series, cov: pd.DataFrame,
                                   risk_free_rate: float = DEFAULT_RF_ANNUAL) -> pd.Series:
        """Calculate maximum Sharpe ratio weights.
        
        Args:
            expected_returns: Expected returns for each asset
            cov: Covariance matrix
            risk_free_rate: Annual risk-free rate
            
        Returns:
            Series of weights
        """
        if cov.empty or expected_returns.empty:
            return pd.Series(dtype=float)
        
        n = len(cov)
        
        # Negative Sharpe ratio for minimization
        def neg_sharpe(w):
            port_return = w @ expected_returns.values
            port_vol = np.sqrt(w @ cov.values @ w)
            return -(port_return - risk_free_rate) / port_vol if port_vol > 0 else 0
        
        # Constraints: weights sum to 1
        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        
        # Bounds: 0 to 1 for each weight
        bounds = [(0, 1) for _ in range(n)]
        
        # Initial guess: equal weights
        w0 = np.full(n, 1.0 / n)
        
        # Optimize
        result = optimize.minimize(neg_sharpe, w0, method='SLSQP',
                                  bounds=bounds, constraints=constraints)
        
        if result.success:
            return pd.Series(result.x, index=cov.index)
        else:
            # Fallback to equal weights
            return pd.Series(w0, index=cov.index)
    
    def optimize_weights_max_diversification(self, cov: pd.DataFrame) -> pd.Series:
        """Maximum Diversification: maximize diversification ratio = (w' * sigma) / sqrt(w' * Sigma * w)

        Long-only, sum-to-1 constraints.
        """
        if cov.empty:
            return pd.Series(dtype=float)
        n = len(cov)
        Sigma = cov.values
        sigma = np.sqrt(np.diag(Sigma))

        # Objective: negative diversification ratio (since we minimize)
        def neg_diversification_ratio(w: np.ndarray) -> float:
            num = w @ sigma
            den = np.sqrt(max(w @ Sigma @ w, 1e-16))
            return -(num / den) if den > 0 else 0.0

        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0.0, 1.0) for _ in range(n)]
        w0 = np.full(n, 1.0 / n)

        result = optimize.minimize(neg_diversification_ratio, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        if result.success:
            return pd.Series(result.x, index=cov.index)
        return pd.Series(w0, index=cov.index)

    def optimize_weights_min_correlation(self, corr: pd.DataFrame) -> pd.Series:
        """Minimum Correlation Algorithm (MCA): minimize average pairwise correlation of the portfolio.

        Implemented via minimizing w' C w subject to sum(w)=1, w>=0 with C as correlation matrix with zeros on the diagonal
        to focus on off-diagonal correlations.
        """
        if corr.empty:
            return pd.Series(dtype=float)
        n = len(corr)
        C = corr.copy().values.astype(float)
        np.fill_diagonal(C, 0.0)

        def objective(w: np.ndarray) -> float:
            return float(w @ C @ w)

        constraints = {'type': 'eq', 'fun': lambda w: np.sum(w) - 1}
        bounds = [(0.0, 1.0) for _ in range(n)]
        w0 = np.full(n, 1.0 / n)

        result = optimize.minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=constraints)
        if result.success:
            return pd.Series(result.x, index=corr.index)
        return pd.Series(w0, index=corr.index)
    
    def apply_constraints(self, weights: pd.Series, 
                         max_position_weight: float = 0.10,
                         min_position_weight: float = 0.0) -> pd.Series:
        """Apply per-name min/max caps and project onto the simplex.

        This performs a bounded-simplex projection so that the returned weights:
          - are within [min_position_weight, max_position_weight] elementwise
          - are non-negative and finite
          - sum exactly to 1.0
          - stay as close as possible to the original weights in proportion
        """
        if weights.empty:
            return weights

        w = pd.Series(weights.astype(float).clip(lower=0.0).fillna(0.0), index=weights.index)

        n = len(w)
        if n == 0:
            return w

        # Handle degenerate bounds
        max_w = float(max_position_weight) if max_position_weight is not None else 1.0
        max_w = max(0.0, min(1.0, max_w))
        min_w = float(min_position_weight) if min_position_weight is not None else 0.0
        min_w = max(0.0, min(max_w, min_w))

        # Feasibility checks and shortcuts
        # If bounds force equal weights (e.g., min_w * n >= 1), use equal weight
        if min_w * n >= 1.0:
            return pd.Series(np.full(n, 1.0 / n), index=w.index)

        # If max bound is extremely small but feasible, start from clipped
        if max_w <= 0.0:
            return pd.Series(np.full(n, 1.0 / n), index=w.index)

        # Initial normalization to avoid numerical issues
        s = float(w.sum())
        if s <= 0.0 or not np.isfinite(s):
            w = pd.Series(np.full(n, 1.0 / n), index=w.index)
        else:
            w = w / s

        # Water-filling style projection onto bounded simplex
        lower = pd.Series(np.full(n, min_w), index=w.index)
        upper = pd.Series(np.full(n, max_w), index=w.index)

        fixed = pd.Series(np.zeros(n, dtype=bool), index=w.index)
        alloc = pd.Series(np.zeros(n, dtype=float), index=w.index)
        remaining_mass = 1.0

        # To preserve proportions for non-fixed names
        base = w.copy()
        base[base < 0.0] = 0.0
        if float(base.sum()) <= 0.0:
            base = pd.Series(np.full(n, 1.0 / n), index=w.index)

        iteration_guard = 0
        while True:
            iteration_guard += 1
            if iteration_guard > 5 * n:
                # Safety break to avoid infinite loops; fallback to equal within bounds
                eq = pd.Series(np.full(n, remaining_mass / max(1, (~fixed).sum())), index=w.index)
                alloc[~fixed] = eq[~fixed]
                break

            active = ~fixed
            if not active.any():
                break

            base_active = base[active]
            total_base = float(base_active.sum())
            if total_base <= 0.0 or not np.isfinite(total_base):
                # Distribute equally among active if base degenerate
                proposed = pd.Series(np.full(active.sum(), remaining_mass / active.sum()), index=base_active.index)
            else:
                scale = remaining_mass / total_base
                proposed = base_active * scale

            # Enforce bounds on proposed
            hit_upper = proposed > upper[active]
            hit_lower = proposed < lower[active]

            if not hit_upper.any() and not hit_lower.any():
                alloc[active] = proposed
                break

            # Fix any that hit bounds and update remaining mass
            if hit_upper.any():
                idx = proposed[hit_upper].index
                alloc[idx] = upper[idx]
                fixed[idx] = True
            if hit_lower.any():
                idx = proposed[hit_lower].index
                alloc[idx] = lower[idx]
                fixed[idx] = True

            remaining_mass = 1.0 - float(alloc[fixed].sum())
            if remaining_mass < 0.0:
                # Numerical guard
                remaining_mass = 0.0
            # Re-weight base for remaining active set only
            if active.any():
                base = base.where(~fixed, 0.0)

        # Final small numerical cleanup
        alloc = alloc.clip(lower=lower, upper=upper)
        total = float(alloc.sum())
        if total > 0.0:
            alloc = alloc / total
        else:
            alloc = pd.Series(np.full(n, 1.0 / n), index=w.index)

        return alloc
    
    def calculate_position_sizes(self, weights: pd.Series, 
                                portfolio_value: float,
                                leverage: float = 1.0) -> pd.Series:
        """Calculate dollar position sizes from weights.
        
        Args:
            weights: Portfolio weights (should sum to 1)
            portfolio_value: Total portfolio value in dollars
            leverage: Leverage multiplier (e.g., 1.5 for 150% exposure)
            
        Returns:
            Series of position sizes in dollars
        """
        if weights.empty:
            return pd.Series(dtype=float)
        
        # Calculate leveraged portfolio value
        leveraged_value = portfolio_value * leverage
        
        # Calculate position sizes
        position_sizes = weights * leveraged_value
        
        return position_sizes
    
    def optimize_weights_risk_based(self, cov: pd.DataFrame, base_convictions: Optional[pd.Series] = None) -> pd.Series:
        """Calculate risk-based weights using inverse risk weighting.
        
        This is the original correlation portfolio builder's approach:
        - Calculate risk score = volatility * (1 + avg_correlation)
        - Weight inversely to risk score
        
        Args:
            cov: Covariance matrix
            base_convictions: Base conviction weights to adjust
            
        Returns:
            Series of risk-adjusted weights
        """
        if cov.empty:
            return pd.Series(dtype=float)
        
        n = len(cov)
        tickers = list(cov.index)
        
        # If no base convictions, use equal weight
        if base_convictions is None:
            base_convictions = pd.Series(np.full(n, 1.0 / n), index=tickers)
        
        # Get individual volatilities from diagonal
        individual_vols = np.sqrt(np.diag(cov.values))
        
        # Calculate risk scores for each asset
        risk_scores = {}
        cov_matrix = cov.values
        
        for i, ticker in enumerate(tickers):
            # Individual volatility component
            vol_score = individual_vols[i]
            
            # Correlation component (average absolute correlation with others)
            corr_with_others = []
            for j in range(n):
                if i != j and individual_vols[i] > 0 and individual_vols[j] > 0:
                    correlation = cov_matrix[i, j] / (individual_vols[i] * individual_vols[j])
                    corr_with_others.append(abs(correlation))
            
            avg_corr = np.mean(corr_with_others) if corr_with_others else 0
            
            # Combined risk score (higher = riskier)
            risk_scores[ticker] = vol_score * (1 + avg_corr)
        
        # Normalize risk scores
        max_risk = max(risk_scores.values()) if risk_scores else 1.0
        
        # Calculate risk-adjusted weights (inverse risk weighting)
        adjusted_weights = {}
        for ticker in tickers:
            # Lower weight for higher risk assets
            if risk_scores[ticker] > 0:
                risk_adjustment = max_risk / risk_scores[ticker]
            else:
                risk_adjustment = 1.0
            adjusted_weights[ticker] = base_convictions.get(ticker, 0) * risk_adjustment
        
        # Normalize to sum to 1
        weights_series = pd.Series(adjusted_weights)
        total = weights_series.sum()
        if total > 0:
            weights_series = weights_series / total
        
        return weights_series


