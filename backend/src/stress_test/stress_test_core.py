"""
Core stress test class that orchestrates stress testing functionality.
"""
import pandas as pd
from backend.src.stress_test.historical_shocks.scenarios import STRESS_SCENARIOS
from backend.src.stress_test.data_fetcher import calculate_price_returns
# from backend.src.stress_test.historical_shocks.capture_analysis import calculate_portfolio_capture_ratio, calculate_ticker_capture_ratios
from backend.src.stress_test.historical_shocks.drawdown_metrics import calculate_portfolio_max_drawdown, calculate_ticker_max_drawdowns


class StressTest:
    def __init__(self, portfolio: dict = None):
        self.portfolio = portfolio
        self.tickers = list(portfolio.keys())
        
        # Initialize scenario data storage
        self.trump_tariff_crash = {}
        self.tariff_pause_relief_rally = {}
        self.svb_bank_collapse = {}
        self.hot_cpi_shock = {}
        self.powell_hawkish_jackson_hole_speech = {}
        self.japan_nikkei_black_monday = {}
        self.china_stock_market_crash = {}

        self._get_stress_scenario_returns()
        print('🚀 Initializing stress test...')
    
    def _get_stress_scenario_returns(self):
        """Fetch returns data for all predefined stress scenarios."""
        for scenario_name, scenario_data in STRESS_SCENARIOS.items():
            # Get the scenario attribute name (e.g., 'trump_tariff_crash')
            attr_name = scenario_name
            
            # Calculate returns for this scenario
            portfolio_returns, ticker_returns = calculate_price_returns(
                self.portfolio, 
                scenario_data['start_date'], 
                scenario_data['end_date']
            )
            
            # Store the results
            scenario_dict = getattr(self, attr_name, {})
            scenario_dict['portfolio_returns'] = portfolio_returns
            scenario_dict['ticker_returns'] = ticker_returns
            setattr(self, attr_name, scenario_dict)

    
    def calculate_max_drawdown(self, scenario_name: str, portfolio: bool = False, num_tickers: int = 5):
        """
        Calculate maximum drawdown for portfolio or individual tickers.
        
        :param scenario_name: Name of the stress scenario
        :param portfolio: If True, return portfolio drawdown. If False, return top N ticker drawdowns
        :param num_tickers: Number of tickers to return when portfolio=False (default: 5)
        :return: Float (portfolio drawdown) or Dict (ticker drawdowns)
        """
        scenario_data = getattr(self, scenario_name, None)
        if scenario_data is None:
            return f"Scenario '{scenario_name}' not found"

        if portfolio:
            portfolio_returns = scenario_data.get('portfolio_returns', pd.Series())
            return calculate_portfolio_max_drawdown(portfolio_returns)
        else:
            ticker_returns = scenario_data.get('ticker_returns', pd.DataFrame())
            return calculate_ticker_max_drawdowns(ticker_returns, num_tickers)


if __name__ == "__main__":
    portfolio = {
        'AAPL': .1,
        'MSFT': .1,
        'META': .1,
        'AMZN': .1,
        'NVDA': .1,
        'TSLA': .2,
        'NFLX': .2,
        'AAL': .2,
    }

    stress_test = StressTest(portfolio)
    print(stress_test.calculate_max_drawdown('japan_nikkei_black_monday', portfolio=True))
    print(stress_test.calculate_max_drawdown('japan_nikkei_black_monday', portfolio=False))