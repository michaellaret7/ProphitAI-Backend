"""Main orchestrator for correlation-aware portfolio building."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional
import pandas as pd

from backend.src.calculations_v2.core import DataService
from backend.src.calculations_v2.returns.calculator import ReturnsCalculator
from backend.src.calculations_v2.risk.calculator import RiskCalculator
from backend.src.calculations_v2.performance.calculator import PerformanceCalculator
from backend.src.calculations_v2.portfolio.correlation import CorrelationAnalysis
from backend.src.calculations_v2.portfolio.build.optimizer import PortfolioOptimizer
from backend.src.calculations_v2.core.config import DEFAULT_CONFIDENCE

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
        self.perf_calc = PerformanceCalculator()
        self.optimizer = PortfolioOptimizer()
        self.correlation = CorrelationAnalysis()
        
        # Cache for returns data
        self._returns_cache: Optional[pd.DataFrame] = None
        self._price_cache: Optional[Dict[str, pd.Series]] = None
    
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
            
            # Step 3: Calculate returns
            returns_df = self.calculate_returns(price_data)
            if returns_df.empty:
                return {"error": "Failed to calculate returns"}
            
            # Step 4: Calculate optimal weights with long/short positions
            weights = self.calculate_optimal_weights_with_positions(
                returns_df, tickers, target_net_exposure, max_position_weight
            )
            
            # Step 4.5: Scale weights to achieve target volatility
            weights = self.scale_to_target_volatility(
                weights, returns_df, target_annual_vol
            )
            
            # Step 5: Generate risk metrics
            risk_metrics = self.generate_risk_metrics(weights, returns_df)
            
            # Step 6: Calculate position sizes with leverage
            position_sizes = self.optimizer.calculate_position_sizes(
                weights, portfolio_value, leverage
            )
            
            # Step 7: Calculate exposure metrics
            long_exposure = sum(w for t, w in weights.items() 
                              if tickers[t]['position'] == 'long')
            short_exposure = sum(abs(w) for t, w in weights.items() 
                               if tickers[t]['position'] == 'short')
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
    
    def calculate_optimal_weights_with_positions(self, returns: pd.DataFrame,
                                                 tickers: Dict[str, Dict],
                                                 target_net_exposure: Optional[float] = None,
                                                 max_position_weight: float = 0.10,
                                                 method: str = "risk_based") -> pd.Series:
        """Calculate optimal weights considering long/short positions and net exposure.
        
        Args:
            returns: DataFrame of returns
            tickers: Dictionary with ticker info including position and allocation
            target_net_exposure: Target net exposure (None for natural)
            max_position_weight: Maximum weight per position
            method: Optimization method
            
        Returns:
            Series of signed weights (negative for shorts)
        """
        if returns.empty:
            return pd.Series()
        
        # Separate long and short positions
        long_tickers = [t for t in tickers if tickers[t]['position'] == 'long']
        short_tickers = [t for t in tickers if tickers[t]['position'] == 'short']
        
        # Get allocations (as decimal allocations, e.g., 0.1 = 10%)
        # If no allocation specified, use equal weight placeholder
        base_allocations = {}
        for ticker in tickers:
            if ticker in returns.columns:
                # Allocation is already a decimal (0.1 = 10% allocation)
                base_allocations[ticker] = tickers[ticker].get('allocation', 0.1)
        
        # Get covariance matrix
        cov = self.correlation.covariance_matrix(returns, annualize=True)
        
        # Separate allocations by long/short
        long_allocations = {t: base_allocations[t] for t in long_tickers if t in base_allocations}
        short_allocations = {t: base_allocations[t] for t in short_tickers if t in base_allocations}
        
        # Normalize convictions within each group to sum to 1
        long_weights = {}
        short_weights = {}
        
        if long_tickers and long_allocations:
            # Normalize long allocations
            long_alloc_sum = sum(long_allocations.values())
            if long_alloc_sum > 0:
                long_norm_alloc = {k: v/long_alloc_sum for k, v in long_allocations.items()}
            else:
                long_norm_alloc = {k: 1.0/len(long_allocations) for k in long_allocations}
            
            # Apply optimization with allocation-based starting weights
            long_returns = returns[long_tickers]
            long_cov = cov.loc[long_tickers, long_tickers]
            
            if method == "risk_parity":
                long_opt = self.optimizer.optimize_weights_risk_parity(long_cov)
            elif method == "max_sharpe":
                expected_returns = long_returns.mean() * 252
                long_opt = self.optimizer.optimize_weights_max_sharpe(expected_returns, long_cov)
            elif method == "min_variance":
                long_opt = self.optimizer.optimize_weights_min_variance(long_cov)
            else:  # Default to risk_based
                # Create base allocations series for risk-based optimization
                alloc_series = pd.Series(long_norm_alloc)
                long_opt = self.optimizer.optimize_weights_risk_based(long_cov, alloc_series)
            
            # Blend optimization with allocation weights (50/50 blend)
            for ticker in long_tickers:
                opt_weight = long_opt.get(ticker, 0)
                alloc_weight = long_norm_alloc.get(ticker, 0)
                # Blend optimization result with allocation
                long_weights[ticker] = 0.5 * opt_weight + 0.5 * alloc_weight
        
        if short_tickers and short_allocations:
            # Normalize short allocations
            short_alloc_sum = sum(short_allocations.values())
            if short_alloc_sum > 0:
                short_norm_alloc = {k: v/short_alloc_sum for k, v in short_allocations.items()}
            else:
                short_norm_alloc = {k: 1.0/len(short_allocations) for k in short_allocations}
            
            # Apply optimization with allocation-based starting weights
            short_returns = returns[short_tickers]
            short_cov = cov.loc[short_tickers, short_tickers]
            
            if method == "risk_parity":
                short_opt = self.optimizer.optimize_weights_risk_parity(short_cov)
            elif method == "max_sharpe":
                expected_returns = short_returns.mean() * 252
                short_opt = self.optimizer.optimize_weights_max_sharpe(expected_returns, short_cov)
            elif method == "min_variance":
                short_opt = self.optimizer.optimize_weights_min_variance(short_cov)
            else:  # Default to risk_based
                # Create base allocations series for risk-based optimization
                alloc_series = pd.Series(short_norm_alloc)
                short_opt = self.optimizer.optimize_weights_risk_based(short_cov, alloc_series)
            
            # Blend optimization with allocation weights (50/50 blend)
            for ticker in short_tickers:
                opt_weight = short_opt.get(ticker, 0)
                alloc_weight = short_norm_alloc.get(ticker, 0)
                # Blend optimization result with allocation
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
        
        # Adjust for target net exposure
        if target_net_exposure is not None:
            # Calculate required long/short allocations
            if target_net_exposure >= 0:
                # Net long
                long_allocation = (1 + target_net_exposure) / 2
                short_allocation = (1 - target_net_exposure) / 2
            else:
                # Net short
                long_allocation = (1 + target_net_exposure) / 2
                short_allocation = (1 - target_net_exposure) / 2
        else:
            # Natural exposure based on number of positions
            n_long = len(long_tickers)
            n_short = len(short_tickers)
            total = n_long + n_short
            if total > 0:
                long_allocation = n_long / total
                short_allocation = n_short / total
            else:
                long_allocation = 0.5
                short_allocation = 0.5
        
        # Combine with appropriate signs
        final_weights = {}
        for ticker, weight in long_weights.items():
            final_weights[ticker] = weight * long_allocation
        for ticker, weight in short_weights.items():
            final_weights[ticker] = -weight * short_allocation  # Negative for shorts
        
        # Apply position constraints
        weights_series = pd.Series(final_weights)
        for ticker in weights_series.index:
            if abs(weights_series[ticker]) > max_position_weight:
                weights_series[ticker] = max_position_weight * (1 if weights_series[ticker] > 0 else -1)
        
        # Renormalize to maintain gross exposure = 1
        gross = weights_series.abs().sum()
        if gross > 0:
            weights_series = weights_series / gross
        
        return weights_series
    
    def scale_to_target_volatility(self, weights: pd.Series, returns: pd.DataFrame,
                                  target_annual_vol: float) -> pd.Series:
        """Scale portfolio weights to achieve target annual volatility.
        
        This is a critical step from the original implementation that ensures
        the portfolio achieves the desired risk level.
        
        Args:
            weights: Portfolio weights (can include negative for shorts)
            returns: DataFrame of returns
            target_annual_vol: Target annual volatility (e.g., 0.10 for 10%)
            
        Returns:
            Scaled weights to achieve target volatility
        """
        if weights.empty or returns.empty:
            return weights
        
        # Calculate current portfolio volatility
        portfolio_returns = (returns * weights).sum(axis=1)
        current_vol = self.risk_calc.annualized_volatility(portfolio_returns)
        
        # Scale weights to achieve target volatility
        if current_vol > 0 and target_annual_vol > 0:
            vol_scale = target_annual_vol / current_vol
            scaled_weights = weights * vol_scale
            
            print(f"\nVolatility Scaling:")
            print(f"  Current volatility: {current_vol:.2%}")
            print(f"  Target volatility:  {target_annual_vol:.2%}")
            print(f"  Scaling factor:     {vol_scale:.3f}")
            
            return scaled_weights
        
        return weights
    
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