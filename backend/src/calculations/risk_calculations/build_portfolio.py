from backend.src.calculations.risk_calculations.ticker_risk_calculations import TickerRiskCalculations
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.repositories.price_data import get_price_data_daily
from datetime import datetime, timedelta

class BuildPortfolio:
    def __init__(self, tickers: dict[str, float], target_annual_vol: float, portfolio_value: float):
        self.tickers = tickers
        self.target_annual_vol = target_annual_vol
        self.portfolio_value = portfolio_value

    def build_portfolio(self):
        start_date = datetime.now() - timedelta(days=365)
        end_date = datetime.now()

        ticker_positions = {}
        total_long_value = 0
        total_short_value = 0
        
        print(f"\nBuilding portfolio with target volatility: {self.target_annual_vol:.1%}")
        print(f"Portfolio value: ${self.portfolio_value:,.2f}\n")
        
        for ticker, ticker_data in self.tickers.items():
            price_data = get_price_data_daily(ticker, start_date, end_date)
            volatility = VolatilityFactors(price_data['close']).annualized_volatility(lookback_days=252)
            
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
                actual_position_value = -position_size['position_size']  # NEGATIVE
                total_short_value += position_size['position_size']  # Track absolute value
            
            ticker_positions[ticker] = {
                'position': ticker_data['position'],
                'position_size': actual_position_value,  # Negative for shorts
                'position_weight': position_size['position_weight'],
                'volatility': volatility
            }
            
            # Display with proper formatting
            print(f"{ticker:6} ({ticker_data['position']:5}): "
                f"Size={'$' + f'{actual_position_value:>11,.2f}':>13}, "  # Shows negative
                f"Weight={position_size['position_weight']:>6.2%}, "
                f"Vol={volatility:>6.2%}")
        
        # Calculate proper metrics
        gross_exposure = total_long_value + total_short_value
        net_exposure = total_long_value - total_short_value
        net_position_value = net_exposure  # This is what you actually need in cash
        
        print(f"\n{'='*50}")
        print(f"Long positions:  ${total_long_value:>12,.2f} ({total_long_value/self.portfolio_value:>6.1%})")
        print(f"Short positions: ${total_short_value:>12,.2f} ({total_short_value/self.portfolio_value:>6.1%})")
        print(f"{'='*50}")
        print(f"Gross exposure:  ${gross_exposure:>12,.2f} ({gross_exposure/self.portfolio_value:>6.1%})")
        print(f"Net exposure:    ${net_exposure:>12,.2f} ({net_exposure/self.portfolio_value:>6.1%})")
        print(f"{'='*50}")
        print(f"Cash needed:     ${net_position_value:>12,.2f}")
        print(f"Cash remaining:  ${self.portfolio_value - net_position_value:>12,.2f}")
        
        return ticker_positions

if __name__ == "__main__":
    tickers = {
        "AAPL": {"conviction": 0.10, "position": "short"},
        "MSFT": {"conviction": 0.05, "position": "long"},
        "GOOGL": {"conviction": 0.05, "position": "short"},
        "NVDA": {"conviction": 0.15, "position": "long"},
        "JPM": {"conviction": 0.05, "position": "short"},
        "JNJ": {"conviction": 0.05, "position": "short"},
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
    build_portfolio = BuildPortfolio(tickers, 0.175, 1_000_000)
    build_portfolio.build_portfolio()

