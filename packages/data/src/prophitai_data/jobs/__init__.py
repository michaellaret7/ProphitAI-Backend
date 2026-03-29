"""
Database Update Jobs Package

This package contains all database update jobs for ProphitAI.
Jobs are organized by domain:

- market/: Ticker and price data updates
- fundamentals/: Financial statements, analyst data, news, ETF data
- macro/: Commodity prices, economic indicators, calendar, treasury rates
- portfolio/: Portfolio value updates

BaseUpdater provides common utilities for safe type conversion and progress tracking.
"""

from prophitai_data.jobs.base import BaseUpdater

__all__ = [
    'BaseUpdater',
]
