from backend.src.calculations.risk_calculations.ticker_risk_calculations import TickerRiskCalculations
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.repositories.price_data import get_price_data_daily
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

class BuildPortfolio:
    def __init__(self, tickers: dict[str, float], target_annual_vol: float, portfolio_value: float):
        self.tickers = tickers
        self.target_annual_vol = target_annual_vol
        self.portfolio_value = portfolio_value

    def _fetch_ticker_data(self, ticker):
        """Helper to fetch data for a single ticker"""
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()
        price_data = get_price_data_daily(ticker, start_date, end_date)
        volatility = VolatilityFactors(price_data['close']).annualized_volatility(lookback_days=252)
        return ticker, volatility, price_data

    def build_portfolio(self):
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        ticker_positions = {}
        total_long_value = 0
        total_short_value = 0
        
        print(f"\nBuilding portfolio with target volatility: {self.target_annual_vol:.1%}")
        print(f"Portfolio value: ${self.portfolio_value:,.2f}\n")
        
        # Fetch all data in parallel
        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_ticker = {
                executor.submit(self._fetch_ticker_data, ticker): ticker 
                for ticker in self.tickers.keys()
            }
            
            # Process results as they complete
            for future in as_completed(future_to_ticker):
                ticker, volatility, price_data = future.result()
                ticker_data = self.tickers[ticker]
                
                position_size = TickerRiskCalculations(ticker).calculate_ticker_position_size(
                    self.portfolio_value, 
                    self.target_annual_vol, 
                    position_annual_vol=volatility, 
                    risk_allocation=ticker_data['conviction'], 
                    correlation=0.0
                )
                
                # Store with proper sign
                if ticker_data['position'] == "long":
                    actual_position_value = position_size['position_size']
                    total_long_value += actual_position_value
                else:
                    actual_position_value = -position_size['position_size']
                    total_short_value += position_size['position_size']
                
                ticker_positions[ticker] = {
                    'position': ticker_data['position'],
                    'position_size': actual_position_value,
                    'position_weight': position_size['position_weight'],
                    'volatility': volatility
                }
                
                print(f"{ticker:6} ({ticker_data['position']:5}): "
                    f"Size={'$' + f'{actual_position_value:>11,.2f}':>13}, "
                    f"Weight={position_size['position_weight']:>6.2%}, "
                    f"Vol={volatility:>6.2%}")
        
        # Calculate metrics
        gross_exposure = total_long_value + total_short_value
        net_exposure = total_long_value - total_short_value
        
        print(f"\n{'='*50}")
        print(f"Long positions:  ${total_long_value:>12,.2f} ({total_long_value/self.portfolio_value:>6.1%})")
        print(f"Short positions: ${total_short_value:>12,.2f} ({total_short_value/self.portfolio_value:>6.1%})")
        print(f"{'='*50}")
        print(f"Gross exposure:  ${gross_exposure:>12,.2f} ({gross_exposure/self.portfolio_value:>6.1%})")
        print(f"Net exposure:    ${net_exposure:>12,.2f} ({net_exposure/self.portfolio_value:>6.1%})")
        print(f"{'='*50}")
        print(f"Cash needed:     ${net_exposure:>12,.2f}")
        print(f"Cash remaining:  ${self.portfolio_value - net_exposure:>12,.2f}")
        
        return ticker_positions

if __name__ == "__main__":
    tickers = {
        "AAPL": {"conviction": 0.10, "position": "short"},
        "MSFT": {"conviction": 0.05, "position": "long"},
        "GOOGL": {"conviction": 0.05, "position": "short"},
        "NVDA": {"conviction": 0.15, "position": "long"},
        "JPM": {"conviction": 0.05, "position": "long"},
        "JNJ": {"conviction": 0.05, "position": "long"},
        "SPY": {"conviction": 0.15, "position": "long"},
        "LQD": {"conviction": 0.05, "position": "long"},
        "QQQ": {"conviction": 0.05, "position": "long"},
        "IWM": {"conviction": 0.05, "position": "long"},
        "TLT": {"conviction": 0.15, "position": "long"},
        "BIL": {"conviction": 0.01, "position": "long"},
        "AVGO": {"conviction": 0.05, "position": "long"},
        "TSLA": {"conviction": 0.05, "position": "long"},
        "V": {"conviction": 0.10, "position": "long"},
        "RACE": {"conviction": 0.05, "position": "short"},
        "LMT": {"conviction": 0.05, "position": "long"},
        "CRDO": {"conviction": 0.15, "position": "long"},
        "FNGR": {"conviction": 0.05, "position": "short"},
        "BAC": {"conviction": 0.10, "position": "short"},
    }
    build_portfolio = BuildPortfolio(tickers, 0.50, 500_000)
    # build_portfolio.build_portfolio()

    portfolio_dict = build_portfolio.build_portfolio()
    dict_p = {}

    for ticker, info in portfolio_dict.items():
        if info["position"] == "long":
            dict_p[ticker] = info["position_weight"]
        else:
            dict_p[ticker] = -info["position_weight"]
    print(dict_p)

    from backend.src.calculations.returns_calculations.portfolio_returns_calculations import CalculatePortfolioReturns
    from datetime import datetime, timedelta
    
    # Create portfolio returns calculator
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*4)
    
    portfolio_calculator = CalculatePortfolioReturns(
        tickers_weights=dict_p,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )
    
    # Calculate and display portfolio returns
    annualized_return = portfolio_calculator.calculate_annualized_total_return()
    holding_period_return = portfolio_calculator.calculate_holding_period_return()
    
    print(f"Annualized Total Return: {annualized_return:.2%}")
    print(f"Holding Period Return: {holding_period_return:.2%}")
    
    # Also plot the performance
    portfolio_calculator.plot_portfolio_performance()


