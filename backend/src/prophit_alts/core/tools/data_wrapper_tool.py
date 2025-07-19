from backend.src.repositories.price_data import get_price_data_daily
from datetime import datetime, timedelta
import pandas as pd
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.factor_calculations.growth_factor_calculations import GrowthFactors
from backend.src.calculations.factor_calculations.value_factor_calculations import ValueFactors
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.db.core.market_data_models import *
from backend.src.db.core.db_config import UserSession, MarketSession
from backend.src.utils.serialize_output import serialize_sqlalchemy_obj
from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.utils.token_count import get_token_count
import tiktoken
import json
import os
from backend.src.prophit_alts.core.tools.earnings_prompt import prompt

class ProphitAltsDataWrapper:
    def __init__(self, ticker: str = None):
        self.ticker = ticker
        self.price_data = None
        self.spy_data = None
        self.sector_data = None
        self.start_date = None
        self.end_date = None

        self.ticker = ticker.upper()
        
        if ticker:
            self._load_data()

    def _load_data(self):
        """Load price data for the ticker and benchmark data"""
        start_date_dt = datetime.now() - timedelta(days=365*2)
        end_date_dt = datetime.now()
        
        # Store datetime objects
        self.start_date = start_date_dt
        self.end_date = end_date_dt

        self.price_data = get_price_data_daily(self.ticker, start_date=start_date_dt, end_date=end_date_dt)
        self.spy_data = get_price_data_daily("spy", start_date=start_date_dt, end_date=end_date_dt)
        self.sector_data = get_price_data_daily("xlf", start_date=start_date_dt, end_date=end_date_dt) # --> THIS IS GOING TO CAUSE A PROBLEM, GET ACTUAL SECTOR DATA

    def retrieve_returns(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Calculate daily returns first
        daily_returns = CalculateTickerReturns(self.price_data).calculate_daily_total_returns() 
        
        # Convert to DataFrame with proper date index for resampling
        if 'date' in self.price_data.columns:
            # Create DataFrame with dates and daily returns
            returns_with_dates = pd.DataFrame({
                'date': self.price_data['date'].iloc[1:].reset_index(drop=True),
                'daily_return': daily_returns.values
            })
            returns_with_dates['date'] = pd.to_datetime(returns_with_dates['date'])
            returns_with_dates.set_index('date', inplace=True)
            
            # Resample to weekly frequency (Friday end-of-week)
            weekly_returns = (1 + returns_with_dates['daily_return']).resample('W-FRI').prod() - 1
            
            # Convert back to records format
            weekly_data = []
            for date, return_val in weekly_returns.items():
                weekly_data.append({
                    'week_ending': date.strftime('%Y-%m-%d'),
                    'weekly_total_return': round(return_val * 100, 2)  # Convert to percentage
                })
        else:
            # Fallback - just return daily data if no dates available
            weekly_data = [{'weekly_total_return': round(return_val * 100, 2)} for return_val in daily_returns.values]
        
        return weekly_data
    
    def retrieve_momentum_factors(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Extract the required Series from DataFrames
        price_series = self.price_data['close'] if 'close' in self.price_data.columns else None
        volume_series = self.price_data['volume'] if 'volume' in self.price_data.columns else None
        spy_price_series = self.spy_data['close'] if self.spy_data is not None and 'close' in self.spy_data.columns else None
        sector_price_series = self.sector_data['close'] if self.sector_data is not None and 'close' in self.sector_data.columns else None
        
        momentum_factors = MomentumFactors(
            price_series=price_series,
            volume_series=volume_series, 
            spy_price_series=spy_price_series,
            sector_price_series=sector_price_series
        )

        momentum_factors_dict = momentum_factors.calc_all().model_dump()
        
        # Convert to percentages and round to 2 decimal places (exclude MACD and RSI)
        exclude_from_percentage = {'macd_value', 'macd_signal', 'rsi'}
        
        for key, value in momentum_factors_dict.items():
            if value is not None:
                if key in exclude_from_percentage:
                    # Keep MACD and RSI in their original format, just round to 2 decimal places
                    momentum_factors_dict[key] = round(value, 2)
                else:
                    # Convert other metrics to percentages and round to 2 decimal places
                    momentum_factors_dict[key] = round(value * 100, 2)
        
        return momentum_factors_dict
    
    def retrieve_volatility_factors(self):
        if self.price_data is None or self.price_data.empty:
            raise ValueError("No price data available. Call run_all() with a ticker first.")
            
        # Extract the required Series from DataFrames
        price_series = self.price_data['close'] if 'close' in self.price_data.columns else None
        spy_price_series = self.spy_data['close'] if self.spy_data is not None and 'close' in self.spy_data.columns else None
        
        volatility_factors = VolatilityFactors(
            price_series=price_series,
            spy_price_series=spy_price_series
        )
        
        volatility_factors_dict = volatility_factors.calc_all().model_dump()
        return volatility_factors_dict

    def retrieve_news(self):
        with MarketSession() as session:
            news_data = session.query(StockNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockNews.publishedDate.desc()).limit(20).all()
            price_target_news = session.query(PriceTargetNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(PriceTargetNews.publishedDate.desc()).limit(10).all()
            stock_grade_news = session.query(StockGradeNews).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradeNews.publishedDate.desc()).limit(10).all()
            press_release_news = session.query(PressRelease).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(PressRelease.publishedDate.desc()).limit(10).all()

        news_data = [serialize_sqlalchemy_obj(news) for news in news_data]
        news_data_headlines = [news['title'] for news in news_data]
        news_data_text = [news['text'] for news in news_data]
        news_data_date = [news['publishedDate'] for news in news_data]

        price_target_news_data = [serialize_sqlalchemy_obj(news) for news in price_target_news]
        price_target_news_data_headlines = [news['newsTitle'] for news in price_target_news_data]
        price_target_news_data_analyst_company = [news['analystCompany'] for news in price_target_news_data]
        price_target_news_data_price_target = [news['priceTarget'] for news in price_target_news_data]
        price_target_news_data_date = [news['publishedDate'] for news in price_target_news_data]

        stock_grade_news_data = [serialize_sqlalchemy_obj(news) for news in stock_grade_news]
        stock_grade_news_data_headlines = [news['newsTitle'] for news in stock_grade_news_data]
        stock_grade_news_data_analyst_company = [news['gradingCompany'] for news in stock_grade_news_data]
        stock_grade_news_data_stock_grade = [news['newGrade'] for news in stock_grade_news_data]
        stock_grade_news_data_date = [news['publishedDate'] for news in stock_grade_news_data]

        press_release_news_data = [serialize_sqlalchemy_obj(news) for news in press_release_news]
        press_release_news_data_headlines = [news['title'] for news in press_release_news_data]
        press_release_news_data_text = [news['text'] for news in press_release_news_data]
        press_release_news_data_date = [news['publishedDate'] for news in press_release_news_data]

        news_dict = {
            "stock_news": {},
            "price_target_news": {},
            "stock_grade_news": {},
            "press_release_news": {}
        }

        for headline, text, date in zip(news_data_headlines, news_data_text, news_data_date):
            news_dict["stock_news"][headline] = {
                "text": text,
                "date": date
            }

        for headline, analyst_company, price_target, date in zip(price_target_news_data_headlines, price_target_news_data_analyst_company, price_target_news_data_price_target, price_target_news_data_date):
            news_dict["price_target_news"][headline] = {
                "analyst_company": analyst_company,
                "price_target": price_target,
                "date": date
            }

        for headline, analyst_company, stock_grade, date in zip(stock_grade_news_data_headlines, stock_grade_news_data_analyst_company, stock_grade_news_data_stock_grade, stock_grade_news_data_date):
            news_dict["stock_grade_news"][headline] = {
                "analyst_company": analyst_company,
                "stock_grade": stock_grade,
                "date": date
            }

        for headline, text, date in zip(press_release_news_data_headlines, press_release_news_data_text, press_release_news_data_date):
            news_dict["press_release_news"][headline] = {
                "text": text,
                "date": date
            }

        return news_dict
    
    def retrieve_and_summarize_earnings(self):
        model, client = openai_model_and_client()

        session = MarketSession()
        earnings_data = session.query(EarningsTranscript).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(EarningsTranscript.date.desc()).limit(4).all()
        earnings_data = [serialize_sqlalchemy_obj(earnings) for earnings in earnings_data]
        session.close()
        
        if len(earnings_data) == 0:
            # Return a structured response that's consistent with the LLM output format
            return {
                "status": "no_data",
                "message": f"No earnings transcripts available for {self.ticker}",
                "summary": None
            }
        
        else:
            earnings_dict = {}      
            for earnings in earnings_data:
                earnings_dict[earnings['date']] = {
                    'Quarter': earnings['period'],
                    'Year': earnings['year'],
                    'Earnings Call Transcript': earnings['content'],
                }
            
            # Add error handling for LLM call
            try:
                completions = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": json.dumps(earnings_dict)}
                    ]
                )
                completion_text = completions.choices[0].message.content
                
                return {
                    "status": "success",
                    "message": f"Analyzed {len(earnings_data)} earnings transcripts",
                    "summary": completion_text
                }
            except Exception as e:
                return {
                    "status": "error",
                    "message": f"Error analyzing earnings transcripts: {str(e)}",
                    "summary": None
                }
    
    def retrieve_analyst_estimates(self):
        session = MarketSession()
        analyst_estimates = session.query(AnalystEstimate).join(Ticker).filter(Ticker.ticker == self.ticker).filter(AnalystEstimate.date > datetime.now().date()).all()
        analyst_estimates = [serialize_sqlalchemy_obj(estimate) for estimate in analyst_estimates]
        session.close()

        return analyst_estimates
    
    def retrieve_fundamentals(self):
        fundamentals_dict = {}
        
        session = MarketSession()
        balance_sheet = session.query(BalanceSheet).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(BalanceSheet.date.desc()).limit(4).all()
        balance_sheet = [serialize_sqlalchemy_obj(balance_sheet) for balance_sheet in balance_sheet]

        income_statement = session.query(IncomeStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(IncomeStatement.date.desc()).limit(4).all()
        income_statement = [serialize_sqlalchemy_obj(income_statement) for income_statement in income_statement]

        cash_flow_statement = session.query(CashFlowStatement).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(CashFlowStatement.date.desc()).limit(4).all()
        cash_flow_statement = [serialize_sqlalchemy_obj(cash_flow_statement) for cash_flow_statement in cash_flow_statement]

        financial_ratios = session.query(FinancialRatio).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(FinancialRatio.date.desc()).limit(4).all()
        financial_ratios = [serialize_sqlalchemy_obj(financial_ratio) for financial_ratio in financial_ratios]

        session.close()

        for balance_sheet, income_statement, cash_flow_statement, financial_ratios in zip(balance_sheet, income_statement, cash_flow_statement, financial_ratios):
            fundamentals_dict[financial_ratios['date']] = {
                'balance_sheet': balance_sheet,
                'income_statement': income_statement,
                'cash_flow_statement': cash_flow_statement,
                'financial_ratios': financial_ratios
            }

        return fundamentals_dict
    
    def retrieve_grades_and_ratings(self):
        grades_and_ratings_dict = {}

        session = MarketSession()

        analyst_recommendations = session.query(AnalystRecommendation).join(Ticker).filter(Ticker.ticker == self.ticker).first()
        analyst_recommendations = serialize_sqlalchemy_obj(analyst_recommendations)

        stock_grades = session.query(StockGradesIndividual).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradesIndividual.date.desc()).limit(10).all()
        stock_grades = [serialize_sqlalchemy_obj(grade) for grade in stock_grades]

        stock_grades_summary = session.query(StockGradesSummary).join(Ticker).filter(Ticker.ticker == self.ticker).order_by(StockGradesSummary.date.desc()).limit(4).all()
        stock_grades_summary = [serialize_sqlalchemy_obj(grade) for grade in stock_grades_summary]

        session.close()

        grades_and_ratings_dict['analyst_recommendations'] = analyst_recommendations
        grades_and_ratings_dict['stock_grades'] = stock_grades
        grades_and_ratings_dict['stock_grades_summary'] = stock_grades_summary

        return grades_and_ratings_dict
    
    def run_all(self):
        """Load data for the given ticker and return all analysis results"""
        self._load_data() # --> make sure to load the data only once per ticker per tool call

        data = {
            'Factors and Returns': {
                "ticker": self.ticker,
                # "weekly_returns": self.retrieve_returns(),
                "momentum_factors": self.retrieve_momentum_factors(),
                "volatility_factors": self.retrieve_volatility_factors(),
                "growth_factors": GrowthFactors(self.ticker).calc_all().model_dump(),
                "value_factors": ValueFactors(self.ticker).calc_all().model_dump(),
                "quality_factors": QualityFactors(self.ticker).calc_all().model_dump(),
            },
            'News': self.retrieve_news(),
            'Earnings Transcript': self.retrieve_and_summarize_earnings(),
            'Analyst Estimates': self.retrieve_analyst_estimates(),
            'Fundamentals': self.retrieve_fundamentals(),
            'Grades and Ratings': self.retrieve_grades_and_ratings(),
        }
        
        return data


