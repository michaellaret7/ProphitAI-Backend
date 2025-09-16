"""
Cut the position when its 5% below the highest max of the holding period 
if appl was in the portfolio and its high from the duration of the holding period was 100 and the price hits 95, cut the position
"""
from app.db.core.market_data_models import Price, Ticker
from app.db.core.db_config import MarketSession
from datetime import datetime, timedelta
import pandas as pd
import time
from app.repositories.price_data import get_price_data_15_mins

class DrawdownManagement:
    def __init__(self, ticker: str = None):
        self.ticker = ticker.upper()
        self.first_cut_drawdown = .05
        self.position_entry_date = '2025-06-01'
        self.last_checked_date = '2025-07-14'
        self.curent_date = '2025-07-16'
        self.peak_price = self._get_ticker_peak()

    def _get_ticker_peak(self):
        start_date = self.position_entry_date
        end_date = self.last_checked_date
        df = get_price_data_15_mins(self.ticker, start_date, end_date)
        return df.max()['high']

    def check_drawdown_simulation(self):
        df = get_price_data_15_mins(self.ticker, self.last_checked_date, self.curent_date)
        df.loc['2025-07-15 14:15:00', 'high'] = 709.78

        if df.empty:
            return 'DataFrame is empty'
        else:
            for index, row in df.iterrows():
                if row['high'] < self.peak_price * (1 - self.first_cut_drawdown):
                    print(f'Cut The position by 5% at {index} 🗡️, current high price is {row["high"]}, threshold is {self.peak_price * (1 - self.first_cut_drawdown)}')
                    return f'Drawdown Crossed Threshold, Cut position by 5% 🗡️, current high price is {row["high"]}, threshold is {self.peak_price * (1 - self.first_cut_drawdown)}'
                else:
                    print(f'All good ✅ at {index}, current high price is {row["high"]}, threshold is {self.peak_price * (1 - self.first_cut_drawdown)}') 
                time.sleep(.25)

            return 'All good ✅'

if __name__ == "__main__":
    drawdown_management = DrawdownManagement(ticker='META')
    print(drawdown_management.check_drawdown_simulation())