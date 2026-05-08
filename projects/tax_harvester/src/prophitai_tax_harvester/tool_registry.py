"""Tool registry for the Tax Harvester agent.

Curated minimal kit for the experimental tax-loss harvesting agent:
1. Portfolio input — the xlsx workbook reader (canonical input).
2. Wash-sale rule research — IRS source citation (non-negotiable per
   system prompt).
3. Replacement discovery — ETF screener + single-stock peer lookup.
4. Substantially-identical check — ETF metadata + holdings basket
   comparison.
5. Exposure preservation check — pairwise correlation between the
   original and the proposed replacement.
"""

from typing import Callable, List

# ================================
# --> Portfolio input (xlsx tax-lot workbook)
# ================================
from prophitai_tax_harvester.tools.read_portfolio_xlsx import read_portfolio_xlsx

# ================================
# --> Wash-sale rule research (IRS / tax docs)
# ================================
from prophitai_tools.research.tax_research import tax_research_search

# ================================
# --> Replacement discovery
# ================================
from prophitai_tools.screener.etf_screener import etf_screener
from prophitai_tools.ticker.info.peers import get_ticker_peers

# ================================
# --> Substantially-identical check (ETF metadata + holdings basket)
# ================================
from prophitai_tools.ticker.info.description import get_etf_info
from prophitai_tools.ticker.info.etf_holdings import get_etf_holdings

# ================================
# --> Replacement diligence (fundamentals, performance, risk)
# ================================
from prophitai_tools.ticker.fundamentals.statements import get_ticker_fundamental_data
from prophitai_tools.ticker.fundamentals.ttm_ratios import get_ratios_ttm
from prophitai_tools.ticker.performance import ticker_performance
from prophitai_tools.ticker.risk import ticker_risk

# ================================
# --> Event awareness (news for harvest / replacement candidates)
# ================================
from prophitai_tools.news.ticker_news import get_ticker_news

# ================================
# --> Exposure preservation (pairwise correlation)
# ================================
from prophitai_tools.portfolio.correlation import portfolio_correlation


TAX_HARVESTER_TOOLS: List[Callable] = [
    # portfolio input
    read_portfolio_xlsx,
    # wash-sale research
    tax_research_search,
    # replacement discovery
    etf_screener,
    get_ticker_peers,
    # substantially-identical check
    get_etf_info,
    get_etf_holdings,
    # replacement diligence
    get_ticker_fundamental_data,
    get_ratios_ttm,
    ticker_performance,
    ticker_risk,
    # event awareness
    get_ticker_news,
    # exposure preservation
    portfolio_correlation,
]
