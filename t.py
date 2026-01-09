"""Script to print all unique sub-industries in the fixed income ETF industry."""

from sqlalchemy import select, distinct
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker


def get_fixed_income_sub_industries():
    """Query and print all unique sub-industries in fixed income ETFs."""
    with MarketSession() as session:
        query = (
            select(distinct(Ticker.sub_industry))
            .where(Ticker.sector == 'etf')
            .where(Ticker.industry == 'fixed_income_etfs')
            .where(Ticker.sub_industry.isnot(None))
            .order_by(Ticker.sub_industry)
        )
        result = session.execute(query)
        sub_industries = [row[0] for row in result]

        print(f"Found {len(sub_industries)} unique sub-industries in fixed income ETFs:\n")
        for sub_industry in sub_industries:
            print(f"  - {sub_industry}")


if __name__ == "__main__":
    get_fixed_income_sub_industries()
