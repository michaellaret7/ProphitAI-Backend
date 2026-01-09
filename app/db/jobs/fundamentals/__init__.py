"""
Fundamentals Update Package

This package contains modular updaters for fundamental data:
- FinancialStatementsUpdater: Balance sheets, cash flows, income statements, ratios
- AnalystDataUpdater: Estimates, grades, ratings, recommendations, price targets
- NewsDataUpdater: Press releases, stock news, price target news, grade news, transcripts
- ETFDataUpdater: ETF holdings, ETF info, dividends
- FundamentalsUpdater: Orchestrator that combines all sub-updaters

Usage:
    from app.db.jobs.fundamentals import FundamentalsUpdater

    updater = FundamentalsUpdater()
    updater.update_all_fundamentals(max_workers=5)
"""

from app.db.jobs.fundamentals.financial_statements import FinancialStatementsUpdater
from app.db.jobs.fundamentals.analyst_data import AnalystDataUpdater
from app.db.jobs.fundamentals.news_data import NewsDataUpdater
from app.db.jobs.fundamentals.etf_data import ETFDataUpdater
from app.db.jobs.fundamentals.orchestrator import FundamentalsUpdater

__all__ = [
    'FinancialStatementsUpdater',
    'AnalystDataUpdater',
    'NewsDataUpdater',
    'ETFDataUpdater',
    'FundamentalsUpdater',
]
