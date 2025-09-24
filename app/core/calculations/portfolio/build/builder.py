"""Main orchestrator for correlation-aware portfolio building."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

from app.core.calculations.core import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.core.calculations.risk.calculator import RiskCalculator
from app.core.calculations.risk.liquidity import LiquidityCalculator
from app.core.calculations.performance.calculator import PerformanceCalculator
from app.core.calculations.portfolio.correlation import CorrelationAnalysis
from app.core.calculations.portfolio.build.optimizer import PortfolioOptimizer
from app.core.calculations.core.config import DEFAULT_CONFIDENCE

class CorrelationPortfolioBuilder:
    """Portfolio builder that incorporates correlation analysis.
    
    This is a skeleton implementation. Methods will be filled in subsequent steps.
    """
    
    def __init__(self, data_service: Optional[DataService] = None):
        """Initialize the portfolio builder.
        
        Args:
            data_service: Optional DataService instance. If not provided, creates a new one.
        """
        self.data_service = data_service or DataService()
        self.returns_calc = ReturnsCalculator()
        self.risk_calc = RiskCalculator()
        self.liquidity_calc = LiquidityCalculator()
        self.perf_calc = PerformanceCalculator()
        self.optimizer = PortfolioOptimizer()
        self.correlation = CorrelationAnalysis()
        
        # Cache for returns data
        self._returns_cache: Optional[pd.DataFrame] = None
        self._price_cache: Optional[Dict[str, pd.Series]] = None
        self._liquidity_scores: Optional[Dict[str, float]] = None
    
    def build_portfolio(self, tickers: Dict[str, Dict], target_annual_vol: float, 
                       portfolio_value: float, leverage: float = 1.0,
                       target_net_exposure: Optional[float] = None,
                       lookback_days: int = 252, max_position_weight: float = 0.10) -> Dict:
        """Build portfolio with correlation-aware optimization.
        
        Args:
            tickers: Dictionary with ticker symbols as keys and dict containing:
                    - 'allocation': Decimal risk allocation (e.g., 0.10 = 10% of risk budget)
                                   Allocations are normalized within long/short groups
                    - 'position': Either 'long' or 'short'
            target_annual_vol: Target annual volatility (e.g., 0.10 for 10%)
            portfolio_value: Total portfolio value in dollars (base capital before leverage)
            leverage: Leverage multiplier (e.g., 1.5 for 150% gross exposure)
            target_net_exposure: Target net exposure as fraction of base capital 
                                (e.g., 0.35 for 35%, None for natural exposure)
            lookback_days: Number of days for historical data
            max_position_weight: Maximum weight for any single position
            
        Returns:
            Portfolio results dictionary
        """
        try:
            # Step 1: Extract ticker list and validate
            ticker_list = list(tickers.keys())
            clean_tickers = self._validate_tickers(ticker_list)
            if not clean_tickers:
                return {"error": "No valid tickers provided"}
            
            # Step 2: Fetch price data
            price_data = self.fetch_and_prepare_data(clean_tickers, lookback_days)
            if not self._validate_data(price_data):
                return {"error": "Failed to fetch valid price data"}
            
            # Step 2.5: Get liquidity scores for all tickers
            liquidity_scores = self.get_liquidity_scores(clean_tickers)
            
            # Step 3: Calculate returns
            returns_df = self.calculate_returns(price_data)
            if returns_df.empty:
                return {"error": "Failed to calculate returns"}
            
            # Step 4: Calculate optimal weights with proper constraint enforcement
            # This now handles net exposure and position caps correctly
            weights = self.calculate_optimal_weights_with_positions(
                returns_df, tickers, target_net_exposure, liquidity_scores
            )
            
            # Step 4.5: Scale to target volatility while respecting caps
            # This ensures caps are never violated during volatility scaling
            weights = self.scale_to_target_volatility_with_caps(
                weights, returns_df, target_annual_vol, tickers, liquidity_scores
            )
            
            # Step 5: Validate constraints are satisfied
            validation_errors = self.validate_portfolio_constraints(
                weights, tickers, liquidity_scores, target_net_exposure
            )
            if validation_errors:
                print(f"WARNING: Constraint violations detected: {validation_errors}")
            
            # Step 6: Generate risk metrics
            risk_metrics = self.generate_risk_metrics(weights, returns_df)
            
            # Step 7: Calculate position sizes with leverage
            position_sizes = self.optimizer.calculate_position_sizes(
                weights, portfolio_value, leverage
            )
            
            # Step 8: Calculate exposure metrics
            long_exposure = sum(w for t, w in weights.items() 
                              if weights[t] > 0)  # Use actual weight sign, not tickers dict
            short_exposure = sum(abs(w) for t, w in weights.items() 
                               if weights[t] < 0)  # Use actual weight sign
            net_exposure = long_exposure - short_exposure
            gross_exposure = long_exposure + short_exposure
            
            # Create final portfolio in allocation/position format
            final_portfolio = {}
            for ticker, weight in weights.items():
                final_portfolio[ticker] = {
                    "allocation": round(abs(float(weight)), 5),
                    "position": "long" if float(weight) > 0 else "short"
                }
            
            return {
                "status": "success",
                "weights": weights.to_dict(),
                "position_sizes": position_sizes.to_dict(),
                "risk_metrics": risk_metrics,
                "target_vol": target_annual_vol,
                "portfolio_value": portfolio_value,
                "leverage": leverage,
                "target_net_exposure": target_net_exposure,
                "actual_net_exposure": net_exposure,
                "gross_exposure": gross_exposure,
                "long_exposure": long_exposure,
                "short_exposure": short_exposure,
                "final_portfolio": final_portfolio
            }
            
        except Exception as e:
            return {"error": f"Portfolio build failed: {str(e)}"}
    
    def get_liquidity_scores(self, tickers: list[str]) -> Dict[str, float]:
        """Get liquidity scores for all tickers.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Dictionary of liquidity scores (0-1) keyed by ticker
        """
        if self._liquidity_scores is not None:
            # Return cached scores if available
            return self._liquidity_scores
        
        scores = {}
        for ticker in tickers:
            try:
                result = self.liquidity_calc.analyze_ticker(ticker, lookback_days=30)
                scores[ticker] = result.get('composite_score', 0.5)  # Default to 0.5 if error
            except:
                scores[ticker] = 0.5  # Default mid-liquidity on error
        
        self._liquidity_scores = scores
        return scores
    
    def fetch_and_prepare_data(self, tickers: list[str], 
                               lookback_days: int = 252,
                               end_date: Optional[datetime] = None) -> Dict[str, pd.Series]:
        """Fetch and prepare price data for analysis using DataService.
        
        Args:
            tickers: List of ticker symbols
            lookback_days: Number of days to look back for historical data
            end_date: End date for data fetch. Defaults to today.
            
        Returns:
            Dictionary of price series keyed by ticker
        """
        if not tickers:
            return {}
        
        # Set date range
        end = end_date or datetime.now()
        start = end - timedelta(days=lookback_days)
        
        # Use DataService.get_bulk_close_series() for efficient fetching
        price_data = self.data_service.get_bulk_close_series(tickers, start, end)
        
        return price_data
    
    def calculate_optimal_weights(self, returns: pd.DataFrame, 
                                 method: str = "min_variance") -> pd.Series:
        """Calculate optimal portfolio weights using specified method.
        
        Args:
            returns: DataFrame of returns
            method: Optimization method ('min_variance', 'risk_parity', 'max_sharpe')
            
        Returns:
            Series of optimal weights
        """
        if returns.empty:
            return pd.Series()
        
        # Calculate covariance matrix
        cov = self.correlation.covariance_matrix(returns, annualize=True)
        
        # Select optimization method
        if method == "risk_parity":
            weights = self.optimizer.optimize_weights_risk_parity(cov)
        elif method == "max_sharpe":
            # Calculate expected returns (mean historical returns)
            expected_returns = returns.mean() * 252  # Annualize
            weights = self.optimizer.optimize_weights_max_sharpe(expected_returns, cov)
        else:  # Default to min_variance
            weights = self.optimizer.optimize_weights_min_variance(cov)
        
        # Apply constraints
        weights = self.optimizer.apply_constraints(weights)
        
        return weights
    
    def generate_risk_metrics(self, weights: pd.Series, returns: pd.DataFrame) -> Dict:
        """Generate risk metrics for the portfolio using RiskCalculator.
        
        Args:
            weights: Portfolio weights
            returns: Returns data
        
        Returns:
            Dictionary of risk metrics
        """
        if weights.empty or returns.empty:
            return {}
        
        # Calculate portfolio returns
        portfolio_returns = (returns * weights).sum(axis=1)
        
        # Calculate cumulative portfolio value for drawdown calculation
        # Start with $1 and compound the returns
        portfolio_value = (1 + portfolio_returns).cumprod()
        
        # Calculate covariance matrix
        cov = self.correlation.covariance_matrix(returns, annualize=True)
        
        # Risk metrics using RiskCalculator
        metrics = {
            "annual_volatility": self.risk_calc.annualized_volatility(portfolio_returns),
            "max_drawdown": self.risk_calc.max_drawdown(portfolio_value),  # Pass cumulative value, not returns
            "var_99": self.risk_calc.historical_var(portfolio_returns, confidence=DEFAULT_CONFIDENCE),
            "expected_shortfall": self.risk_calc.expected_shortfall(portfolio_returns),
            "sharpe_ratio": self.perf_calc.sharpe_ratio(portfolio_returns),
        }
        
        # Add correlation metrics
        corr = self.correlation.correlation_matrix(returns)
        metrics.update(self.correlation.concentration_risk_metrics(corr))
        metrics["diversification_ratio"] = self.correlation.effective_diversification_ratio(corr)
        
        return metrics
    
    def _validate_data(self, price_data: Dict[str, pd.Series]) -> bool:
        """Validate fetched price data.
        
        Args:
            price_data: Dictionary of price series
            
        Returns:
            True if data is valid, False otherwise
        """
        if not price_data:
            return False
        
        for ticker, series in price_data.items():
            if series is None or series.empty:
                return False
            if series.isna().all():
                return False
        
        return True
    
    def _validate_tickers(self, tickers: list[str]) -> list[str]:
        """Validate and clean ticker list.
        
        Args:
            tickers: List of ticker symbols
            
        Returns:
            Cleaned list of valid tickers
        """
        if not tickers:
            return []
        
        # Remove duplicates and clean
        cleaned = []
        seen = set()
        for ticker in tickers:
            if ticker and ticker.upper() not in seen:
                cleaned.append(ticker.upper())
                seen.add(ticker.upper())
        
        return cleaned
    
    def calculate_raw_optimal_weights(self, returns: pd.DataFrame,
                                      tickers: Dict[str, Dict],
                                      method: str = "risk_based") -> pd.Series:
        """Calculate raw optimal weights without any constraints.
        
        Args:
            returns: DataFrame of returns
            tickers: Dictionary with ticker info including position and allocation
            method: Optimization method
            
        Returns:
            Series of raw optimized weights (negative for shorts)
        """
        if returns.empty:
            return pd.Series()
        
        # Separate long and short positions
        long_tickers = [t for t in tickers if tickers[t]['position'] == 'long']
        short_tickers = [t for t in tickers if tickers[t]['position'] == 'short']
        
        # Get allocations
        base_allocations = {}
        for ticker in tickers:
            if ticker in returns.columns:
                base_allocations[ticker] = tickers[ticker].get('allocation', 0.1)
        
        # Get covariance matrix
        cov = self.correlation.covariance_matrix(returns, annualize=True)
        
        # Optimize long positions
        long_weights = {}
        if long_tickers and any(t in base_allocations for t in long_tickers):
            long_allocations = {t: base_allocations[t] for t in long_tickers if t in base_allocations}
            long_alloc_sum = sum(long_allocations.values())
            if long_alloc_sum > 0:
                long_norm_alloc = {k: v/long_alloc_sum for k, v in long_allocations.items()}
            else:
                long_norm_alloc = {k: 1.0/len(long_allocations) for k in long_allocations}
            
            long_returns = returns[long_tickers]
            long_cov = cov.loc[long_tickers, long_tickers]
            
            if method == "risk_parity":
                long_opt = self.optimizer.optimize_weights_risk_parity(long_cov)
            elif method == "max_sharpe":
                expected_returns = long_returns.mean() * 252
                long_opt = self.optimizer.optimize_weights_max_sharpe(expected_returns, long_cov)
            elif method == "min_variance":
                long_opt = self.optimizer.optimize_weights_min_variance(long_cov)
            else:  # risk_based
                alloc_series = pd.Series(long_norm_alloc)
                long_opt = self.optimizer.optimize_weights_risk_based(long_cov, alloc_series)
            
            for ticker in long_tickers:
                opt_weight = long_opt.get(ticker, 0)
                alloc_weight = long_norm_alloc.get(ticker, 0)
                long_weights[ticker] = 0.5 * opt_weight + 0.5 * alloc_weight
        
        # Optimize short positions
        short_weights = {}
        if short_tickers and any(t in base_allocations for t in short_tickers):
            short_allocations = {t: base_allocations[t] for t in short_tickers if t in base_allocations}
            short_alloc_sum = sum(short_allocations.values())
            if short_alloc_sum > 0:
                short_norm_alloc = {k: v/short_alloc_sum for k, v in short_allocations.items()}
            else:
                short_norm_alloc = {k: 1.0/len(short_allocations) for k in short_allocations}
            
            short_returns = returns[short_tickers]
            short_cov = cov.loc[short_tickers, short_tickers]
            
            if method == "risk_parity":
                short_opt = self.optimizer.optimize_weights_risk_parity(short_cov)
            elif method == "max_sharpe":
                expected_returns = short_returns.mean() * 252
                short_opt = self.optimizer.optimize_weights_max_sharpe(expected_returns, short_cov)
            elif method == "min_variance":
                short_opt = self.optimizer.optimize_weights_min_variance(short_cov)
            else:  # risk_based
                alloc_series = pd.Series(short_norm_alloc)
                short_opt = self.optimizer.optimize_weights_risk_based(short_cov, alloc_series)
            
            for ticker in short_tickers:
                opt_weight = short_opt.get(ticker, 0)
                alloc_weight = short_norm_alloc.get(ticker, 0)
                short_weights[ticker] = 0.5 * opt_weight + 0.5 * alloc_weight
        
        # Normalize within groups
        if long_weights:
            long_total = sum(long_weights.values())
            if long_total > 0:
                long_weights = {k: v/long_total for k, v in long_weights.items()}
        
        if short_weights:
            short_total = sum(short_weights.values())
            if short_total > 0:
                short_weights = {k: v/short_total for k, v in short_weights.items()}
        
        # Combine with appropriate signs (initially equal allocation)
        final_weights = {}
        for ticker, weight in long_weights.items():
            final_weights[ticker] = weight * 0.5  # Initial 50% long
        for ticker, weight in short_weights.items():
            final_weights[ticker] = -weight * 0.5  # Initial 50% short
        
        return pd.Series(final_weights)
    
    def calculate_optimal_weights_with_positions(self, returns: pd.DataFrame,
                                                 tickers: Dict[str, Dict],
                                                 target_net_exposure: Optional[float] = None,
                                                 liquidity_scores: Dict[str, float] = None,
                                                 method: str = "risk_based") -> pd.Series:
        """Calculate optimal weights with proper constraint enforcement.
        
        Revised approach to handle net exposure correctly:
        1. Get raw optimal weights
        2. Apply position caps first (hard constraints)
        3. Adjust for net exposure within the capped constraints
        4. Normalize to gross = 1.0 while preserving net/gross ratio
        """
        # Step 1: Get raw optimal weights
        raw_weights = self.calculate_raw_optimal_weights(returns, tickers, method)
        if raw_weights.empty:
            return pd.Series()
        
        # Step 2: Normalize raw weights initially
        raw_weights = raw_weights / raw_weights.abs().sum()
        
        # Step 3: Apply caps and net exposure together
        final_weights = self.apply_caps_with_net_exposure(
            raw_weights, tickers, liquidity_scores, target_net_exposure
        )
        
        return final_weights
    
    def enforce_net_exposure(self, weights: pd.Series, tickers: Dict[str, Dict],
                            target_net_exposure: Optional[float]) -> pd.Series:
        """Enforce target net exposure on portfolio weights.
        
        Args:
            weights: Raw portfolio weights
            tickers: Dictionary with position info
            target_net_exposure: Target net exposure
            
        Returns:
            Weights adjusted for target net exposure
        """
        if weights.empty:
            return weights
        
        # Separate long and short weights
        long_weights = weights[weights > 0].copy()
        short_weights = weights[weights < 0].abs()
        
        # Calculate target allocations
        if target_net_exposure is not None:
            if target_net_exposure >= 0:
                long_allocation = (1 + target_net_exposure) / 2
                short_allocation = (1 - target_net_exposure) / 2
            else:
                long_allocation = (1 + target_net_exposure) / 2
                short_allocation = (1 - target_net_exposure) / 2
        else:
            # Natural exposure based on number of positions
            n_long = len(long_weights)
            n_short = len(short_weights)
            total = n_long + n_short
            if total > 0:
                long_allocation = n_long / total
                short_allocation = n_short / total
            else:
                long_allocation = 0.5
                short_allocation = 0.5
        
        # Scale each book to target allocation
        adjusted_weights = pd.Series(dtype=float)
        
        if not long_weights.empty:
            long_sum = long_weights.sum()
            if long_sum > 0:
                for ticker in long_weights.index:
                    adjusted_weights[ticker] = (long_weights[ticker] / long_sum) * long_allocation
        
        if not short_weights.empty:
            short_sum = short_weights.sum()
            if short_sum > 0:
                for ticker in short_weights.index:
                    adjusted_weights[ticker] = -(short_weights[ticker] / short_sum) * short_allocation
        
        return adjusted_weights
    
    def apply_position_caps_with_redistribution(self, weights: pd.Series, 
                                               tickers: Dict[str, Dict],
                                               liquidity_scores: Optional[Dict[str, float]],
                                               target_net_exposure: Optional[float],
                                               max_iterations: int = 10) -> pd.Series:
        """Apply position caps while maintaining net exposure as much as possible.
        
        New approach: Don't normalize to gross = 1.0, instead maintain net exposure
        and let leverage handle the scaling.
        """
        if weights.empty:
            return weights
        
        if liquidity_scores is None:
            liquidity_scores = {}
        
        weights = weights.copy()
        
        # Store initial net exposure to maintain
        initial_long = weights[weights > 0].sum()
        initial_short = weights[weights < 0].abs().sum()
        initial_net = initial_long - initial_short
        
        # Define position caps
        position_caps = {}
        for ticker in weights.index:
            position_type = 'long' if weights[ticker] > 0 else 'short'
            liquidity_score = liquidity_scores.get(ticker, 0.5)
            
            if position_type == 'long':
                position_caps[ticker] = 0.12  # 12% cap for longs
            else:  # short
                if liquidity_score >= 0.55:  # Mid/High liquidity (grades A, B, C)
                    position_caps[ticker] = 0.05  # 5% cap
                else:  # Med/Low liquidity (grades D, F)
                    position_caps[ticker] = 0.03  # 3% cap
        
        # Apply caps and track how much we need to redistribute
        long_excess = 0
        short_excess = 0
        
        # First pass: apply caps
        for ticker in weights.index:
            if abs(weights[ticker]) > position_caps[ticker]:
                if weights[ticker] > 0:
                    long_excess += weights[ticker] - position_caps[ticker]
                    weights[ticker] = position_caps[ticker]
                else:
                    short_excess += abs(weights[ticker]) - position_caps[ticker]
                    weights[ticker] = -position_caps[ticker]
        
        # Redistribute excess within each book, respecting caps
        for iteration in range(max_iterations):
            if long_excess < 0.001 and short_excess < 0.001:
                break
            
            # Redistribute long excess
            if long_excess > 0:
                long_mask = weights > 0
                available_longs = []
                for ticker in weights[long_mask].index:
                    room = position_caps[ticker] - weights[ticker]
                    if room > 0.001:
                        available_longs.append((ticker, room))
                
                if available_longs:
                    total_room = sum(room for _, room in available_longs)
                    distributed = 0
                    for ticker, room in available_longs:
                        share = min(room, long_excess * (room / total_room))
                        weights[ticker] += share
                        distributed += share
                    long_excess -= distributed
            
            # Redistribute short excess
            if short_excess > 0:
                short_mask = weights < 0
                available_shorts = []
                for ticker in weights[short_mask].index:
                    room = position_caps[ticker] - abs(weights[ticker])
                    if room > 0.001:
                        available_shorts.append((ticker, room))
                
                if available_shorts:
                    total_room = sum(room for _, room in available_shorts)
                    distributed = 0
                    for ticker, room in available_shorts:
                        share = min(room, short_excess * (room / total_room))
                        weights[ticker] -= share  # Negative for shorts
                        distributed += share
                    short_excess -= distributed
        
        # Calculate final exposures
        final_long = weights[weights > 0].sum()
        final_short = weights[weights < 0].abs().sum()
        final_net = final_long - final_short
        
        # If net exposure has drifted significantly, scale books to restore it
        if target_net_exposure is not None and abs(final_net - target_net_exposure) > 0.02:
            # Calculate what the long/short exposures should be for target net
            # We need: long - short = target_net
            # And we want to maintain relative sizes as much as possible
            
            # Use current gross as basis
            current_gross = final_long + final_short
            
            # Solve: long - short = target_net, long + short = current_gross
            # Therefore: long = (current_gross + target_net) / 2
            #           short = (current_gross - target_net) / 2
            target_long = (current_gross + target_net_exposure) / 2
            target_short = (current_gross - target_net_exposure) / 2
            
            # Scale each book
            if final_long > 0:
                long_scale = target_long / final_long
                # But don't scale up if it would violate caps
                if long_scale > 1:
                    long_scale = 1  # Don't scale up, only down
                for ticker in weights[weights > 0].index:
                    weights[ticker] *= long_scale
            
            if final_short > 0:
                short_scale = target_short / final_short
                # But don't scale up if it would violate caps
                if short_scale > 1:
                    short_scale = 1  # Don't scale up, only down
                for ticker in weights[weights < 0].index:
                    weights[ticker] *= short_scale
        
        return weights
    
    def apply_caps_with_net_exposure(self, weights: pd.Series,
                                    tickers: Dict[str, Dict],
                                    liquidity_scores: Optional[Dict[str, float]],
                                    target_net_exposure: Optional[float]) -> pd.Series:
        """Apply position caps while maintaining net exposure as closely as possible.
        
        This is the core method that handles the interaction between:
        1. Position caps (hard constraints)
        2. Net exposure targets (soft constraint, best effort)
        3. Gross exposure normalization
        """
        if weights.empty:
            return weights
        
        if liquidity_scores is None:
            liquidity_scores = {}
        
        weights = weights.copy()
        
        # Define position caps
        position_caps = {}
        for ticker in weights.index:
            position_type = 'long' if weights[ticker] > 0 else 'short'
            liquidity_score = liquidity_scores.get(ticker, 0.5)
            
            if position_type == 'long':
                position_caps[ticker] = 0.12  # 12% cap for longs
            else:
                if liquidity_score >= 0.55:  # Mid/High liquidity
                    position_caps[ticker] = 0.05  # 5% cap
                else:
                    position_caps[ticker] = 0.03  # 3% cap
        
        # Calculate maximum possible exposures given caps
        long_tickers = [t for t in weights.index if weights[t] > 0]
        short_tickers = [t for t in weights.index if weights[t] < 0]
        
        max_long_exposure = sum(position_caps[t] for t in long_tickers)
        max_short_exposure = sum(position_caps[t] for t in short_tickers)
        
        # Calculate achievable target allocations
        if target_net_exposure is not None:
            # Ideal allocations
            ideal_long_alloc = (1 + target_net_exposure) / 2
            ideal_short_alloc = (1 - target_net_exposure) / 2
            
            # Check if ideal allocations are achievable
            # We want the minimum of ideal allocation and what's possible
            target_long_alloc = min(ideal_long_alloc, max_long_exposure)
            target_short_alloc = min(ideal_short_alloc, max_short_exposure)
            
            # If we had to reduce one side, adjust the other to maintain ratio if possible
            if target_long_alloc < ideal_long_alloc:
                # Longs are constrained, adjust shorts proportionally
                if ideal_long_alloc > 0:
                    ratio = target_long_alloc / ideal_long_alloc
                    target_short_alloc = min(ideal_short_alloc * ratio, max_short_exposure)
            elif target_short_alloc < ideal_short_alloc:
                # Shorts are constrained, adjust longs proportionally
                if ideal_short_alloc > 0:
                    ratio = target_short_alloc / ideal_short_alloc
                    target_long_alloc = min(ideal_long_alloc * ratio, max_long_exposure)
            
            # Normalize to sum to 1
            total_alloc = target_long_alloc + target_short_alloc
            if total_alloc > 1:
                target_long_alloc = target_long_alloc / total_alloc
                target_short_alloc = target_short_alloc / total_alloc
        else:
            # Natural exposure based on current weights
            long_sum = weights[weights > 0].sum()
            short_sum = weights[weights < 0].abs().sum()
            total = long_sum + short_sum
            if total > 0:
                target_long_alloc = long_sum / total
                target_short_alloc = short_sum / total
            else:
                target_long_alloc = 0.5
                target_short_alloc = 0.5
        
        # Separate and scale long/short books to target allocations
        long_weights = weights[weights > 0].copy()
        short_weights = weights[weights < 0].abs()
        
        # Scale to target allocations
        if not long_weights.empty:
            long_sum = long_weights.sum()
            if long_sum > 0:
                long_weights = long_weights / long_sum * target_long_alloc
        
        if not short_weights.empty:
            short_sum = short_weights.sum()
            if short_sum > 0:
                short_weights = short_weights / short_sum * target_short_alloc
        
        # Apply caps with redistribution within each book
        # Long positions
        for _ in range(10):  # Max iterations
            capped_any = False
            for ticker in long_weights.index:
                if long_weights[ticker] > position_caps[ticker]:
                    excess = long_weights[ticker] - position_caps[ticker]
                    long_weights[ticker] = position_caps[ticker]
                    capped_any = True
                    
                    # Redistribute excess to uncapped longs
                    available_for_redistribution = []
                    for other_ticker in long_weights.index:
                        if other_ticker != ticker:
                            room = position_caps[other_ticker] - long_weights[other_ticker]
                            if room > 0.001:
                                available_for_redistribution.append((other_ticker, room))
                    
                    if available_for_redistribution:
                        total_room = sum(r for _, r in available_for_redistribution)
                        remaining_excess = excess
                        for other_ticker, room in available_for_redistribution:
                            share = min(room, remaining_excess * (room / total_room))
                            long_weights[other_ticker] += share
                            remaining_excess -= share
            
            if not capped_any:
                break
        
        # Short positions
        for _ in range(10):  # Max iterations
            capped_any = False
            for ticker in short_weights.index:
                if short_weights[ticker] > position_caps[ticker]:
                    excess = short_weights[ticker] - position_caps[ticker]
                    short_weights[ticker] = position_caps[ticker]
                    capped_any = True
                    
                    # Redistribute excess to uncapped shorts
                    available_for_redistribution = []
                    for other_ticker in short_weights.index:
                        if other_ticker != ticker:
                            room = position_caps[other_ticker] - short_weights[other_ticker]
                            if room > 0.001:
                                available_for_redistribution.append((other_ticker, room))
                    
                    if available_for_redistribution:
                        total_room = sum(r for _, r in available_for_redistribution)
                        remaining_excess = excess
                        for other_ticker, room in available_for_redistribution:
                            share = min(room, remaining_excess * (room / total_room))
                            short_weights[other_ticker] += share
                            remaining_excess -= share
            
            if not capped_any:
                break
        
        # Combine back with appropriate signs
        final_weights = pd.Series(dtype=float, index=weights.index)
        for ticker in long_weights.index:
            final_weights[ticker] = long_weights[ticker]
        for ticker in short_weights.index:
            final_weights[ticker] = -short_weights[ticker]
        
        # Check actual vs target exposure before normalization
        pre_norm_long = final_weights[final_weights > 0].sum()
        pre_norm_short = final_weights[final_weights < 0].abs().sum()
        pre_norm_net = pre_norm_long - pre_norm_short
        
        # Final normalization to ensure gross = 1.0
        gross = final_weights.abs().sum()
        if gross > 0:
            final_weights = final_weights / gross
        
        # Debug: Check if net exposure is maintained after normalization
        final_long = final_weights[final_weights > 0].sum()
        final_short = final_weights[final_weights < 0].abs().sum()
        final_net = final_long - final_short
        
        if target_net_exposure is not None:
            print(f"DEBUG: Target net exposure: {target_net_exposure:.2%}")
            print(f"DEBUG: Pre-norm net: {pre_norm_net:.2%}, gross: {gross:.2%}")
            print(f"DEBUG: Final net: {final_net:.2%}, long: {final_long:.2%}, short: {final_short:.2%}")
            
            # If we're way off target, try a different approach
            if abs(final_net - target_net_exposure) > 0.1:
                print(f"WARNING: Net exposure {final_net:.2%} far from target {target_net_exposure:.2%}")
        
        return final_weights
    
    def scale_to_target_volatility_with_caps(self, weights: pd.Series, returns: pd.DataFrame,
                                            target_annual_vol: float,
                                            tickers: Dict[str, Dict],
                                            liquidity_scores: Optional[Dict[str, float]] = None) -> pd.Series:
        """Scale portfolio to target volatility while respecting position caps.
        
        This method scales the portfolio to achieve target volatility but ensures
        position caps are never violated.
        
        Args:
            weights: Portfolio weights with caps already applied
            returns: DataFrame of returns
            target_annual_vol: Target annual volatility
            tickers: Dictionary with position info
            liquidity_scores: Liquidity scores per ticker
            
        Returns:
            Scaled weights that respect caps and achieve target vol
        """
        if weights.empty or returns.empty:
            return weights
        
        # Calculate current portfolio volatility
        portfolio_returns = (returns * weights).sum(axis=1)
        current_vol = self.risk_calc.annualized_volatility(portfolio_returns)
        
        # Calculate ideal scaling factor
        if current_vol > 0 and target_annual_vol > 0:
            ideal_scale = target_annual_vol / current_vol
            
            # If scaling down, we can apply directly
            if ideal_scale <= 1.0:
                return weights * ideal_scale
            
            # If scaling up, need to respect caps
            if liquidity_scores is None:
                liquidity_scores = {}
            
            # Define position caps
            position_caps = {}
            for ticker in weights.index:
                position_type = 'long' if weights[ticker] > 0 else 'short'
                liquidity_score = liquidity_scores.get(ticker, 0.5)
                
                if position_type == 'long':
                    position_caps[ticker] = 0.12  # 12% cap
                else:
                    if liquidity_score >= 0.55:  # Mid/High liquidity (grades A, B, C)
                        position_caps[ticker] = 0.05  # 5% cap
                    else:  # Med/Low liquidity (grades D, F)
                        position_caps[ticker] = 0.03  # 3% cap
            
            # Scale up to the maximum allowed by caps
            scaled_weights = weights.copy()
            max_scale = 1.0
            
            for ticker in weights.index:
                if abs(weights[ticker]) > 0:
                    # Maximum scale for this position before hitting cap
                    ticker_max_scale = position_caps[ticker] / abs(weights[ticker])
                    max_scale = max(max_scale, min(ideal_scale, ticker_max_scale))
            
            # Apply the constrained scale
            scaled_weights = weights * min(ideal_scale, max_scale)
            
            # Ensure no position exceeds its cap
            for ticker in scaled_weights.index:
                if abs(scaled_weights[ticker]) > position_caps[ticker]:
                    scaled_weights[ticker] = position_caps[ticker] * (1 if scaled_weights[ticker] > 0 else -1)
            
            return scaled_weights
        
        return weights
    
    def scale_to_target_volatility(self, weights: pd.Series, returns: pd.DataFrame,
                                  target_annual_vol: float) -> pd.Series:
        """Legacy method - now just calls the new capped version.
        
        DEPRECATED: Use scale_to_target_volatility_with_caps instead
        """
        # For backward compatibility, but should not be used in new flow
        if weights.empty or returns.empty:
            return weights
        
        portfolio_returns = (returns * weights).sum(axis=1)
        current_vol = self.risk_calc.annualized_volatility(portfolio_returns)
        
        if current_vol > 0 and target_annual_vol > 0:
            vol_scale = target_annual_vol / current_vol
            return weights * vol_scale
        
        return weights
    
    def validate_portfolio_constraints(self, weights: pd.Series,
                                      tickers: Dict[str, Dict],
                                      liquidity_scores: Optional[Dict[str, float]],
                                      target_net_exposure: Optional[float]) -> list:
        """Validate that all portfolio constraints are satisfied.
        
        Args:
            weights: Final portfolio weights
            tickers: Dictionary with position info
            liquidity_scores: Liquidity scores per ticker
            target_net_exposure: Target net exposure
            
        Returns:
            List of validation errors (empty if all constraints satisfied)
        """
        errors = []
        
        if weights.empty:
            return ["Empty weights"]
        
        if liquidity_scores is None:
            liquidity_scores = {}
        
        # Check position caps
        for ticker in weights.index:
            weight = abs(weights[ticker])
            position_type = 'long' if weights[ticker] > 0 else 'short'
            liquidity_score = liquidity_scores.get(ticker, 0.5)
            
            if position_type == 'long':
                max_cap = 0.12
                if weight > max_cap + 0.001:  # Small tolerance for rounding
                    errors.append(f"{ticker}: Long position {weight:.4f} exceeds cap {max_cap}")
            else:
                if liquidity_score >= 0.55:  # Mid/High liquidity (grades A, B, C)
                    max_cap = 0.05
                else:  # Med/Low liquidity (grades D, F)
                    max_cap = 0.03
                if weight > max_cap + 0.001:
                    errors.append(f"{ticker}: Short position {weight:.4f} exceeds cap {max_cap}")
        
        # Check net exposure
        if target_net_exposure is not None:
            long_exposure = weights[weights > 0].sum()
            short_exposure = weights[weights < 0].abs().sum()
            actual_net = long_exposure - short_exposure
            
            # Allow 5% tolerance for net exposure
            if abs(actual_net - target_net_exposure) > 0.05:
                errors.append(f"Net exposure {actual_net:.2%} deviates from target {target_net_exposure:.2%}")
        
        # Check gross exposure (should be close to 1.0)
        gross = weights.abs().sum()
        if abs(gross - 1.0) > 0.01:
            errors.append(f"Gross exposure {gross:.4f} not normalized to 1.0")
        
        return errors
    
    def calculate_returns(self, price_data: Dict[str, pd.Series], 
                         use_cache: bool = True) -> pd.DataFrame:
        """Calculate daily returns from price data using ReturnsCalculator.
        
        Args:
            price_data: Dictionary of price series keyed by ticker
            use_cache: Whether to use cached returns if available
        
        Returns:
            DataFrame with returns for each ticker as columns
        """
        # Check cache
        if use_cache and self._returns_cache is not None:
            return self._returns_cache
        
        if not price_data:
            return pd.DataFrame()
        
        # Calculate returns for each ticker using ReturnsCalculator
        returns_dict = {}
        for ticker, prices in price_data.items():
            if prices is not None and not prices.empty:
                # Use ReturnsCalculator.daily_price_returns()
                daily_returns = self.returns_calc.daily_price_returns(prices)
                returns_dict[ticker] = daily_returns
        
        # Assemble into DataFrame
        if returns_dict:
            returns_df = pd.DataFrame(returns_dict)
            # Cache the results
            self._returns_cache = returns_df
            self._price_cache = price_data
            return returns_df
        
        return pd.DataFrame()


if __name__ == "__main__":
    """Test the portfolio builder with a fake long/short equity portfolio."""
    
    # Create a consumer staples long/short equity portfolio
    test_portfolio = {
        # Long positions
        "ACI": {"allocation": 0.02046, "position": "long"},
        "ADM": {"allocation": 0.05139, "position": "long"},
        "CCEP": {"allocation": 0.06676, "position": "long"},
        "CL": {"allocation": 0.03158, "position": "long"},
        "GIS": {"allocation": 0.04037, "position": "long"},
        "INGR": {"allocation": 0.095, "position": "long"},
        "IPAR": {"allocation": 0.05, "position": "long"},
        "KDP": {"allocation": 0.0696, "position": "long"},
        "KMB": {"allocation": 0.10359, "position": "long"},
        "KO": {"allocation": 0.08445, "position": "long"},
        "KVUE": {"allocation": 0.05708, "position": "long"},
        "LW": {"allocation": 0.04633, "position": "long"},
        "MO": {"allocation": 0.10028, "position": "long"},
        "PPC": {"allocation": 0.07188, "position": "long"},
        "REYN": {"allocation": 0.08937, "position": "long"},
        "RLX": {"allocation": 0.04158, "position": "long"},
        "SAM": {"allocation": 0.02808, "position": "long"},
        "BJ": {"allocation": 0.02779, "position": "long"},
        
        # Short positions
        "CELH": {"allocation": 0.05, "position": "short"},
        "CLX": {"allocation": 0.08, "position": "short"},
        "COTY": {"allocation": 0.04, "position": "short"},
        "EL": {"allocation": 0.048, "position": "short"},
        "ELF": {"allocation": 0.045, "position": "short"},
        "FRPT": {"allocation": 0.044, "position": "short"},
        "HSY": {"allocation": 0.08, "position": "short"},
        "PFGC": {"allocation": 0.045, "position": "short"},
        "SFM": {"allocation": 0.069, "position": "short"},
        "STZ": {"allocation": 0.08, "position": "short"},
        "USFD": {"allocation": 0.045, "position": "short"},
        "UTZ": {"allocation": 0.08, "position": "short"},
        "VITL": {"allocation": 0.065, "position": "short"},
        "WDFC": {"allocation": 0.08, "position": "short"}
    }
    
    # Test parameters
    target_annual_vol = 0.15       # 15% annual volatility target
    portfolio_value = 1_000_000    # $1M portfolio
    leverage = 1.5                  # 1.5x leverage (150% gross exposure)
    target_net_exposure = 0.35      # 35% net long
    
    print("=" * 80)
    print("PORTFOLIO BUILDER TEST")
    print("=" * 80)
    print(f"\nTest Portfolio: {len(test_portfolio)} positions")
    print(f"Long positions: {sum(1 for t in test_portfolio.values() if t['position'] == 'long')}")
    print(f"Short positions: {sum(1 for t in test_portfolio.values() if t['position'] == 'short')}")
    print(f"\nParameters:")
    print(f"  Target Annual Volatility: {target_annual_vol:.1%}")
    print(f"  Portfolio Value: ${portfolio_value:,.0f}")
    print(f"  Leverage: {leverage:.1f}x")
    print(f"  Target Net Exposure: {target_net_exposure:.1%}")
    
    # Build the portfolio
    print("\n" + "=" * 80)
    print("Building portfolio with liquidity-based position caps...")
    print("=" * 80)
    
    builder = CorrelationPortfolioBuilder()
    result = builder.build_portfolio(
        tickers=test_portfolio,
        target_annual_vol=target_annual_vol,
        portfolio_value=portfolio_value,
        leverage=leverage,
        target_net_exposure=target_net_exposure,
        lookback_days=252
    )
    
    # Display results
    if "error" in result:
        print(f"\nERROR: {result['error']}")
    else:
        print(f"\nStatus: {result['status']}")
        print(f"\nExposures:")
        print(f"  Gross Exposure: {result['gross_exposure']:.1%}")
        print(f"  Net Exposure: {result['actual_net_exposure']:.1%}")
        print(f"  Long Exposure: {result['long_exposure']:.1%}")
        print(f"  Short Exposure: {result['short_exposure']:.1%}")
        
        print(f"\nRisk Metrics:")
        risk = result.get('risk_metrics', {})
        print(f"  Annual Volatility: {risk.get('annual_volatility', 0):.2%}")
        print(f"  Sharpe Ratio: {risk.get('sharpe_ratio', 0):.2f}")
        print(f"  Max Drawdown: {risk.get('max_drawdown', 0):.2%}")
        print(f"  VaR 99%: {risk.get('var_99', 0):.2%}")
        
        print(f"\nFinal Portfolio Allocations:")
        print("-" * 50)
        final_portfolio = result.get('final_portfolio', {})
        
        # Separate and sort by position type
        longs = [(t, p) for t, p in final_portfolio.items() if p['position'] == 'long']
        shorts = [(t, p) for t, p in final_portfolio.items() if p['position'] == 'short']
        
        longs.sort(key=lambda x: x[1]['allocation'], reverse=True)
        shorts.sort(key=lambda x: x[1]['allocation'], reverse=True)
        
        print("\nLONG POSITIONS:")
        for ticker, pos in longs:
            allocation_pct = pos['allocation'] * 100
            # Check if capped at 12%
            capped = " [CAPPED]" if abs(allocation_pct - 12.0) < 0.01 else ""
            print(f"  {ticker:6s}: {allocation_pct:5.2f}%{capped}")
        
        print("\nSHORT POSITIONS:")
        for ticker, pos in shorts:
            allocation_pct = pos['allocation'] * 100
            # Check if capped at 3% or 5%
            if abs(allocation_pct - 5.0) < 0.01:
                capped = " [CAPPED @ 5% - Mid/High Liquid]"
            elif abs(allocation_pct - 3.0) < 0.01:
                capped = " [CAPPED @ 3% - Med/Low Liquid]"
            else:
                capped = ""
            print(f"  {ticker:6s}: {allocation_pct:5.2f}%{capped}")
        
        print("\n" + "=" * 80)
        print("Portfolio build completed successfully!")
        print("=" * 80)