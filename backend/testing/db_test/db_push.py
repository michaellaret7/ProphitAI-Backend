from backend.testing.db_test.test_price_data import FMP_API_DATA
from backend.testing.db_test.db_config import MarketSession
from backend.testing.db_test.market_data_models import (Ticker, 
                                                        FinancialRatio, 
                                                        IncomeStatement, 
                                                        BalanceSheet, 
                                                        Dividend, 
                                                        EarningsTranscript,
                                                        CashFlowStatement, 
                                                        ETFHolding,
                                                        ETFInfo, 
                                                        AnalystRecommendation,
                                                        PriceTargetSummary,
                                                        Rating,
                                                        StockGradesIndividual,
                                                        StockGradesSummary)
from datetime import datetime
from decimal import Decimal
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from sqlalchemy import Numeric, Date, DateTime, insert, Integer, Float, JSON
import json

class DBPushData:
    def __init__(self):
        self.fmp_api = FMP_API_DATA()

    def _get_or_create_ticker(self, session, ticker_symbol):
        ticker = session.query(Ticker).filter(Ticker.ticker == ticker_symbol).first()
        if not ticker:
            ticker = Ticker(id=uuid.uuid4(), ticker=ticker_symbol)
            session.add(ticker)
            session.commit()
            print(f"Created new ticker: {ticker_symbol} with ID: {ticker.id}")
        return ticker

    def push_price_target_summary_threaded(self, ticker_symbol):
        price_target_summary_data = self.fmp_api.get_price_target_summary(ticker_symbol)

        if not price_target_summary_data:
            print(f"No price target summary found for {ticker_symbol}.")
            return

        summary_data = price_target_summary_data[0]

        session = MarketSession()
        try:
            ticker = self._get_or_create_ticker(session, ticker_symbol)
            if not ticker:
                print(f"Could not process ticker: {ticker_symbol}")
                return

            existing_summary = session.query(PriceTargetSummary).filter_by(ticker_id=ticker.id).first()

            if existing_summary:
                is_changed = False
                for key, value in summary_data.items():
                    if not hasattr(existing_summary, key):
                        continue

                    new_value = value
                    column_type = getattr(PriceTargetSummary, key).property.columns[0].type
                    if new_value is not None:
                        if isinstance(column_type, Integer):
                            new_value = int(new_value)
                        elif isinstance(column_type, Float):
                            new_value = float(new_value)
                        elif isinstance(column_type, JSON) and isinstance(new_value, str):
                            new_value = json.loads(new_value)

                    if getattr(existing_summary, key) != new_value:
                        setattr(existing_summary, key, new_value)
                        is_changed = True
                
                if is_changed:
                    session.commit()
                    print(f"Successfully updated price target summary for {ticker_symbol}.")
                else:
                    print(f"No updates needed for price target summary for {ticker_symbol}.")
            else:
                new_summary_dict = {k: v for k, v in summary_data.items() if hasattr(PriceTargetSummary, k)}
                if 'publishers' in new_summary_dict and isinstance(new_summary_dict['publishers'], str):
                    new_summary_dict['publishers'] = json.loads(new_summary_dict['publishers'])
                
                new_summary_dict['ticker_id'] = ticker.id
                
                new_instance = PriceTargetSummary(**new_summary_dict)
                session.add(new_instance)
                session.commit()
                print(f"Successfully inserted new price target summary for {ticker_symbol}.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred during operation for {ticker_symbol}: {e}")
        finally:
            session.close()


    def push(self, max_workers=4, push_function=None):
        session = MarketSession()
        ticker_symbols = [r[0] for r in session.query(Ticker.ticker).filter(Ticker.is_etf == False).all()]
        session.close()

        print(f"Processing {len(ticker_symbols)} tickers...")
        start_time = time.time()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_ticker = {executor.submit(push_function, symbol): symbol for symbol in ticker_symbols}

            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    future.result()
                except Exception as exc:
                    print(f'Ticker {ticker} generated an exception: {exc}')
        
        end_time = time.time()
        print(f"Finished processing all tickers in {end_time - start_time:.2f} seconds.")
        return 


if __name__ == "__main__":
    db_pusher = DBPushData()
    db_pusher.push(push_function=db_pusher.push_price_target_summary_threaded)


    



        

  
