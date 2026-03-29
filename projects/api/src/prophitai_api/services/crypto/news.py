import pandas as pd
import asyncio
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_shared.time_utils import get_current_utc_time
from datetime import timedelta
from prophitai_api.utils.serialize_output import serialize_sqlalchemy_obj

class CryptoNewsService:
    def __init__(self):
        self.fmp = FMP_API_DATA()

    async def get_crypto_news_general(self, row_limit: int = 1000, from_date: str = None, to_date: str = None):
        """
        Get crypto news from FMP
        """
        all_news = []
        tasks = []

        for i in range(0, 10):
            tasks.append(asyncio.to_thread(self.fmp.get_latest_crypto_news, page=i, limit=250))

        results = await asyncio.gather(*tasks)

        for data in results:
            if data:
                all_news.extend(data)

        df = pd.DataFrame(all_news)
        df = df[:row_limit]

        return df.to_dict(orient='records')

    async def get_crypto_news_by_symbol(self, symbol: str, row_limit: int = 250, from_date: str = None, to_date: str = None):
        """
        Get crypto news by symbol from FMP
        """
        if row_limit > 250:
            row_limit = 250

        data = self.fmp.get_crypto_news(symbols=symbol, limit=row_limit, from_date=from_date, to_date=to_date)
        df = pd.DataFrame(data)
        df = df[:row_limit]

        return df.to_dict(orient='records')
