from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_shared.time_utils import get_current_utc_time
from datetime import timedelta
from prophitai_api.utils.serialize_output import serialize_sqlalchemy_obj
from prophitai_calculations.technicals.momentum import calc_rsi, calc_macd
from prophitai_calculations.technicals.trend import calc_sma, calc_ema, calc_ichimoku
from prophitai_calculations.technicals.volatility import calc_bollinger_bands
import pandas as pd
import asyncio

class CryptoPriceService:
    def __init__(self):
        self.fmp = FMP_API_DATA()

    async def get_crypto_eod_price_by_symbol(self, symbol: str, from_date: str = None, to_date: str = None, technical_indicators: bool = True):
        """
        Get crypto price by symbol from FMP
        """
        from datetime import datetime

        # Ensure dates are datetime objects
        if isinstance(from_date, str):
            from_date = datetime.strptime(from_date, "%Y-%m-%d")
        if isinstance(to_date, str):
            to_date = datetime.strptime(to_date, "%Y-%m-%d")

        data = self.fmp.get_daily_prices_for_ticker(ticker=symbol, from_date=from_date, to_date=to_date) #data retrieval function

        # FMP API returns a dict with 'historical' key for this endpoint
        if isinstance(data, dict) and 'historical' in data:
            df = pd.DataFrame(data['historical'])
        else:
            df = pd.DataFrame(data)

        if not df.empty and 'close' in df.columns:
            # Ensure numeric columns and correct sort order
            cols_to_numeric = ['open', 'high', 'low', 'close']
            for col in cols_to_numeric:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            if 'date' in df.columns:
                 df.sort_values('date', ascending=True, inplace=True)

            if technical_indicators:
                close = df['close']
                high = df['high']
                low = df['low']

                # SMAs
                df['SMA8'] = calc_sma(close, window=8)
                df['SMA20'] = calc_sma(close, window=20)
                df['SMA50'] = calc_sma(close, window=50)
                df['SMA100'] = calc_sma(close, window=100)
                df['SMA200'] = calc_sma(close, window=200)

                # RSI
                df['RSI'] = calc_rsi(close, window=14)

                # MACD
                macd_line, signal, histogram = calc_macd(close, fast=12, slow=26, signal_span=9)
                df['MACD'] = macd_line
                df['MACD_Signal'] = signal
                df['MACD_Hist'] = histogram

                # Bollinger Bands
                bb_upper, bb_middle, bb_lower = calc_bollinger_bands(close, window=20, num_std=2.0)
                df['Bollinger_Bands_Upper'] = bb_upper
                df['Bollinger_Bands_Lower'] = bb_lower
                df['Bollinger_Bands_Middle'] = bb_middle

                # Ichimoku Cloud
                tenkan, kijun, senkou_a, senkou_b, chikou = calc_ichimoku(high, low, close)
                df['Ichimoku_Cloud_Tenkan'] = tenkan
                df['Ichimoku_Cloud_Kijun'] = kijun
                df['Ichimoku_Cloud_Senkou_A'] = senkou_a
                df['Ichimoku_Cloud_Senkou_B'] = senkou_b
                df['Ichimoku_Cloud_Chikou'] = chikou

                # Clean up
                df.dropna(inplace=True)

        return df
