import os
from datetime import datetime, timedelta
from openai import OpenAI
import yfinance as yf
from dotenv import load_dotenv
from app.utils.choose_model_and_client import openai_model_and_client
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import *
from app.utils.decorators.database import with_session
from app.utils.serialize_output import serialize_sqlalchemy_obj
from app.utils.decorators.database import with_session

# Load environment variables from .env file
load_dotenv()

# Load OpenAI credentials from environment

model, client = openai_model_and_client('gpt-4o-mini')

def name_to_ticker(company_name):
    """
    Convert company name to ticker symbol using OpenAI and yfinance fallback.

    Args:
        company_name (str): Company name or approximate ticker

    Returns:
        str: Ticker symbol
    """
    # If input already looks like a ticker (all caps, 1-5 chars), return it
    if company_name.isupper() and 1 <= len(company_name) <= 5:
        return company_name

    # Use OpenAI to identify the ticker
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a financial assistant that converts company names to their stock ticker symbols. Respond ONLY with the ticker symbol in uppercase, nothing else."
                },
                {
                    "role": "user",
                    "content": f"What is the stock ticker symbol for {company_name}?"
                }
            ],
            temperature=0,
            max_tokens=30
        )
        ticker = response.choices[0].message.content.strip().upper()
        if ticker and len(ticker) <= 5 and ticker.isalpha():
            return ticker
    except Exception:
        pass

    # Fallback to yfinance if OpenAI fails
    try:
        info = yf.Ticker(company_name).info
        if 'symbol' in info:
            return info['symbol'].upper()
    except Exception:
        pass

    # Last resort: return uppercase input
    return company_name.upper() 

@with_session('market')
def get_most_recent_price(ticker, session=None):
    """Get just the most recent close price for a ticker"""
    ticker = ticker.upper()

    price = session.query(Ticker).filter(Ticker.ticker == ticker).first()
    price = price.price
    
    return price

@with_session('market')
def get_eligible_tickers(industry: str, market_cap: int, price: int = None, dollar_volume: int = None, session=None):
   ticker_list = []

   if price is None:
      tickers = session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > market_cap).all()
   else:
      tickers = session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > market_cap, Ticker.price > price).all()

   if dollar_volume is not None and price is not None:
      tickers = session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > market_cap, Ticker.dollar_volume > dollar_volume, Ticker.price > price).all()
      
   tickers = [serialize_sqlalchemy_obj(ticker) for ticker in tickers]

   for ticker in tickers:
      ticker_list.append(ticker['ticker'])

   return ticker_list

