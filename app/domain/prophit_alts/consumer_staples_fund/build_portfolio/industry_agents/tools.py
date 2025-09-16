from app.core.calculations.sectors.industry import *
from app.core.calculations.sectors.sub_industry import *
from app.core.calculations.factors.growth import GrowthFactors
from app.core.calculations.factors.value import ValueFactors
from app.core.calculations.factors.momentum import MomentumFactors
from app.core.calculations.factors.quality import QualityFactors
from app.core.calculations.factors.volatility import VolatilityFactors
from app.core.calculations.core.data_service import DataService
from app.core.calculations.returns.calculator import ReturnsCalculator
from app.repositories.fundamental_data import get_fundamental_data
from app.repositories.news_data import get_press_releases, get_stock_news, get_price_target_news
from app.repositories.ratings_data import (
    get_stock_grades_individual,
    get_stock_grades_summary,
    get_ratings,
    get_analyst_recommendations,
    get_price_target_summary,
)
from app.repositories.etf_data import get_etf_info, get_etf_holdings
from app.repositories.transcripts_data import get_earnings_transcripts, get_latest_transcript
from app.repositories.price_data import get_dividends_series
from datetime import datetime, timedelta
from app.db.core.db_config import MarketSession
from app.db.core.market_data_models import Ticker
from typing import List

def get_weekly_returns(ticker: str):
    """Get weekly returns for the last year for a given ticker."""
    ds = DataService()
    end_date = datetime.now()
    start_date = end_date - timedelta(days=252)
    
    # Get price data for the ticker
    price_data = ds.get_price_data(ticker, start_date, end_date)
    if price_data is None or price_data.frame.empty:
        return {"error": f"No price data available for {ticker}"}
    
    # Get closing prices
    close_prices = price_data.frame['close']
    
    # Resample to weekly and calculate returns
    weekly_prices = close_prices.resample('W').last()
    weekly_returns = weekly_prices.pct_change().dropna()
    
    # Convert to dictionary with string dates and format as percentages
    return {
        "ticker": ticker,
        "weekly_returns": {str(date.date()): f"{round(ret * 100, 2)}%" for date, ret in weekly_returns.items()},
        "total_weeks": len(weekly_returns),
        "average_weekly_return": f"{round(weekly_returns.mean() * 100, 2)}%" if not weekly_returns.empty else "0%"
    }

def calculate_ticker_factors(ticker: str, factor: str):
    """Calculate all factor metrics for a given ticker and factor type."""
    # Growth, Value, and Quality factors take ticker string directly
    if factor in ["growth", "value", "quality"]:
        if factor == "growth":
            return GrowthFactors(ticker).calc_all()
        elif factor == "value":
            return ValueFactors(ticker).calc_all()
        else:  # quality
            return QualityFactors(ticker).calc_all()
    
    # Momentum and Volatility factors need price series
    elif factor in ["momentum", "volatility"]:
        ds = DataService()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=504)  # ~2 years of data
        
        # Get price data for ticker (and SPY for market-relative metrics)
        price_data = ds.get_price_data(ticker, start_date, end_date)
        if price_data is None or price_data.frame.empty:
            return {"error": f"No price data available for {ticker}"}
        
        price_series = price_data.frame['close']
        
        # Get SPY data for both momentum and volatility
        spy_data = ds.get_price_data("SPY", start_date, end_date)
        spy_prices = spy_data.frame['close'] if spy_data and not spy_data.frame.empty else None
        
        if factor == "momentum":
            # Get additional data for momentum calculations
            volume_series = price_data.frame.get('volume', None)
            
            # Get dividends if available
            try:
                divs = ds.get_dividends(ticker, start_date, end_date).series
                divs = divs.reindex(price_series.index).fillna(0.0)
            except Exception:
                divs = None
            
            return MomentumFactors(
                price_series=price_series,
                volume_series=volume_series,
                market_price_series=spy_prices,
                dividends_series=divs
            ).calc_all()
        else:  # volatility
            return VolatilityFactors(price_series, spy_price_series=spy_prices).calc_all()
    
    else:
        raise ValueError(f"Unknown factor: {factor}")

def fetch_repository_data(ticker: str, data_type: str, limit: int | None = None):
    """Route to repository functions based on data_type.

    Supported data_type values:
      - press_releases, stock_news, price_target_news
      - grades_individual, grades_summary, ratings, analyst_recommendations
      - price_target_summary
      - etf_info, etf_holdings
      - earnings_transcripts, latest_transcript
      - dividends_series
    """
    t = (data_type or "").strip().lower()
    now = datetime.now()
    start_news = now - timedelta(days=180)
    start_divs = now - timedelta(days=365)

    if t in ["press_releases", "press-release", "press"]:
        return get_press_releases(ticker, start=start_news, end=now, limit=50, ascending=False)
    if t in ["stock_news", "news"]:
        return get_stock_news(ticker, start=start_news, end=now, limit=50, ascending=False)
    if t in ["price_target_news", "pt_news"]:
        return get_price_target_news(ticker, start=start_news, end=now, limit=50, ascending=False)

    if t in ["grades_individual", "grades_detail"]:
        return get_stock_grades_individual(ticker, start=start_news, end=now)
    if t in ["grades_summary", "grades"]:
        return get_stock_grades_summary(ticker, start=start_news, end=now)
    if t == "ratings":
        return get_ratings(ticker, start=start_news, end=now)
    if t in ["analyst_recommendations", "analyst_recomendations", "recommendations"]:
        return get_analyst_recommendations(ticker, start=start_news, end=now)
    if t == "price_target_summary":
        return get_price_target_summary(ticker)

    if t == "etf_info":
        return get_etf_info(ticker)
    if t == "etf_holdings":
        return get_etf_holdings(ticker)

    if t == "earnings_transcripts":
        # Default last 2 years; honor optional limit for number of transcripts
        return get_earnings_transcripts(
            ticker,
            start_year=now.year - 2,
            end_year=now.year,
            limit=limit,
        )
    if t == "latest_transcript":
        return get_latest_transcript(ticker)

    if t == "dividends_series":
        s = get_dividends_series(ticker, start_divs, now)
        items = [{"date": str(idx.date()), "amount": float(val)} for idx, val in s.items()]
        return {"ticker": ticker.upper(), "count": len(items), "items": items}

    return {"error": f"Unknown data_type: {data_type}"}

def get_eligible_tickers(industry: str):
    """Get the eligible tickers for a given industry."""
    market_session = MarketSession()
    industry = industry.lower()
    tickers = market_session.query(Ticker).filter(Ticker.industry == industry, Ticker.market_cap > 600_000_000).all()
    market_session.close()
    return [ticker.ticker for ticker in tickers]

def get_base_ticker_info(tickers: List[str]):
    """Get the base ticker info for a given list of tickers."""
    market_session = MarketSession()
    ticker_objects = market_session.query(Ticker).filter(Ticker.ticker.in_(tickers)).all()
    market_session.close()
    
    # Convert SQLAlchemy objects to dictionaries
    result = []
    for ticker in ticker_objects:
        ticker_dict = {
            'ticker': ticker.ticker,
            'sector': ticker.sector,
            'industry': ticker.industry,
            'sub_industry': ticker.sub_industry,
            'is_etf': ticker.is_etf,
            'price': ticker.price,
            'market_cap': float(ticker.market_cap) if ticker.market_cap else None,
            'avg_volume': float(ticker.avg_volume) if ticker.avg_volume else None,
            'eps': ticker.eps,
            'pe': ticker.pe,
            'dollar_volume': float(ticker.dollar_volume) if ticker.dollar_volume else None,
        }
        result.append(ticker_dict)
    
    return result


if __name__ == "__main__":
    print(get_base_ticker_info(["AAPL", "MSFT", "KO"]))