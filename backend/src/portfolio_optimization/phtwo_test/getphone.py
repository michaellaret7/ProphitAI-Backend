import json
import logging
from backend.src.utils.determine_etf import is_etf_asset_class, is_etf_ticker
from datetime import datetime, timedelta
from backend.src.repositories.market_data.cached_ticker_repository import get_cached_ticker_data
from finvizfinance.quote import finvizfinance


logger = logging.getLogger(__name__)

lookback_years = 1.5

output = """
{
  "portfolio_thesis": "This portfolio is crafted for a young, high-risk-tolerance investor targeting aggressive long-term capital growth through disruptive innovation, thematic sector leadership, and global diversification. The allocation is strategically overweight high-conviction technology, AI, and semiconductor subsectors—leveraging their robust forward earnings momentum—while balancing cyclical and defensive exposures to manage volatility amid macro uncertainty and sector rotation. Emerging markets, select alternatives, and real assets (REITs, gold) are introduced for alpha, currency diversification, and inflation protection. The portfolio is structured to outperform the S&P 500 by harnessing secular growth themes, capturing tactical opportunities in mid/small caps, and implementing disciplined risk management to navigate persistent inflation, policy shifts, and market volatility.",
  "portfolio": [
    {
      "asset_class": "wireless_telecommunication_services",
      "allocation": 18,
      "position": "LONG",
      "reason": "AI/data center demand is fueling 40%+ earnings growth for sector leaders (NVDA, AVGO, MRVL, ARM); high conviction for multi-year outperformance and technological disruption."
    },
    {
      "asset_class": "sovereign",
      "allocation": 18,
      "position": "LONG",
      "reason": "AI/data center demand is fueling 40%+ earnings growth for sector leaders (NVDA, AVGO, MRVL, ARM); high conviction for multi-year outperformance and technological disruption."
    }
  ],
  "risk_management": {
    "portfolio_volatility": "Expected 18-22% (annualized), managed via diversified sector, geographic, and asset-class exposures; beta targeted at 1.1-1.3 relative to S&P 500.",
    "key_risks": [
      "Tech/AI sector concentration risk and multiple compression",
      "EM currency/sovereign volatility",
      "Policy and inflation shocks (Fed, tariffs, elections)",
      "Commodities cycle downside (energy/metals oversupply)",
      "Crypto drawdown risk"
    ],
    "hedging_strategy": "Diversification across growth, cyclical, defensive, and alternative assets. Maintain 7% cash for tactical rebalancing and volatility control. Use multi_utilities, corporate_bond_etfs, and precious_metals as core hedges; overweight healthcare and industrials for sector rotation defense. Monitor macro signals; be prepared to rotate into more defensive allocations if volatility or macro data deteriorate."
  }
}
"""

class PhaseTwoExtractAssetClasses:
    def __init__(self, phase_one_data):
        self.asset_classes = json.loads(phase_one_data)
    
    def get_asset_classes(self):
        portfolio = self.asset_classes.get("portfolio", [])
        asset_classes = [item.get("asset_class") for item in portfolio]
        return [ac for ac in asset_classes if ac]
    
    def get_asset_class_allocations(self):
        portfolio = self.asset_classes.get("portfolio", [])
        asset_class_allocations = {item.get("asset_class"): item.get("allocation") for item in portfolio}
        return asset_class_allocations

class PhaseTwoFilters:
    def __init__(self, asset_class):
        self.asset_class = asset_class
        self.minimum_daily_average_volume = 10_000
        self.is_etf = is_etf_asset_class(self.asset_class)
        with open('backend/src/data/database/database_schemas.json', 'r') as f:
            self.database_schemas = json.load(f)
        
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
    
    def get_asset_class_tickers(self):
        if self.asset_class == "cash":
            return []

        for sector_data in self.database_schemas.values():
            if "schemas" in sector_data:
                for schema_data in sector_data["schemas"].values():
                    if "tables" in schema_data and self.asset_class in schema_data["tables"]:
                        return schema_data["tables"][self.asset_class].get("tickers", [])
        
        logger.warning(f"No tickers found for asset class: {self.asset_class}")
        return []

    def _calculate_daily_average_volume(self, equity_data):
        total_volume = equity_data["volume"].sum()
        number_of_trading_days = len(equity_data)

        if number_of_trading_days == 0:
            return 0
            
        daily_average_volume = total_volume / number_of_trading_days
        return daily_average_volume

    def filter_tickers(self, tickers):
        filtered_tickers = []
        for ticker in tickers:

            data = self._get_ticker_data(ticker) # --> get the data for the ticker

            if data is not None and not data.empty:
                volume = self._calculate_daily_average_volume(data) # --> calculate the daily average volume for the ticker

                if volume > self.minimum_daily_average_volume:
                    filtered_tickers.append(ticker)

            else:
                logger.warning(f"No data returned for ticker '{ticker}', it will be skipped.")

        logger.info(f"Filtered tickers: {filtered_tickers}")
        return filtered_tickers
    
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
    
    def calculate_performance_metrics_and_factors(self):
        from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
        from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
        from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
        from backend.src.calculations.performance_calculations.ticker_performance_calculations import TickerPerformanceMetrics

        equity_data = self._get_ticker_data(self.ticker)
        price_data = equity_data['close']
        volume_data = equity_data['volume']

        spy_df = self._get_ticker_data('SPY')
        spy_price_data = spy_df['close']

        sector_df = self._get_ticker_data('XLF')
        sector_price_data = sector_df['close']
        
        momentum_factors = MomentumFactors(price_data, volume_data, spy_price_data, sector_price_data).calc_all()
        volatility_factors = VolatilityFactors(price_data, spy_price_data).calc_all()
        returns_calculator = CalculateTickerReturns(equity_data)
        performance_calculator = TickerPerformanceMetrics(self.ticker).calc_all()

        # Turn output into a dictionary
        momentum_factors = momentum_factors.model_dump()
        volatility_factors = volatility_factors.model_dump()
        performance_metrics = performance_calculator.model_dump()

        return momentum_factors, volatility_factors, returns_calculator.calculate_annualized_total_return(), returns_calculator.calculate_holding_period_return(), performance_metrics
    
    def get_fundamental_metrics(self):
        from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
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

from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.portfolio_optimization.phase_two.phase_two_prompts import SYSTEM_PROMPT_TEMPLATE, USER_PROMPT_TEMPLATE

class PhaseTwoRunLLM:
    def __init__(self):
        self.model, self.client = openai_model_and_client()
    
    def build_system_prompt(self, user_profile_formatted, num_top_tickers):
        pass
    
    def build_user_prompt(self, data):
        user_prompt = USER_PROMPT_TEMPLATE.format(data_string=data)
        return user_prompt
    
    def run(self, data):

        system_prompt = self.build_system_prompt()
        user_prompt = self.build_user_prompt()

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    
    def filter_llm_response(self, response):
        pass

        

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    assets = PhaseTwoExtractAssetClasses(output)
    asset_class_allocations = assets.get_asset_class_allocations()

    logger.info(f"Cache stats: {get_cached_ticker_data.cache_info()}")

    portfolio = {}

    for asset_class, allocation in asset_class_allocations.items():
        filters = PhaseTwoFilters(asset_class)

        tickers = filters.get_asset_class_tickers() # --> get all tickers for an asset class
        tickers = filters.filter_tickers(tickers) # --> filter tickers by daily average volume of over 10,000

        ticker_dict = []

        for ticker in tickers:
            phase_two_performance_metrics = PhaseTwoPerformanceData(ticker)

            momentum_metrics, volatility_metrics, annualized_total_return, holding_period_return, performance_metrics = phase_two_performance_metrics.calculate_performance_metrics_and_factors()
            fundamental_data = phase_two_performance_metrics.get_fundamental_metrics()

            # logger.info(f"Momentum metrics for {ticker}: {momentum_metrics}")
            # logger.info(f"Volatility metrics for {ticker}: {volatility_metrics}, {annualized_total_return}, {holding_period_return}")
            # logger.info(f"Performance metrics for {ticker}: {performance_metrics}")
            # logger.info(f"Fundamental estimates for {ticker}: {fundamental_data['fundamental_estimates']}")
            # logger.info(f"Fundamental report for {ticker}: {fundamental_data['fundamental_report']}")

            ticker_dict.append({
                "ticker": ticker,
                "momentum_metrics": momentum_metrics,
                "volatility_metrics": volatility_metrics,
                "annualized_total_return": annualized_total_return,
                "holding_period_return": holding_period_return,
                "performance_metrics": performance_metrics,
                "fundamental_estimates": fundamental_data['fundamental_estimates'],
                "fundamental_report": fundamental_data['fundamental_report']
            })
        
        portfolio[asset_class] = {
            "allocation": allocation,
            "tickers": ticker_dict
        }

    for asset_class, data in portfolio.items():
        logger.info("+"*100)
        # Create a new dict for each item to include the asset class name (the key) in the JSON
        asset_class_json = json.dumps({asset_class: data})
        llm = PhaseTwoRunLLM()
        logger.info(llm.build_user_prompt(asset_class_json))
        exit()
        # logger.info(asset_class_json)

    
    
    