from app.db.core.pull_fmp_data import FMP_API_DATA
from app.utils.decorators.tool_validation import log_simulation_data_range
from app.utils.token_count import get_token_count
from datetime import datetime
from typing import Optional
from app.core.agentic_framework.tool_lib.common.responses import success_response, error_response
from app.utils.tool_validator import ToolValidator
import pandas as pd
import numpy as np
from app.db.core.models.market_data_models import Ticker
from app.db.core.db_config import MarketSession
from app.utils.serialize_output import serialize_sqlalchemy_obj

import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

@log_simulation_data_range()
def get_ticker_peers(ticker: str, **kwargs) -> str:
    """Get peers for a ticker with additional data from Ticker table"""
    fmp = FMP_API_DATA()
    data = fmp.get_stock_peers(ticker)

    # Enrich peer data with Ticker table information
    with MarketSession() as session:
        enriched_peers = []

        for peer in data:
            peer_symbol = peer.get('symbol')
            ticker_info = session.query(Ticker).filter(Ticker.ticker == peer_symbol).first()

            enriched_peer = {}
            enriched_peer['symbol'] = peer_symbol

            # Add Ticker table data if available
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

            # Add price and market data
            enriched_peer['price'] = peer.get('price')
            enriched_peer['mktCap'] = peer.get('mktCap')

            # Add additional ticker metrics if available
            if ticker_info:
                enriched_peer['beta'] = ticker_info.beta
                enriched_peer['eps'] = ticker_info.eps
                enriched_peer['pe'] = ticker_info.pe
                enriched_peer['dollar_volume'] = float(ticker_info.dollar_volume) if ticker_info.dollar_volume else None
                enriched_peer['is_etf'] = ticker_info.is_etf
                # enriched_peer['is_actively_trading'] = ticker_info.is_actively_trading

            enriched_peers.append(enriched_peer)

    return success_response(enriched_peers)

if __name__ == "__main__":
    print(get_ticker_peers(ticker='AAPL'))

# Tool Schema Constants
GET_TICKER_PEERS_DESCRIPTION = (
    "Retrieve peer companies for a ticker with enriched fundamental and market data. "
    "Returns competitors within the same industry/sector with detailed metrics for comparative analysis.\n\n"
    "**Data Returned (per peer):**\n"
    "  - **symbol, companyName**: Ticker and company name\n"
    "  - **sector, industry, sub_industry**: GICS classifications for precise comparison\n"
    "  - **price, mktCap**: Current price and market capitalization\n"
    "  - **beta, eps, pe**: Risk (beta), profitability (EPS), valuation (P/E ratio)\n"
    "  - **dollar_volume**: Average daily dollar volume (liquidity measure)\n"
    "  - **is_actively_trading**: Current trading status\n\n"
    "**Use Cases:**\n"
    "  - **Relative Valuation**: Compare P/E ratios and market caps across peers\n"
    "  - **Portfolio Construction**: Build sector baskets or long/short pairs trades\n"
    "  - **Competitive Analysis**: Assess market positioning and competitive landscape\n"
    "  - **Liquidity Filtering**: Identify institutional-grade peers by dollar volume\n"
    "  - **Factor Analysis**: Analyze value (P/E), size (mktCap), volatility (beta) exposures\n\n"
    "**Key Insights:**\n"
    "  - **Valuation Dispersion**: Wide P/E spreads suggest mispricing opportunities\n"
    "  - **Liquidity Tiers**: Dollar volume differentiates tradeable vs illiquid names\n"
    "  - **Sector Purity**: Sub-industry matches identify closest business competitors\n"
    "  - **Beta Clustering**: Similar betas indicate comparable market sensitivity\n\n"
    "**Examples:**\n"
    "  get_ticker_peers(ticker='AAPL')   # Apple peers: MSFT, GOOGL, META, etc.\n"
    "  get_ticker_peers(ticker='JPM')    # JP Morgan peers: BAC, C, WFC, GS\n"
    "  get_ticker_peers(ticker='NVDA')   # Nvidia peers: AMD, INTC, AVGO"
)

GET_TICKER_PEERS_PARAMETERS = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": (
                "Ticker symbol to retrieve peer companies for. "
                "Examples: 'AAPL', 'MSFT', 'JPM', 'TSLA'"
            ),
        },
    },
    "required": ["ticker"],
}

GET_TICKER_PEERS_TOOL = {
    "name": "get_ticker_peers",
    "description": GET_TICKER_PEERS_DESCRIPTION,
    "parameters": GET_TICKER_PEERS_PARAMETERS,
    "function": get_ticker_peers,
}
