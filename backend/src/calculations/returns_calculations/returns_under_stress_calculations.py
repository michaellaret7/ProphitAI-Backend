from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data

class CalculateReturnsUnderStress:
    def __init__(self, ticker: str):
        self.ticker = ticker

    def _calculate_stress_returns(self, start_date: str, end_date: str):
        price_data = get_ticker_price_data(self.ticker, start_date, end_date, "1h")
        spy_data = get_ticker_price_data("SPY", start_date, end_date, "1h")
        
        if price_data is not None and not price_data.empty and spy_data is not None and not spy_data.empty:
            # Calculate ticker returns and cumulative returns
            price_data['ticker_returns'] = (price_data['close'].pct_change().fillna(0) * 100).dropna()
            price_data['ticker_cumulative_returns'] = ((1 + price_data['ticker_returns']/100).cumprod() - 1) * 100
            price_data['ticker_cumulative_returns'] = price_data['ticker_cumulative_returns'].round(2)
            
            # Calculate SPY returns and cumulative returns
            spy_data['spy_returns'] = (spy_data['close'].pct_change().fillna(0) * 100).dropna()
            spy_data['spy_cumulative_returns'] = ((1 + spy_data['spy_returns']/100).cumprod() - 1) * 100
            spy_data['spy_cumulative_returns'] = spy_data['spy_cumulative_returns'].round(2)
            
            price_data.set_index('date', inplace=True)
            spy_data.set_index('date', inplace=True)
            
            # Merge the dataframes on date index
            combined_data = price_data[['ticker_returns', 'ticker_cumulative_returns']].merge(
                spy_data[['spy_returns', 'spy_cumulative_returns']], 
                left_index=True, 
                right_index=True, 
                how='inner'
            )

            combined_data.reset_index(inplace=True)
            
            return combined_data
        
        return None

    def liberation_day_tariff_shock(self):
        return self._calculate_stress_returns("2025-04-02", "2025-04-09")

    def japan_nikkei_black_monday(self):
        return self._calculate_stress_returns("2024-08-05", "2024-08-07")

    def china_stock_market_crash(self):
        return self._calculate_stress_returns("2024-02-02", "2024-02-28")

    def credit_suisse_banking_crisis(self):
        return self._calculate_stress_returns("2023-03-14", "2023-03-20")

    def silicon_valley_bank_collapse(self):
        return self._calculate_stress_returns("2023-03-08", "2023-03-13")

    def ftx_crypto_exchange_collapse(self):
        return self._calculate_stress_returns("2022-11-02", "2022-11-11")

    def inflation_surge_peak(self):
        return self._calculate_stress_returns("2022-03-01", "2022-07-31")

    def russia_ukraine_war_shock(self):
        return self._calculate_stress_returns("2022-02-24", "2022-03-15")

    def evergrande_property_crisis(self):
        return self._calculate_stress_returns("2021-09-13", "2021-12-31")

    def omicron_variant_volatility(self):
        return self._calculate_stress_returns("2021-11-26", "2021-12-31")
    
    def fed_raises_rates_by_25bps_may_2022(self):
        return self._calculate_stress_returns("2022-05-05", "2022-05-10")

if __name__ == "__main__":
    stress_calculator = CalculateReturnsUnderStress("AAPL")

    print("Silicon Valley Bank Collapse:")
    print(stress_calculator.silicon_valley_bank_collapse())

    print("\nJapan Nikkei Black Monday:")
    print(stress_calculator.japan_nikkei_black_monday())

    print("\nFTX Crypto Exchange Collapse:")
    print(stress_calculator.ftx_crypto_exchange_collapse())

    print(stress_calculator.inflation_surge_peak())