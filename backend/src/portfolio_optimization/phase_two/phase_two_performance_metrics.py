from datetime import datetime, timedelta
from backend.src.repositories.market_data.cached_ticker_repository import get_cached_ticker_data
from finvizfinance.quote import finvizfinance
from backend.src.utils.determine_etf import is_etf_ticker
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository

lookback_years = 1.5

class PhaseTwoPerformanceData:
    def __init__(self, ticker):
        self.ticker = ticker
    
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Convert dates to ISO format strings for caching (hashable)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Use the cached function
        data = get_cached_ticker_data(
            ticker=ticker,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d"
        )
        
        if data is None:
            return None

        return data
    
    def calculate_performance_metrics_and_factors(self, equity_data=None, spy_data=None, spy_returns=None, xlf_data=None):
        # Use pre-fetched data if provided, otherwise fetch it
        if equity_data is None:
            equity_data = self._get_ticker_data(self.ticker)
        
        price_data = equity_data['close']
        volume_data = equity_data['volume']

        if spy_data is None:
            spy_df = self._get_ticker_data('SPY')
        else:
            spy_df = spy_data
            
        spy_price_data = spy_df['close']
        
        # Pre-calculate SPY returns to pass to TickerPerformanceMetrics
        if spy_returns is None:
            spy_returns_calc = CalculateTickerReturns(spy_df)
            spy_returns = spy_returns_calc.calculate_daily_total_returns()

        if xlf_data is None:
            sector_df = self._get_ticker_data('XLF')
        else:
            sector_df = xlf_data
            
        sector_price_data = sector_df['close']
        
        momentum_factors = MomentumFactors(price_data, volume_data, spy_price_data, sector_price_data).calc_all()
        volatility_factors = VolatilityFactors(price_data, spy_price_data).calc_all()
        returns_calculator = CalculateTickerReturns(equity_data)
        
        # Pass pre-fetched data and market returns to avoid duplicate fetches
        performance_calculator = TickerPerformanceMetrics(self.ticker, price_data=equity_data, market_returns=spy_returns).calc_all()

        # Turn output into a dictionary
        momentum_factors = momentum_factors.model_dump()
        volatility_factors = volatility_factors.model_dump()
        performance_metrics = performance_calculator.model_dump()

        return momentum_factors, volatility_factors, returns_calculator.calculate_annualized_total_return(), returns_calculator.calculate_holding_period_return(), performance_metrics
    
    def get_fundamental_metrics(self):
        fundamental_repository = FundamentalDataRepository()

        fundamental_data = {}

        if is_etf_ticker(self.ticker):
            etf = finvizfinance(self.ticker)
            etf_description = etf.ticker_description()

            fundamental_data['fundamental_estimates'] = 'None this is an ETF, no fundamental estimates available'
            fundamental_data['fundamental_report'] = etf_description

            return fundamental_data
        else:
            fundamental_estimates = fundamental_repository.fetch_fundamental_estimates(self.ticker)
            fundamental_report = fundamental_repository.fetch_fundamental_report(self.ticker)

            fundamental_data['fundamental_estimates'] = fundamental_estimates
            fundamental_data['fundamental_report'] = fundamental_report

            return fundamental_data