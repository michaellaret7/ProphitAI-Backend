"""Ticker peers tools.

Provides tools for retrieving peer companies with enriched
fundamental and market data for comparative analysis.
"""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_data.clients.fmp import FMP_API_DATA
from prophitai_data.db.config import MarketSession
from prophitai_data.db.models.market import Ticker


# ================================
# --> Tools
# ================================

@agent_tool(name="get_ticker_peers", category="ticker_info")
def get_ticker_peers(
    ticker: str,
) -> str:
    """
    Retrieve peer companies for a ticker with enriched fundamental and market data.

    Returns competitors within the same industry/sector with detailed metrics
    for comparative analysis.

    **Data Returned (per peer):**
    - symbol, companyName: Ticker and company name
    - description: Business overview
    - sector, industry, sub_industry: GICS classifications for precise comparison
    - price, mktCap: Current price and market capitalization
    - beta, eps, pe: Risk (beta), profitability (EPS), valuation (P/E ratio)
    - dollar_volume: Average daily dollar volume (liquidity measure)
    - is_etf: Whether the peer is an ETF

    **Use Cases:**
    - Relative Valuation: Compare P/E ratios and market caps across peers
    - Portfolio Construction: Build sector baskets or long/short pairs trades
    - Competitive Analysis: Assess market positioning and competitive landscape
    - Liquidity Filtering: Identify institutional-grade peers by dollar volume
    - Factor Analysis: Analyze value (P/E), size (mktCap), volatility (beta) exposures

    **Key Insights:**
    - Valuation Dispersion: Wide P/E spreads suggest mispricing opportunities
    - Liquidity Tiers: Dollar volume differentiates tradeable vs illiquid names
    - Sector Purity: Sub-industry matches identify closest business competitors
    - Beta Clustering: Similar betas indicate comparable market sensitivity

    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL', 'JPM', 'NVDA')

    Returns:
        List of peer companies with enriched fundamental data

    Examples:
        get_ticker_peers(ticker='AAPL')
        >>> {"success": True, "data": [{"symbol": "MSFT", "companyName": "Microsoft Corp", ...}]}

        get_ticker_peers(ticker='JPM')
        >>> {"success": True, "data": [{"symbol": "BAC", ...}, {"symbol": "C", ...}]}

    Raises:
        Exception: If ticker is invalid or data retrieval fails
    """
    try:
        fmp = FMP_API_DATA()
        data = fmp.get_stock_peers(ticker.upper())

        with MarketSession() as session:
            enriched_peers = []

            for peer in data:
                peer_symbol = peer.get('symbol')
                ticker_info = session.query(Ticker).filter(Ticker.ticker == peer_symbol).first()

                enriched_peer = {'symbol': peer_symbol}

                if ticker_info:
                    enriched_peer['companyName'] = ticker_info.ticker_name
                    enriched_peer['description'] = ticker_info.ticker_description
                    enriched_peer['sector'] = ticker_info.sector
                    enriched_peer['industry'] = ticker_info.industry
                    enriched_peer['sub_industry'] = ticker_info.sub_industry
                else:
                    enriched_peer['companyName'] = None
                    enriched_peer['description'] = None
                    enriched_peer['sector'] = None
                    enriched_peer['industry'] = None
                    enriched_peer['sub_industry'] = None

                enriched_peer['price'] = peer.get('price')
                enriched_peer['mktCap'] = peer.get('mktCap')

                if ticker_info:
                    enriched_peer['beta'] = ticker_info.beta
                    enriched_peer['eps'] = ticker_info.eps
                    enriched_peer['pe'] = ticker_info.pe
                    enriched_peer['dollar_volume'] = float(ticker_info.dollar_volume) if ticker_info.dollar_volume else None
                    enriched_peer['is_etf'] = ticker_info.is_etf

                enriched_peers.append(enriched_peer)

        return success_response(enriched_peers)
    except Exception as e:
        return error_response(f"Failed to retrieve peers for {ticker}: {str(e)}")


# ================================
# --> Standalone testing
# ================================

if __name__ == "__main__":
    print(get_ticker_peers.tool)
