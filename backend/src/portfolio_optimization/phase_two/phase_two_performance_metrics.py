from datetime import datetime, timedelta
from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data
from finvizfinance.quote import finvizfinance
from backend.src.utils.determine_etf import is_etf_ticker
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.utils.determine_etf import is_etf_ticker
import logging

logger = logging.getLogger(__name__)

lookback_years = 1.5

class PhaseTwoPerformanceData:
    def __init__(self, ticker):
        self.ticker = ticker
        self.is_etf = is_etf_ticker(ticker)
    
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Convert dates to ISO format strings for caching (hashable)
        start_date_str = start_date.isoformat()
        end_date_str = end_date.isoformat()
        
        # Use the cached function
        data = get_ticker_price_data(
            ticker=ticker,
            start_date=start_date_str,
            end_date=end_date_str,
            interval="1d"
        )
        
        if data is None:
            return None

        return data
    
    def calculate_performance_metrics_and_factors(self, equity_data=None, spy_data=None, spy_returns=None, xlf_data=None):
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
        
        # these are the calculations and factors that are used in the ticker selection process (ADD REST OF FACTORS)
        returns = {
            'holding_period_return': CalculateTickerReturns(equity_data).calculate_holding_period_return(),
            'annualized_total_return': CalculateTickerReturns(equity_data).calculate_annualized_total_return()
        }
        performance_metrics = TickerPerformanceMetrics(self.ticker, price_data=equity_data, market_returns=spy_returns).calc_all().model_dump()  
        momentum_factors = MomentumFactors(price_data, volume_data, spy_price_data, sector_price_data).calc_all().model_dump()
        volatility_factors = VolatilityFactors(price_data, spy_price_data).calc_all().model_dump()

        if not self.is_etf:
            try:
                quality_factors = QualityFactors(ticker=self.ticker).calc_all()
                quality_factors = quality_factors.model_dump()
            except Exception as e:
                logger.warning(f"Failed to calculate quality factors for {self.ticker}: {e}")
                quality_factors = None
        else:
            quality_factors = "None this is an ETF, no quality factors available"

        return {
            'momentum_factors': momentum_factors,
            'volatility_factors': volatility_factors,
            'quality_factors': quality_factors,
            'returns': returns,
            'performance_metrics': performance_metrics
        }
    
    def get_fundamental_metrics(self): # --> get the fundamental metrics and estimates for the ticker
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

            fundamental_data['fundamental_estimates'] = fundamental_estimates if fundamental_estimates is not None else None
            fundamental_data['fundamental_report'] = fundamental_report if fundamental_report is not None else None

            return fundamental_data


if __name__ == '__main__':
    phase_two_performance_data = PhaseTwoPerformanceData(ticker='XLE')
    logger.info(phase_two_performance_data.calculate_performance_metrics_and_factors())