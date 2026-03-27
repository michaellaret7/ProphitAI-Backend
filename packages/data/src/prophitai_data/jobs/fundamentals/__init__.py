"""
Fundamentals Update Package

This package contains modular updaters for fundamental data:
- FinancialStatementsUpdater: Balance sheets, cash flows, income statements, ratios
- AnalystDataUpdater: Estimates, grades, ratings, recommendations, price targets
- NewsDataUpdater: Press releases, stock news, price target news, grade news, transcripts
- ETFDataUpdater: ETF holdings, ETF info, dividends
- FundamentalsUpdater: Orchestrator that combines all sub-updaters

Usage:
    from prophitai_data.jobs.fundamentals import FundamentalsUpdater

    updater = FundamentalsUpdater()
    updater.update_all_fundamentals(max_workers=5)
"""

from prophitai_data.jobs.fundamentals.financial_statements import FinancialStatementsUpdater
from prophitai_data.jobs.fundamentals.analyst_data import AnalystDataUpdater
from prophitai_data.jobs.fundamentals.news_data import NewsDataUpdater
from prophitai_data.jobs.fundamentals.etf_data import ETFDataUpdater
from prophitai_data.jobs.fundamentals.orchestrator import FundamentalsUpdater

__all__ = [
    'FinancialStatementsUpdater',
    'AnalystDataUpdater',
    'NewsDataUpdater',
    'ETFDataUpdater',
    'FundamentalsUpdater',
]
