from app.repositories.ratings_data import get_stock_grades_individual, get_stock_grades_summary, get_ratings, get_analyst_recommendations, get_price_target_summary
from app.repositories.etf_data import get_etf_info, get_etf_holdings
from app.repositories.transcripts_data import get_earnings_transcripts, get_latest_transcript
from app.repositories.price_data import get_dividends_series
from datetime import datetime, timedelta
from app.repositories.news_data import get_press_releases, get_stock_news, get_price_target_news
from app.utils.decorators.database import with_session

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


# Tool Schema Constants
FETCH_TICKER_REPOSITORY_DATA_DESCRIPTION = (
    "Fetch auxiliary data for a ticker. Supported data_type: "
    "'press_releases','stock_news','price_target_news','grades_individual','grades_summary',"
    "'ratings','analyst_recommendations','price_target_summary','etf_info','etf_holdings',"
    ",'dividends_series'.\n\n"
    "Example: fetch_ticker_repository_data(ticker='AAPL', data_type='stock_news', limit=3)"
)

FETCH_TICKER_REPOSITORY_DATA_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Ticker symbol (e.g., 'AAPL').",
        },
        "data_type": {
            "type": "string",
            "description": "Type of data to fetch.",
            "enum": [
                "press_releases",
                "stock_news",
                "price_target_news",
                "grades_individual",
                "grades_summary",
                "ratings",
                "analyst_recommendations",
                "price_target_summary",
                "etf_info",
                "etf_holdings",
                "dividends_series"
            ]
        },
        "limit": {
            "type": "integer",
            "description": "Optional max number of items (applies to dividends_series).",
            "minimum": 1,
            "maximum": 4
        }
    },
    "required": ["ticker", "data_type"],
}

FETCH_TICKER_REPOSITORY_DATA_TOOL = {
    "name": "fetch_ticker_repository_data",
    "description": FETCH_TICKER_REPOSITORY_DATA_DESCRIPTION,
    "parameters": FETCH_TICKER_REPOSITORY_DATA_PARAMETERS,
    "function": fetch_repository_data,
}
