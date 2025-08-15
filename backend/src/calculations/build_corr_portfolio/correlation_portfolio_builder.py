"""Main orchestrator for correlation-aware portfolio building."""

import pandas as pd
from typing import Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')

# Import all the modular components
from .data_fetcher import DataFetcher
from .returns_calculator import ReturnsCalculator
from .correlation_analyzer import CorrelationAnalyzer
from .portfolio_optimizer import PortfolioOptimizer
from .risk_metrics import RiskMetrics
from .performance_metrics import PerformanceMetrics
from .portfolio_visualizer import PortfolioVisualizer
from .portfolio_reporter import PortfolioReporter

class CorrelationAwarePortfolioBuilder:
    """
    Portfolio builder that incorporates full risk analysis to optimize portfolio weights.
    Uses covariance matrix and VaR calculations to size positions based on risk contributions.
    Orchestrates multiple specialized modules for data fetching, analysis, and reporting.
    """
    
    def __init__(self, tickers: Dict[str, Dict], target_annual_vol: float, portfolio_value: float, 
                 leverage: float = 1.0, target_net_exposure: Optional[float] = None, 
                 lookback_days: int = 252, max_position_weight: float = 0.10):
        """
        Initialize the portfolio builder.
        
        Parameters:
        -----------
        tickers : Dict[str, Dict]
            Dictionary with ticker symbols as keys and dict containing 'conviction' and 'position' (long/short)
        target_annual_vol : float
            Target annual volatility for the portfolio (e.g., 0.10 for 10%)
        portfolio_value : float
            Total portfolio value in dollars (base capital before leverage)
        leverage : float
            Leverage multiplier (e.g., 1.5 for 150% gross exposure, default 1.0 for no leverage)
        target_net_exposure : Optional[float]
            Target net exposure as fraction of base capital (e.g., 0.35 for 35%, default None for natural exposure)
        lookback_days : int
            Number of days to look back for historical data (default 252 trading days)
        max_position_weight : float
            Maximum weight for any single position (e.g., 0.10 for 10%, default 0.10)
        """
        self.tickers = tickers
        self.target_annual_vol = target_annual_vol
        self.portfolio_value = portfolio_value
        self.leverage = leverage
        self.target_net_exposure = target_net_exposure
        self.lookback_days = lookback_days
        self.max_position_weight = max_position_weight
        self.trading_days = 252
        
        # Initialize helper modules
        self.data_fetcher = DataFetcher(lookback_days)
        self.returns_calculator = ReturnsCalculator()
        self.correlation_analyzer = CorrelationAnalyzer(self.trading_days)
        self.portfolio_optimizer = PortfolioOptimizer(
            leverage=leverage,
            target_net_exposure=target_net_exposure,
            max_position_weight=max_position_weight,
            target_annual_vol=target_annual_vol
        )
        self.risk_metrics = RiskMetrics(portfolio_value, leverage, self.trading_days)
        self.performance_metrics = PerformanceMetrics(portfolio_value, leverage, self.trading_days)
        self.visualizer = PortfolioVisualizer()
        self.reporter = PortfolioReporter(portfolio_value, leverage, max_position_weight)
        
        # Data storage references
        self.price_data = {}
        self.returns_data = pd.DataFrame()
        self.correlation_matrix = None
        self.covariance_matrix = None
        self.allocation_df = None
        
    def fetch_all_price_data(self) -> None:
        """Fetch historical price data for all tickers in parallel."""
        self.price_data = self.data_fetcher.fetch_all_price_data(self.tickers)
    
    def calculate_returns(self) -> pd.DataFrame:
        """Calculate daily returns for all assets and combine into a DataFrame."""
        self.returns_data = self.returns_calculator.calculate_returns(self.price_data, self.tickers)
        return self.returns_data
    
    def calculate_correlation_matrix(self) -> pd.DataFrame:
        """Calculate the correlation matrix of asset returns."""
        if self.returns_data.empty:
            self.calculate_returns()
        
        self.correlation_matrix = self.correlation_analyzer.calculate_correlation_matrix(self.returns_data)
        return self.correlation_matrix
    
    def calculate_covariance_matrix(self) -> pd.DataFrame:
        """Calculate the covariance matrix of asset returns."""
        if self.returns_data.empty:
            self.calculate_returns()
        
        self.covariance_matrix = self.correlation_analyzer.calculate_covariance_matrix(self.returns_data)
        return self.covariance_matrix
    

    def risk_based_portfolio(self, base_weights: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """
        Adjust portfolio weights based on risk contributions using full covariance matrix.
        Each position is sized inversely to its contribution to portfolio risk.
        """
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        # Get optimized weights from optimizer
        weights = self.portfolio_optimizer.risk_based_portfolio(
            self.tickers, self.covariance_matrix, base_weights
        )
        
        # Apply position signs
        signed_weights = self.portfolio_optimizer.apply_position_signs(weights, self.tickers)
        
        # Calculate current portfolio volatility for scaling
        current_metrics = self.risk_metrics.calculate_portfolio_metrics(
            signed_weights, self.covariance_matrix, self.returns_data
        )
        current_vol = current_metrics['annual_volatility']
        
        # Scale weights to achieve target volatility
        if current_vol > 0 and self.target_annual_vol > 0:
            vol_scale = self.target_annual_vol / current_vol
            scaled_weights = {k: v * vol_scale for k, v in signed_weights.items()}
            
            print(f"\nVolatility Scaling:")
            print(f"  Current volatility: {current_vol:.2%}")
            print(f"  Target volatility:  {self.target_annual_vol:.2%}")
            print(f"  Scaling factor:     {vol_scale:.3f}")
            
            # Apply position weight cap after volatility scaling
            capped_weights = self.portfolio_optimizer.apply_position_weight_cap_signed(scaled_weights)
            
            return capped_weights
        
        # Apply cap even if no volatility scaling
        capped_weights = self.portfolio_optimizer.apply_position_weight_cap_signed(signed_weights)
        return capped_weights
    

    
    def calculate_risk_contributions(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate each asset's contribution to portfolio risk."""
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        return self.risk_metrics.calculate_risk_contributions(weights, self.covariance_matrix)
    
    def calculate_portfolio_var(self, weights: Dict[str, float], confidence_levels = [0.95, 0.99]) -> Dict:
        """Calculate portfolio VaR at different confidence levels."""
        return self.risk_metrics.calculate_portfolio_var(weights, self.returns_data, confidence_levels)
    
    def calculate_portfolio_metrics(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Calculate key portfolio metrics given weights."""
        if self.covariance_matrix is None:
            self.calculate_covariance_matrix()
        
        return self.risk_metrics.calculate_portfolio_metrics(
            weights, self.covariance_matrix, self.returns_data
        )
    
    def visualize_portfolio_returns(self, weights: Dict[str, float], save_plots: bool = True) -> None:
        """Visualize portfolio and individual asset returns."""
        self.visualizer.visualize_portfolio_returns(
            weights, self.returns_data, self.correlation_matrix, save_plots
        )
    
    def calculate_detailed_performance_metrics(self, weights: Dict[str, float]) -> Dict:
        """Calculate detailed performance metrics over multiple time periods."""
        return self.performance_metrics.calculate_detailed_performance_metrics(
            weights, self.returns_data
        )
    
    def display_performance_summary(self, weights: Dict[str, float]) -> None:
        """Display a comprehensive performance summary."""
        metrics = self.calculate_detailed_performance_metrics(weights)
        self.reporter.display_performance_summary(metrics)
    
    def build_portfolio(self) -> Tuple[Dict[str, Dict], pd.DataFrame]:
        """
        Build portfolio using risk-based strategy with target volatility scaling.
        
        Returns:
        --------
        Tuple of (portfolio_positions dict, allocation DataFrame)
        """
        # Fetch data and calculate correlations
        self.fetch_all_price_data()
        self.calculate_returns()
        self.calculate_correlation_matrix()
        self.calculate_covariance_matrix()
        
        # Get weights using risk-based strategy
        print(f"\nBuilding portfolio using risk-based strategy (covariance & VaR aware)...")
        weights = self.risk_based_portfolio()
        
        # Calculate risk contributions
        risk_contributions = self.calculate_risk_contributions(weights)
        
        # Calculate portfolio metrics
        metrics = self.calculate_portfolio_metrics(weights)
        
        # Calculate VaR
        var_metrics = self.calculate_portfolio_var(weights)
        
        # Display portfolio summary and get allocation DataFrame
        self.allocation_df = self.reporter.display_portfolio_summary(
            weights, self.tickers, risk_contributions, metrics, var_metrics, self.price_data
        )
        
        # Create portfolio positions dict for backward compatibility
        portfolio_positions = {}
        for _, row in self.allocation_df.iterrows():
            ticker = row['ticker']
            portfolio_positions[ticker] = {
                'position': row['position'],
                'weight': row['weight'],
                'position_size': row['position_size'],
                'volatility': row['volatility']
            }
        
        # Visualize portfolio returns
        # self.visualize_portfolio_returns(weights)
        
        # Display performance summary
        self.display_performance_summary(weights)
        
        return portfolio_positions, self.allocation_df 

if __name__ == "__main__":
    # Consumer Staples Portfolio
    # tickers1 = {
    #     # Long positions
    #     "CASY": {"conviction": 0.10, "position": "long"},
    #     "CELH": {"conviction": 0.10, "position": "long"},
    #     "ODC": {"conviction": 0.05, "position": "long"},
    #     "ODD": {"conviction": 0.05, "position": "long"},
    #     "PM": {"conviction": 0.05, "position": "long"},
    #     "VITL": {"conviction": 0.05, "position": "long"},
    #     "WMT": {"conviction": 0.05, "position": "long"},
    #     "BJ": {"conviction": 0.05, "position": "long"},
    #     "SFM": {"conviction": 0.05, "position": "long"},
    #     "COCO": {"conviction": 0.05, "position": "long"},
    #     "MNST": {"conviction": 0.05, "position": "long"},
    #     "CL": {"conviction": 0.05, "position": "long"},
    #     "IPAR": {"conviction": 0.05, "position": "long"},
    #     "TPB": {"conviction": 0.05, "position": "long"},
    #     "DOLE": {"conviction": 0.05, "position": "long"},
    #     "PPC": {"conviction": 0.05, "position": "long"},
    #     "INGR": {"conviction": 0.05, "position": "long"},
    #     # Short positions
    #     "WBA": {"conviction": 0.05, "position": "short"},
    #     "ANDE": {"conviction": 0.05, "position": "short"},
    #     "TGT": {"conviction": 0.02, "position": "short"},
    #     "STZ": {"conviction": 0.05, "position": "short"},
    #     "PEP": {"conviction": 0.05, "position": "short"},
    #     "SAM": {"conviction": 0.05, "position": "short"},
    #     "MGPI": {"conviction": 0.05, "position": "short"},
    #     "ENR": {"conviction": 0.05, "position": "short"},
    #     "SPB": {"conviction": 0.05, "position": "short"},
    #     "COTY": {"conviction": 0.05, "position": "short"},
    #     "KVUE": {"conviction": 0.05, "position": "short"},
    #     "KLG": {"conviction": 0.05, "position": "short"},
    #     "JJSF": {"conviction": 0.05, "position": "short"},
    #     "SEB": {"conviction": 0.05, "position": "short"},
    # }

    tickers2 = {
	# Long positions
        "CASY": {"conviction": 0.08, "position": "long"},
        "CELH": {"conviction": 0.07, "position": "long"},
        "ODC": {"conviction": 0.06, "position": "long"},
        "ODD": {"conviction": 0.05, "position": "long"},
        "PM": {"conviction": 0.07, "position": "long"},
        "VITL": {"conviction": 0.07, "position": "long"},
        "WMT": {"conviction": 0.05, "position": "long"},
        "BJ": {"conviction": 0.05, "position": "long"},
        "SFM": {"conviction": 0.06, "position": "long"},
        "COCO": {"conviction": 0.04, "position": "long"},
        "MNST": {"conviction": 0.04, "position": "long"},
        "CL": {"conviction": 0.04, "position": "long"},
        "TPB": {"conviction": 0.04, "position": "long"},
        "DOLE": {"conviction": 0.03, "position": "long"},
        "PPC": {"conviction": 0.03, "position": "long"},
        "INGR": {"conviction": 0.03, "position": "long"},
        "FIZZ": {"conviction": 0.02, "position": "long"},

        # Short positions
        "WBA": {"conviction": 0.05, "position": "short"},
        "ANDE": {"conviction": 0.05, "position": "short"},
        "TGT": {"conviction": 0.03, "position": "short"},
        "STZ": {"conviction": 0.05, "position": "short"},
        "PEP": {"conviction": 0.05, "position": "short"},
        "SAM": {"conviction": 0.04, "position": "short"},
        "MGPI": {"conviction": 0.03, "position": "short"},
        "ENR": {"conviction": 0.04, "position": "short"},
        "SPB": {"conviction": 0.04, "position": "short"},
        "COTY": {"conviction": 0.04, "position": "short"},
        "KVUE": {"conviction": 0.03, "position": "short"},
        "KLG": {"conviction": 0.03, "position": "short"},
        "JJSF": {"conviction": 0.03, "position": "short"},
        "SEB": {"conviction": 0.02, "position": "short"},
        "WMK": {"conviction": 0.02, "position": "short"},
        "PRMB": {"conviction": 0.02, "position": "short"},
        "REYN": {"conviction": 0.02, "position": "short"},
    }

    tickers3 = {
        "CASY": {"position": "long", "conviction": 0.1},
        "TPB": {"position": "long", "conviction": 0.05},
        "WMT": {"position": "long", "conviction": 0.05},
        "BJ": {"position": "long", "conviction": 0.05},
        "VITL": {"position": "long", "conviction": 0.1},
        "ODC": {"position": "long", "conviction": 0.1},
        "DOLE": {"position": "long", "conviction": 0.05},
        "PPC": {"position": "long", "conviction": 0.05},
        "INGR": {"position": "long", "conviction": 0.05},
        "CL": {"position": "long", "conviction": 0.05},
        "MNST": {"position": "long", "conviction": 0.05},
        "COCO": {"position": "long", "conviction": 0.05},
        "IPAR": {"position": "long", "conviction": 0.05},
        "YSG": {"position": "long", "conviction": 0.02},
        "HLF": {"position": "long", "conviction": 0.02},

        "WBA": {"position": "short", "conviction": 0.05},
        "ANDE": {"position": "short", "conviction": 0.05},
        "TGT": {"position": "short", "conviction": 0.02},
        "STZ": {"position": "short", "conviction": 0.05},
        "PEP": {"position": "short", "conviction": 0.05},
        "SAM": {"position": "short", "conviction": 0.05},
        "MGPI": {"position": "short", "conviction": 0.05},
        "ENR": {"position": "short", "conviction": 0.05},
        "SPB": {"position": "short", "conviction": 0.05},
        "COTY": {"position": "short", "conviction": 0.05},
        "KVUE": {"position": "short", "conviction": 0.05},
        "REYN": {"position": "short", "conviction": 0.02},
        "UVV": {"position": "short", "conviction": 0.02},
        "EL": {"position": "short", "conviction": 0.02},
        "EPC": {"position": "short", "conviction": 0.02},
        "CPB": {"position": "short", "conviction": 0.02}

    }
    
    # Build portfolio with target volatility and portfolio value
    build_portfolio = CorrelationAwarePortfolioBuilder(
        tickers=tickers3,  # Changed to tickers2 to test with the new portfolio
        target_annual_vol=0.17,  # 17% target volatility (adjust as needed)
        portfolio_value=50_000,  # $1M base capital (before leverage)
        leverage=1.5,  # 1.75x leverage (175% gross exposure)
        target_net_exposure=0.30,  # 35% net long exposure
        lookback_days=252 * 3  # 5 years of data
    )
    
    # Build risk-based portfolio with target volatility
    print("\n" + "="*80)
    print("CONSUMER STAPLES PORTFOLIO ANALYSIS (5-YEAR PERFORMANCE)")
    print("="*80)
    
    # Build with risk-based strategy and volatility targeting
    portfolio, allocation_df = build_portfolio.build_portfolio()

    # from backend.src.db.core.db_config import MarketSession
    # from backend.src.db.core.market_data_models import *
    # from backend.testing.alpaca_trade import AlpacaTrader

    # trader = AlpacaTrader(paper=True)
    # session = MarketSession()

    # for index, row in allocation_df.iterrows():
    #     ticker = row['ticker']
    #     position = row['position']
    #     position_size = row['position_size']
    #     recent_price = session.query(Ticker).filter(Ticker.ticker == ticker).first().price

    #     calc_shares = abs(position_size / recent_price)
    #     calc_shares = round(calc_shares, 0)
    #     calc_shares = int(calc_shares)
    #     print(f"{ticker}: {calc_shares} shares")

    #     if position == 'long':
    #         trader.buy(symbol=ticker, qty=calc_shares)
    #     else:
    #         trader.sell(symbol=ticker, qty=calc_shares)


    # session.close()
        
    

        