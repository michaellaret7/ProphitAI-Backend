"""
Database Update Jobs Package

This package contains all database update jobs for ProphitAI.
Jobs are organized by domain:

- market_data/: Ticker and price data updates
- fundamentals/: Financial statements, analyst data, news, ETF data
- macro/: Commodity prices, economic indicators, calendar, treasury rates
- screeners/: ETF and equity screener updates
- portfolio/: Portfolio value updates
- utils/: Utility scripts (timezone fixes, etc.)
- runs/: Job orchestration scripts (EOD, intraday, etc.)

BaseUpdater provides common utilities for safe type conversion and progress tracking.
"""

from app.db.jobs.base_updater import BaseUpdater

__all__ = [
    'BaseUpdater',
]
