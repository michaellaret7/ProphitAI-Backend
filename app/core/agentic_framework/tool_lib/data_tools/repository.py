import yaml
from app.repositories.ratings_data import get_stock_grades_individual, get_stock_grades_summary, get_ratings, get_analyst_recommendations, get_price_target_summary
from app.repositories.etf_data import get_etf_info, get_etf_holdings
from app.repositories.transcripts_data import get_earnings_transcripts, get_latest_transcript
from app.repositories.price_data import get_dividends_series
from datetime import datetime, timedelta
from app.repositories.news_data import get_press_releases, get_stock_news, get_price_target_news
from app.utils.decorators.database import with_session

def fetch_repository_data(ticker: str, data_type: str, limit: int | None = None) -> str:
    """Route to repository functions based on data_type.

    Supported data_type values:
      - press_releases, stock_news, price_target_news
      - grades_individual, grades_summary, ratings, analyst_recommendations
      - price_target_summary
      - etf_info, etf_holdings
      - earnings_transcripts, latest_transcript
      - dividends_series
    """
    try:
        t = (data_type or "").strip().lower()
        now = datetime.now()
        start_news = now - timedelta(days=180)
        start_divs = now - timedelta(days=365)

        if t in ["press_releases", "press-release", "press"]:
            data = get_press_releases(ticker, start=start_news, end=now, limit=50, ascending=False)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t in ["stock_news", "news"]:
            data = get_stock_news(ticker, start=start_news, end=now, limit=50, ascending=False)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t in ["price_target_news", "pt_news"]:
            data = get_price_target_news(ticker, start=start_news, end=now, limit=50, ascending=False)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)

        if t in ["grades_individual", "grades_detail"]:
            data = get_stock_grades_individual(ticker, start=start_news, end=now)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t in ["grades_summary", "grades"]:
            data = get_stock_grades_summary(ticker, start=start_news, end=now)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t == "ratings":
            data = get_ratings(ticker, start=start_news, end=now)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t in ["analyst_recommendations", "analyst_recomendations", "recommendations"]:
            data = get_analyst_recommendations(ticker, start=start_news, end=now)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t == "price_target_summary":
            data = get_price_target_summary(ticker)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)

        if t == "etf_info":
            data = get_etf_info(ticker)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t == "etf_holdings":
            data = get_etf_holdings(ticker)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)

        if t == "earnings_transcripts":
            # Default last 2 years; honor optional limit for number of transcripts
            data = get_earnings_transcripts(
                ticker,
                start_year=now.year - 2,
                end_year=now.year,
                limit=limit,
            )
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)
        if t == "latest_transcript":
            data = get_latest_transcript(ticker)
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)

        if t == "dividends_series":
            s = get_dividends_series(ticker, start_divs, now)
            items = [{"date": str(idx.date()), "amount": float(val)} for idx, val in s.items()]
            data = {"ticker": ticker.upper(), "count": len(items), "items": items}
            return yaml.dump({"success": True, "data": data}, default_flow_style=False)

        return yaml.dump({"success": False, "error": f"Unknown data_type: {data_type}"}, default_flow_style=False)
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)}, default_flow_style=False)


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
