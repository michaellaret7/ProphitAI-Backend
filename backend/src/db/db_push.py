from backend.src.db.core.pull_fmp_data import FMP_API_DATA
from backend.src.db.core.db_config import MarketSession
from backend.src.db.core.market_data_models import (Ticker, 
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
                                                        StockGradesSummary,
                                                        StockNews,
                                                        PressRelease,
                                                        PriceTargetNews,
                                                        StockGradeNews,
                                                        GeneralNews,
                                                        )
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

    def push_stock_news_threaded(self, ticker_symbol):
        stock_news_data = self.fmp_api.get_stock_news(ticker_symbol, 1000)
        if not stock_news_data:
            print(f"No stock news found for {ticker_symbol}.")
            return

        session = MarketSession()
        try:
            ticker = self._get_or_create_ticker(session, ticker_symbol)
            if not ticker:
                print(f"Could not process ticker: {ticker_symbol}")
                return

            existing_urls = {url[0] for url in session.query(StockNews.url).filter_by(ticker_id=ticker.id).all()}
            
            to_insert = []
            processed_urls = set()

            for news_item in stock_news_data:
                url = news_item.get('url')
                if not url or len(url) > 512:
                    continue
                
                if url not in existing_urls and url not in processed_urls:
                    news_item['ticker_id'] = ticker.id
                    to_insert.append(news_item)
                    processed_urls.add(url)
            
            if to_insert:
                session.execute(insert(StockNews), to_insert)
                session.commit()
                print(f"Successfully inserted {len(to_insert)} new stock news for {ticker_symbol}.")
            else:
                print(f"No new stock news to insert for {ticker_symbol}.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred during operation for {ticker_symbol}: {e}")
        finally:
            session.close()

    def push_press_releases_threaded(self, ticker_symbol):
        press_releases_data = self.fmp_api.get_press_releases(ticker_symbol)
        if not press_releases_data:
            print(f"No press releases found for {ticker_symbol}.")
            return

        session = MarketSession()
        try:
            ticker = self._get_or_create_ticker(session, ticker_symbol)
            if not ticker:
                print(f"Could not process ticker: {ticker_symbol}")
                return

            existing_urls = {url[0] for url in session.query(PressRelease.url).filter_by(ticker_id=ticker.id).all()}
            
            to_insert = []
            processed_urls = set()

            for release_item in press_releases_data:
                url = release_item.get('url')
                if not url or len(url) > 512:
                    continue
                
                if url not in existing_urls and url not in processed_urls:
                    release_item['ticker_id'] = ticker.id
                    to_insert.append(release_item)
                    processed_urls.add(url)
            
            if to_insert:
                session.execute(insert(PressRelease), to_insert)
                session.commit()
                print(f"Successfully inserted {len(to_insert)} new press releases for {ticker_symbol}.")
            else:
                print(f"No new press releases to insert for {ticker_symbol}.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred during operation for {ticker_symbol}: {e}")
        finally:
            session.close()

    def push_price_target_news_threaded(self, ticker_symbol):
        price_target_news_data = self.fmp_api.get_price_target_news(ticker_symbol)
        if not price_target_news_data:
            print(f"No price target news found for {ticker_symbol}.")
            return

        session = MarketSession()
        try:
            ticker = self._get_or_create_ticker(session, ticker_symbol)
            if not ticker:
                print(f"Could not process ticker: {ticker_symbol}")
                return

            existing_urls = {url[0] for url in session.query(PriceTargetNews.newsURL).filter_by(ticker_id=ticker.id).all()}
            
            to_insert = []
            processed_urls = set()

            for news_item in price_target_news_data:
                url = news_item.get('newsURL')
                if not url or len(url) > 512:
                    continue
                
                if url not in existing_urls and url not in processed_urls:
                    news_item['ticker_id'] = ticker.id
                    to_insert.append(news_item)
                    processed_urls.add(url)
            
            if to_insert:
                session.execute(insert(PriceTargetNews), to_insert)
                session.commit()
                print(f"Successfully inserted {len(to_insert)} new price target news for {ticker_symbol}.")
            else:
                print(f"No new price target news to insert for {ticker_symbol}.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred during operation for {ticker_symbol}: {e}")
        finally:
            session.close()

    def push_stock_grade_news_threaded(self, ticker_symbol):
        stock_grade_news_data = self.fmp_api.get_stock_grade_news(ticker_symbol)
        if not stock_grade_news_data:
            print(f"No stock grade news found for {ticker_symbol}.")
            return

        session = MarketSession()
        try:
            ticker = self._get_or_create_ticker(session, ticker_symbol)
            if not ticker:
                print(f"Could not process ticker: {ticker_symbol}")
                return

            existing_urls = {url[0] for url in session.query(StockGradeNews.newsURL).filter_by(ticker_id=ticker.id).all()}
            
            to_insert = []
            processed_urls = set()

            for news_item in stock_grade_news_data:
                url = news_item.get('newsURL')
                if not url or len(url) > 512:
                    continue
                
                if url not in existing_urls and url not in processed_urls:
                    news_item['ticker_id'] = ticker.id
                    to_insert.append(news_item)
                    processed_urls.add(url)
            
            if to_insert:
                session.execute(insert(StockGradeNews), to_insert)
                session.commit()
                print(f"Successfully inserted {len(to_insert)} new stock grade news for {ticker_symbol}.")
            else:
                print(f"No new stock grade news to insert for {ticker_symbol}.")

        except Exception as e:
            session.rollback()
            print(f"An error occurred during operation for {ticker_symbol}: {e}")
        finally:
            session.close()

    def push_general_news(self):
        general_news_data = self.fmp_api.get_general_news()
        if not general_news_data:
            print("No general news found.")
            return

        session = MarketSession()
        try:
            to_insert = []
            keys_to_insert = set()

            for news_item in general_news_data:
                url = news_item.get('url')
                if not url or len(url) > 512:
                    continue

                symbols = news_item.get('symbols')
                if isinstance(symbols, str):
                    symbols = [symbols]
                
                if not symbols or not isinstance(symbols, list):
                    continue

                for ticker_symbol in symbols:
                    ticker = self._get_or_create_ticker(session, ticker_symbol)
                    if not ticker:
                        continue

                    if (ticker.id, url) in keys_to_insert:
                        continue

                    existing = session.query(GeneralNews.url).filter_by(ticker_id=ticker.id, url=url).first()
                    if existing:
                        continue
                    
                    item_to_insert = {
                        'ticker_id': ticker.id,
                        'publishedDate': news_item.get('publishedDate'),
                        'publisher': news_item.get('publisher'),
                        'title': news_item.get('title'),
                        'image': news_item.get('image'),
                        'site': news_item.get('site'),
                        'text': news_item.get('text'),
                        'url': url
                    }
                    
                    to_insert.append(item_to_insert)
                    keys_to_insert.add((ticker.id, url))

            if to_insert:
                session.execute(insert(GeneralNews), to_insert)
                session.commit()
                print(f"Successfully inserted {len(to_insert)} new general news records.")
            else:
                print("No new general news to insert.")
        
        except Exception as e:
            session.rollback()
            print(f"An error occurred during general news insertion: {e}")
        finally:
            session.close()


    def recreate_table(self, table_name):
        """Drops and recreates the press_releases table to ensure schema is up to date."""
        session = MarketSession()
        try:
            print(f"Dropping {table_name} table if it exists...")
            table_name.__table__.drop(session.bind, checkfirst=True)
            print(f"Creating {table_name} table...")
            table_name.__table__.create(session.bind)
            session.commit()
            print(f"Table '{table_name}' recreated successfully.")
        except Exception as e:
            session.rollback()
            print(f"An error occurred while recreating the {table_name} table: {e}")
        finally:
            session.close()


    def push(self, max_workers=4, push_function=None):
        session = MarketSession()
        ticker_symbols = [r[0] for r in session.query(Ticker.ticker).all()]
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

    print("Pushing new price target news data...")
    db_pusher.push(push_function=db_pusher.push_stock_grade_news_threaded)
    print("Pushing new press releases data...")
    db_pusher.push(push_function=db_pusher.push_press_releases_threaded)
    print("Pushing new general news data...")
    db_pusher.push_general_news()


    



        

  
