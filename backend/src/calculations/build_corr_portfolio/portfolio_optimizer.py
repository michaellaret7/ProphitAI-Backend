"""
Portfolio optimization module for correlation-aware portfolio builder.
Handles weight optimization and risk-based allocation.
"""

import numpy as np
from typing import Dict, Optional


class PortfolioOptimizer:
    """Handles portfolio weight optimization using risk-based strategies."""
    
    def __init__(self, leverage: float = 1.0, target_net_exposure: Optional[float] = None, 
                 max_position_weight: float = 0.10, target_annual_vol: float = 0.10):
        """
        Initialize the portfolio optimizer.
        
        Parameters:
        -----------
        leverage : float
            Leverage multiplier (e.g., 1.5 for 150% gross exposure)
        target_net_exposure : Optional[float]
            Target net exposure as fraction of base capital
        max_position_weight : float
            Maximum weight for any single position
        target_annual_vol : float
            Target annual volatility for the portfolio
        """
        self.leverage = leverage
        self.target_net_exposure = target_net_exposure
        self.max_position_weight = max_position_weight
        self.target_annual_vol = target_annual_vol
    
    def risk_based_portfolio(self, tickers: Dict[str, Dict], covariance_matrix, 
                            base_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Adjust portfolio weights based on risk contributions using full covariance matrix.
        Each position is sized inversely to its contribution to portfolio risk.
        
        Parameters:
        -----------
        tickers : Dict[str, Dict]
            Dictionary with ticker information including position and conviction
        covariance_matrix : pd.DataFrame
            Covariance matrix of returns
        base_weights : Optional[Dict[str, float]]
            Base weights to start from (if None, uses convictions)
            
        Returns:
        --------
        Dict[str, float]: Optimized portfolio weights
        """
        if base_weights is None:
            base_weights = {ticker: tickers[ticker]['conviction'] for ticker in tickers}
        
        ticker_list = list(tickers.keys())
        cov_matrix = covariance_matrix.loc[ticker_list, ticker_list].values
        
        # Get individual volatilities from diagonal
        individual_vols = np.sqrt(np.diag(cov_matrix))
        
        # Calculate risk scores for each asset
        risk_scores = {}
        for i, ticker in enumerate(ticker_list):
            # Individual volatility component
            vol_score = individual_vols[i]
            
            # Correlation component (average absolute correlation with others)
            corr_with_others = []
            for j in range(len(ticker_list)):
                if i != j:
                    correlation = cov_matrix[i, j] / (individual_vols[i] * individual_vols[j])
                    corr_with_others.append(abs(correlation))
            avg_corr = np.mean(corr_with_others)
            
            # Combined risk score (higher = riskier)
            risk_scores[ticker] = vol_score * (1 + avg_corr)
        
        # Normalize risk scores
        max_risk = max(risk_scores.values())
        
        # Calculate risk-adjusted weights (inverse risk weighting)
        adjusted_weights = {}
        for ticker in ticker_list:
            # Lower weight for higher risk assets
            risk_adjustment = max_risk / risk_scores[ticker]
            adjusted_weights[ticker] = base_weights[ticker] * risk_adjustment
        
        # Separate long and short positions
        long_weights = {t: w for t, w in adjusted_weights.items() if tickers[t]['position'] == 'long'}
        short_weights = {t: w for t, w in adjusted_weights.items() if tickers[t]['position'] == 'short'}
        
        # Normalize within each group
        long_total = sum(long_weights.values())
        short_total = sum(short_weights.values())
        
        if long_total > 0:
            long_weights = {k: v/long_total for k, v in long_weights.items()}
        if short_total > 0:
            short_weights = {k: v/short_total for k, v in short_weights.items()}
        
        # Apply target net exposure if specified
        if self.target_net_exposure is not None:
            # Calculate target long and short values
            gross_exposure = self.leverage
            net_exposure = self.target_net_exposure
            
            # Validate that target net exposure is achievable
            if abs(net_exposure) > gross_exposure:
                raise ValueError(f"Target net exposure ({net_exposure}) cannot exceed gross exposure ({gross_exposure})")
            
            # Solve: long - short = net, long + short = gross
            target_long_pct = (gross_exposure + net_exposure) / 2
            target_short_pct = (gross_exposure - net_exposure) / 2
            
            # Validate we have both long and short positions if needed
            if target_long_pct > 0 and len(long_weights) == 0:
                raise ValueError("Target net exposure requires long positions but none provided")
            if target_short_pct > 0 and len(short_weights) == 0:
                raise ValueError("Target net exposure requires short positions but none provided")
            
            # Scale weights to hit targets
            final_weights = {}
            for ticker, weight in long_weights.items():
                final_weights[ticker] = weight * target_long_pct
            for ticker, weight in short_weights.items():
                final_weights[ticker] = weight * target_short_pct
        else:
            # Natural allocation based on convictions
            total_conviction = sum(base_weights.values())
            final_weights = {k: v/total_conviction for k, v in adjusted_weights.items()}
        
        return final_weights
    
    def apply_position_signs(self, weights: Dict[str, float], tickers: Dict[str, Dict]) -> Dict[str, float]:
        """Apply long/short position signs to weights."""
        signed_weights = {}
        for ticker, weight in weights.items():
            if tickers[ticker]['position'] == 'short':
                signed_weights[ticker] = -weight
            else:
                signed_weights[ticker] = weight
        return signed_weights
    
    def apply_position_weight_cap_signed(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Apply maximum position weight cap to signed weights (positive for long, negative for short).
        Redistributes excess weight proportionally to uncapped positions in the same group.
        """
        # Separate long and short positions based on sign
        long_weights = {t: w for t, w in weights.items() if w > 0}
        short_weights = {t: abs(w) for t, w in weights.items() if w < 0}  # Convert to positive for capping
        
        # Apply cap to each group separately
        capped_long = self._cap_weights_group(long_weights)
        capped_short = self._cap_weights_group(short_weights)
        
        # Combine back with proper signs
        result = {}
        result.update(capped_long)
        for ticker, weight in capped_short.items():
            result[ticker] = -weight  # Re-apply negative sign for shorts
        
        return result
    
    def _cap_weights_group(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Cap weights within a group (long or short) and redistribute excess."""
        if not weights:
            return weights
            
        result = weights.copy()
        max_iterations = 10  # Prevent infinite loops
        
        for _ in range(max_iterations):
            # Find positions exceeding cap
            capped_positions = []
            excess_weight = 0
            
            for ticker, weight in result.items():
                if weight > self.max_position_weight:
                    excess_weight += weight - self.max_position_weight
                    result[ticker] = self.max_position_weight
                    capped_positions.append(ticker)
            
            # If no positions exceed cap, we're done
            if not capped_positions:
                break
            
            # Redistribute excess weight to uncapped positions
            uncapped_positions = [t for t in result.keys() if t not in capped_positions]
            if uncapped_positions:
                # Calculate redistribution proportionally
                uncapped_total = sum(result[t] for t in uncapped_positions)
                if uncapped_total > 0:
                    for ticker in uncapped_positions:
                        result[ticker] += excess_weight * (result[ticker] / uncapped_total)
        
        return result
