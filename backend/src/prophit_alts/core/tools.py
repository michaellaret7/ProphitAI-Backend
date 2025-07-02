from backend.src.repositories.market_data.ticker_repository import get_ticker_price_data
from datetime import datetime, timedelta
from pandas import DataFrame
import pandas as pd
import re
from backend.src.calculations.returns_calculations.ticker_returns_calculations import CalculateTickerReturns
from backend.src.calculations.factor_calculations.momentum_factor_calculations import MomentumFactors
from backend.src.calculations.factor_calculations.volatility_factor_calculations import VolatilityFactors
from backend.src.calculations.factor_calculations.growth_factor_calculations import GrowthFactors
from backend.src.calculations.factor_calculations.value_factor_calculations import ValueFactors
from backend.src.calculations.factor_calculations.quality_factor_calculations import QualityFactors
from backend.src.repositories.fundamental_data.fundamental_repository import FundamentalDataRepository
from backend.src.utils.choose_model_and_client import perplexity_model_and_client

class ProphitAltsDataWrapper:
    def __init__(self, ticker: str = None):
        self.ticker = ticker
        self.price_data = None
        self.spy_data = None
        self.sector_data = None
        self.start_date = None
        self.end_date = None
        
        if ticker:
            self._load_data()

    def _load_data(self):
        """Load price data for the ticker and benchmark data"""
        start_date_dt = datetime.now() - timedelta(days=365*2)
        end_date_dt = datetime.now()
        
        # Convert datetime objects to ISO format strings for the cached_ticker_repository
        self.start_date = start_date_dt.strftime('%Y-%m-%d')
        self.end_date = end_date_dt.strftime('%Y-%m-%d')

        self.price_data = get_ticker_price_data(self.ticker, start_date=self.start_date, end_date=self.end_date, interval="1d")
        self.spy_data = get_ticker_price_data("spy", start_date=self.start_date, end_date=self.end_date, interval="1d")
        self.sector_data = get_ticker_price_data("xlf", start_date=self.start_date, end_date=self.end_date, interval="1d") # --> THIS IS GOING TO CAUSE A PROBLEM, GET ACTUAL SECTOR DATA

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
    
    def run_all(self):
        """Load data for the given ticker and return all analysis results"""
        self._load_data() # --> make sure to load the data only once per ticker per tool call

        data = {
            "ticker": self.ticker,
            "weekly_returns": self.retrieve_returns(),
            "momentum_factors": self.retrieve_momentum_factors(),
            "volatility_factors": self.retrieve_volatility_factors(),

            "growth_factors": GrowthFactors(self.ticker).calc_all().model_dump(),
            "value_factors": ValueFactors(self.ticker).calc_all().model_dump(),
            "quality_factors": QualityFactors(self.ticker).calc_all().model_dump(),

            # "financial_ratios": FundamentalDataRepository().fetch_financial_metrics(self.ticker),
            # "fundamental_estimates": FundamentalDataRepository().fetch_fundamental_estimates(self.ticker)
        }
        
        return data

class AgentSearchEngine:
    def perplexity_free_search(self, query: str):
        model, client = perplexity_model_and_client() # --> initialize model and client for perplexity

        system_prompt = """
        <Role>
        Act as an expert researcher in market research and analysis.
        You have 30 years of experience being a research analyst at the top investment banks and hedge funds in the world
        </Role>

        <Instructions>
        You will be given a query and you will need to research the query and return the most relevant and new information.
        You will need to use the latest data and information to answer the query.
        You will need to use the latest news and information to answer the query.
        You will need to use the latest research and information to answer the query.
        You will need to use the latest analysis and information to answer the query.
        You will need to use the latest insights and information to answer the query.
        </Instructions>

        <Rules>
        You must be as descriptive, informative and detailed as possible.
        You must be as accurate and factual as possible.
        You must be as up to date and relevant as possible.
        Do extensive research on the query and ONLY retrieve information from the top and most reputable sources.
        You have no output token limit.
        </Rules>

        <What to search for>
        - Macro economic data
        - Industry data
        - Company data
        - News
        - Research
        - Insights
        - Analyst Estimates 
        - Analyst Reports
        - Economic Forecasts
        - Economic Data
        - Economic Indicators
        </What to search for>
        """

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            # chat completion with streaming
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=0.7
            )

            content = response.choices[0].message.content
            cleaned_content = re.sub(r'\[\d+\]', '', content) # --> clean up the content to remove the thinking process tags

            return cleaned_content
        
        except Exception as e:
            print(f"Error: {e}")
            return None

if __name__ == "__main__":
    agent_search_engine = AgentSearchEngine()
    print(agent_search_engine.perplexity_free_search("How did the retail sector perform during the liberation day tariff decision?"))
