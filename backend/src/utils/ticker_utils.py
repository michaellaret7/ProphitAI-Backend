import os
from datetime import datetime, timedelta
from openai import OpenAI
import yfinance as yf
from dotenv import load_dotenv
from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.utils.determine_etf import is_etf_ticker

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

def get_most_recent_price(ticker):
    """Get just the most recent close price for a ticker"""
    
    # Import inside function to avoid circular import
    from backend.src.repositories.market_data.etf_price_repository import ETFPriceDataRepository
    from backend.src.repositories.market_data.equity_price_repository import EquityPriceDataRepository
    
    # Use last 7 days to ensure we catch the most recent trading day
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    if is_etf_ticker(ticker):
        etf_data_repo = ETFPriceDataRepository()
        data = etf_data_repo.fetch_etf_price_data(ticker, start_date=start_date, end_date=end_date, interval="1d")
    else:
        equity_data_repo = EquityPriceDataRepository()
        data = equity_data_repo.fetch_equity_price_data(ticker, start_date=start_date, end_date=end_date, interval="1d")
    
    if not data.empty:
        return data['close'].iloc[-1]
    return None