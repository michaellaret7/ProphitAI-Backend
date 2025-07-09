import json
import logging
from datetime import datetime, timedelta
from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.utils.formatting import round_floats_in_object
from backend.src.portfolio_optimization.phase_two.phase_two_extract_assets_classes import PhaseTwoExtractAssetClasses
from backend.src.portfolio_optimization.phase_two.phase_two_filters import PhaseTwoFilters
from backend.src.portfolio_optimization.phase_two.phase_two_performance_metrics import PhaseTwoPerformanceData
from backend.src.portfolio_optimization.phase_two.phase_two_run_llm import PhaseTwoRunLLM
from backend.src.data.user_information import get_user_information

logger = logging.getLogger(__name__)

output = """
{
  "portfolio_thesis": "This portfolio is crafted for a young, high-risk-tolerance investor targeting aggressive long-term capital growth through disruptive innovation, thematic sector leadership, and global diversification. The allocation is strategically overweight high-conviction technology, AI, and semiconductor subsectors—leveraging their robust forward earnings momentum—while balancing cyclical and defensive exposures to manage volatility amid macro uncertainty and sector rotation. Emerging markets, select alternatives, and real assets (REITs, gold) are introduced for alpha, currency diversification, and inflation protection. The portfolio is structured to outperform the S&P 500 by harnessing secular growth themes, capturing tactical opportunities in mid/small caps, and implementing disciplined risk management to navigate persistent inflation, policy shifts, and market volatility.",
  "portfolio": [
    {
      "asset_class": "wireless_telecommunication_services",
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

class PhaseTwo:
    def __init__(self, phase_one_data):
        self.phase_one_data = phase_one_data
        self.lookback_years = 1.5
        
    def _get_market_data(self, ticker):
        """Helper method to fetch market data with proper date range."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*self.lookback_years)
        
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
        
        return data

    def screen_and_analyze_tickers(self):
        assets = PhaseTwoExtractAssetClasses(self.phase_one_data)
        asset_class_allocations = assets.get_asset_class_allocations()
        
        # Pre-fetch market data once for all tickers
        logger.info("Pre-fetching market data for all tickers...")
        spy_data = self._get_market_data('SPY')
        xlf_data = self._get_market_data('XLF')
        
        # Pre-calculate SPY returns once
        spy_returns = None
        if spy_data is not None:
            spy_returns_calc = CalculateTickerReturns(spy_data)
            spy_returns = spy_returns_calc.calculate_daily_total_returns()

        filtered_tickers = {}
        for asset_class, allocation in asset_class_allocations.items():
            filters = PhaseTwoFilters(asset_class)

            tickers = filters.get_asset_class_tickers() # --> get all tickers for an asset class
            tickers_sorted, tickers_data = filters.filter_tickers(tickers) # --> filter tickers and get their data

            ticker_dict = []

            for ticker in tickers_sorted:
                # Get the pre-fetched data for this ticker
                ticker_data = tickers_data.get(ticker)
                
                phase_two_performance_metrics = PhaseTwoPerformanceData(ticker)

                # Pass pre-fetched data to avoid duplicate fetches
                momentum_metrics, volatility_metrics, annualized_total_return, holding_period_return, performance_metrics = phase_two_performance_metrics.calculate_performance_metrics_and_factors(
                    equity_data=ticker_data,
                    spy_data=spy_data,
                    spy_returns=spy_returns,
                    xlf_data=xlf_data
                )
                fundamental_data = phase_two_performance_metrics.get_fundamental_metrics()

                logger.debug(f"Momentum metrics for {ticker}: {momentum_metrics}")
                logger.debug(f"Volatility metrics for {ticker}: {volatility_metrics}, {annualized_total_return}, {holding_period_return}")
                logger.debug(f"Performance metrics for {ticker}: {performance_metrics}")
                logger.debug(f"Fundamental estimates for {ticker}: {fundamental_data['fundamental_estimates']}")
                logger.debug(f"Fundamental report for {ticker}: {fundamental_data['fundamental_report']}")

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
            
            filtered_tickers[asset_class] = {
                "allocation": allocation,
                "tickers": ticker_dict
            }

        filtered_tickers = round_floats_in_object(filtered_tickers) # --> round floats to 3 decimal places to reduce token usage

        return filtered_tickers
    
    def final_recommendations(self, filtered_tickers, user_profile_formatted):
        final_recommendations = {}

        for asset_class, data in filtered_tickers.items():
            asset_class_json = json.dumps({asset_class: data})

            llm = PhaseTwoRunLLM()
            user_prompt = llm.build_user_prompt(asset_class_json)
            system_prompt = llm.build_system_prompt(user_profile_formatted=user_profile_formatted, num_top_tickers=10)

            response = llm.run(system_prompt, user_prompt)
            response_dict = response.model_dump()
            logger.info(f"Response: {type(response_dict)}")
            logger.info(f"Parsed recommendations for {asset_class}: {response_dict}")

            final_recommendations[asset_class] = response_dict

        return final_recommendations


if __name__ == "__main__":
    phase_one_data_parsed = json.loads(output)
    phase_two = PhaseTwo(phase_one_data_parsed)

    user_profile_formatted = get_user_information()

    filtered_and_analyzed_tickers = phase_two.screen_and_analyze_tickers()

    final_recommendations = phase_two.final_recommendations(filtered_and_analyzed_tickers, user_profile_formatted)
    logger.info(f"Final recommendations: {final_recommendations}")
    logger.info(type(final_recommendations))









    
    
    