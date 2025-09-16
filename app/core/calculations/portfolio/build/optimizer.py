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
        """Apply position constraints to weights.
        
        Args:
            weights: Raw weights
            max_position_weight: Maximum weight per position
            min_position_weight: Minimum weight per position
            
        Returns:
            Constrained weights normalized to sum to 1
        """
        if weights.empty:
            return weights
        
        # Apply min/max constraints
        constrained = weights.clip(lower=min_position_weight, upper=max_position_weight)
        
        # Renormalize to sum to 1
        total = constrained.sum()
        if total > 0:
            return constrained / total
        else:
            # If all weights are zero, return equal weights
            n = len(weights)
            return pd.Series(np.full(n, 1.0 / n), index=weights.index)
    
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
    
    def optimize_weights_risk_based(self, cov: pd.DataFrame, 
                                   base_convictions: Optional[pd.Series] = None) -> pd.Series:
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


