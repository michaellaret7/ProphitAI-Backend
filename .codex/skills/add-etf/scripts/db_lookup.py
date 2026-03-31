"""DB lookup helpers for the add-etf skill."""

import sys
import os

# Reason: Ensure the project root is on sys.path so imports resolve
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Ticker


# ================================
# --> Helper funcs
# ================================

def check_ticker_exists(ticker: str) -> dict:
    """
    Check if a ticker already exists in the database.

    Args:
        ticker: Ticker symbol to check.

    Returns:
        Dict with 'exists' bool and classification details if found.
    """
    with MarketSession() as session:
        row = session.query(Ticker).filter(Ticker.ticker == ticker.upper()).first()
        if row:
            return {
                "exists": True,
                "ticker": row.ticker,
                "is_etf": row.is_etf,
                "sector": row.sector,
                "industry": row.industry,
                "sub_industry": row.sub_industry,
            }
        return {"exists": False}


def get_etf_classifications() -> dict:
    """
    Pull all distinct sector, industry, and sub_industry values
    from the tickers table for ETFs only.

    Returns:
        Dict with sorted lists of sectors, industries, and sub_industries.
    """
    with MarketSession() as session:
        sectors = sorted(
            {r[0] for r in session.query(Ticker.sector).distinct().filter(Ticker.is_etf == True).all() if r[0]}
        )
        industries = sorted(
            {r[0] for r in session.query(Ticker.industry).distinct().filter(Ticker.is_etf == True).all() if r[0]}
        )
        sub_industries = sorted(
            {r[0] for r in session.query(Ticker.sub_industry).distinct().filter(Ticker.is_etf == True).all() if r[0]}
        )

    return {
        "sectors": sectors,
        "industries": industries,
        "sub_industries": sub_industries,
    }


# ================================
# --> CLI entry point
# ================================

if __name__ == "__main__":
    import json

    action = sys.argv[1] if len(sys.argv) > 1 else None

    if action == "check":
        ticker = sys.argv[2] if len(sys.argv) > 2 else None
        if not ticker:
            print("Usage: python db_lookup.py check <TICKER>")
            sys.exit(1)
        print(json.dumps(check_ticker_exists(ticker), indent=2))

    elif action == "classifications":
        print(json.dumps(get_etf_classifications(), indent=2))

    else:
        print("Usage: python db_lookup.py [check <TICKER> | classifications]")
        sys.exit(1)
