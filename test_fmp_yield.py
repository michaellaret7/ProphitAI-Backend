"""
Fetch dividend yield TTM for all ETFs and update ETFScreener table.
"""
from app.db.core.pull_fmp_data import FMP_API_DATA
from app.db.core.db_config import MarketSession
from app.db.core.models.market_data_models import Ticker, ETFScreener


def get_etf_tickers() -> list[dict]:
    """Fetch all ETF tickers from ETFScreener table."""
    with MarketSession() as session:
        results = (
            session.query(ETFScreener.ticker_id, Ticker.ticker)
            .join(Ticker, ETFScreener.ticker_id == Ticker.id)
            .all()
        )
        return [{'ticker_id': r.ticker_id, 'ticker': r.ticker} for r in results]


def fetch_and_update_dividend_yields():
    """Fetch dividend yield TTM for all ETFs and update database."""
    fmp = FMP_API_DATA()
    etfs = get_etf_tickers()

    print(f"Found {len(etfs)} ETFs in screener table")

    updated = 0
    failed = 0

    with MarketSession() as session:
        for etf in etfs:
            ticker = etf['ticker']
            ticker_id = etf['ticker_id']

            try:
                ratios = fmp.get_ratios_ttm(ticker)

                if not ratios or len(ratios) == 0:
                    print(f"  {ticker}: No ratios data")
                    failed += 1
                    continue

                dividend_yield = ratios[0].get('dividendYielTTM')

                if dividend_yield is None:
                    print(f"  {ticker}: No dividend yield data")
                    failed += 1
                    continue

                # Update database
                session.query(ETFScreener).filter(
                    ETFScreener.ticker_id == ticker_id
                ).update({'dividend_yield_ttm': dividend_yield})

                print(f"  {ticker}: dividend_yield_ttm = {dividend_yield:.4f}")
                updated += 1

            except Exception as e:
                print(f"  {ticker}: Error - {e}")
                failed += 1

        session.commit()

    print(f"\nUpdated {updated} ETFs, {failed} failed")


if __name__ == "__main__":
    fetch_and_update_dividend_yields()
