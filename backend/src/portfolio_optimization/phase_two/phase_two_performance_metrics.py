from datetime import datetime, timedelta
from backend.src.repositories.price_data import get_price_data_daily
from finvizfinance.quote import finvizfinance
from backend.src.utils.determine_etf import is_etf_ticker
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.utils.determine_etf import is_etf_ticker
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import *
import logging
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj

logger = logging.getLogger(__name__)

lookback_years = 2

class PhaseTwoPerformanceData:
    def __init__(self, ticker):
        self.ticker = ticker
        self.is_etf = is_etf_ticker(ticker)
    
    def _get_ticker_data(self, ticker):
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        # Use the new function with datetime objects
        data = get_price_data_daily(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date
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
            spy_returns_calc = CalculateTickerReturns(spy_df, 'SPY')
            spy_returns = spy_returns_calc.calculate_daily_total_returns()

        if xlf_data is None:
            sector_df = self._get_ticker_data('XLF')
        else:
            sector_df = xlf_data
            
        sector_price_data = sector_df['close']
        
        # these are the calculations and factors that are used in the ticker selection process (ADD REST OF FACTORS)
        returns = {
            'holding_period_return': CalculateTickerReturns(equity_data, self.ticker).calculate_holding_period_return(),
            'annualized_total_return': CalculateTickerReturns(equity_data, self.ticker).calculate_annualized_total_return()
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
        session = MarketSession()
        
        fundamental_data = {}

        if is_etf_ticker(self.ticker):
            etf_info = session.query(ETFInfo).join(Ticker).filter(Ticker.ticker == self.ticker).first()
            fundamental_data['fundamental_report'] = serialize_sqlalchemy_obj(etf_info)
            fundamental_data['fundamental_estimates'] = 'None this is an ETF, no fundamental estimates available'
            fundamental_data['analyst_recommendations'] = 'None this is an ETF, no analyst recommendations available'

            session.close()

            return fundamental_data
        else: 
            fundamental_estimates = session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == self.ticker).all()
            fundamental_report = session.query(FundamentalReport).join(Ticker).filter(Ticker.ticker == self.ticker).all()
            analyst_recommendations = session.query(AnalystRecommendation).join(Ticker).filter(Ticker.ticker == self.ticker).first()


            fundamental_data['fundamental_estimates'] = [serialize_sqlalchemy_obj(est) for est in fundamental_estimates]
            fundamental_data['fundamental_report'] = [serialize_sqlalchemy_obj(report) for report in fundamental_report]
            fundamental_data['analyst_recommendations'] = serialize_sqlalchemy_obj(analyst_recommendations)

            session.close()

            return fundamental_data


if __name__ == '__main__':
    phase_two_performance_data = PhaseTwoPerformanceData(ticker='XLE')
    logger.info(phase_two_performance_data.get_fundamental_metrics())