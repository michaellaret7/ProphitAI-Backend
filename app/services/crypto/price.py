from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.time_utils import get_current_utc_time
from datetime import timedelta
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.core.calculations.technical.indicators import TechnicalIndicators
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
                # Initialize TechnicalIndicators
                ti = TechnicalIndicators(df)

                # SMAs (keeping existing logic or using ti.moving_averages if preferred, sticking to existing for simplicity unless requested)
                df['SMA8'] = ti.moving_averages(lookbacks=[8], ma_type="sma")
                df['SMA20'] = ti.moving_averages(lookbacks=[20], ma_type="sma")
                df['SMA50'] = ti.moving_averages(lookbacks=[50], ma_type="sma")
                df['SMA100'] = ti.moving_averages(lookbacks=[100], ma_type="sma")
                df['SMA200'] = ti.moving_averages(lookbacks=[200], ma_type="sma")

                # RSI using calculations module
                df['RSI'] = ti.rsi(period=14)

                # MACD using calculations module
                macd_data = ti.macd(fast_period=12, slow_period=26, signal_period=9)
                df['MACD'] = macd_data['macd']
                df['MACD_Signal'] = macd_data['signal']
                df['MACD_Hist'] = macd_data['hist']

                # Bollinger Bands using calculations module
                df['Bollinger_Bands_Upper'] = ti.bollinger_bands(period=20, num_std=2.0)['bb_upper']
                df['Bollinger_Bands_Lower'] = ti.bollinger_bands(period=20, num_std=2.0)['bb_lower']
                df['Bollinger_Bands_Middle'] = ti.bollinger_bands(period=20, num_std=2.0)['bb_middle']

                # ADX using calculations module
                adx_df = ti.adx(period=14)
                df['ADX'] = adx_df['adx']

                # Ichimoku Cloud using calculations module
                ichimoku_df = ti.ichimoku_cloud(tenkan_period=9, kijun_period=26, senkou_b_period=52)
                df['Ichimoku_Cloud_Tenkan'] = ichimoku_df['tenkan_sen']
                df['Ichimoku_Cloud_Kijun'] = ichimoku_df['kijun_sen']
                df['Ichimoku_Cloud_Senkou_A'] = ichimoku_df['senkou_span_a']
                df['Ichimoku_Cloud_Senkou_B'] = ichimoku_df['senkou_span_b']
                df['Ichimoku_Cloud_Chikou'] = ichimoku_df['chikou_span']

                # TD Sequential using calculations module
                td_sequential_df = ti.td_sequential()
                df['TD_Buy_Setup'] = td_sequential_df['buy_setup']
                df['TD_Sell_Setup'] = td_sequential_df['sell_setup']
                df['TD_Buy_Setup_Complete'] = td_sequential_df['buy_setup_complete']
                df['TD_Sell_Setup_Complete'] = td_sequential_df['sell_setup_complete']
                df['TD_Buy_Countdown'] = td_sequential_df['buy_countdown']
                df['TD_Sell_Countdown'] = td_sequential_df['sell_countdown']
                df['TD_Buy_Signal'] = td_sequential_df['td_buy_signal']
                df['TD_Sell_Signal'] = td_sequential_df['td_sell_signal']

                # Clean up
                df.dropna(inplace=True)

        return df




