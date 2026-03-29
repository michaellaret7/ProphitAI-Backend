"""
Portfolio Jobs Package

This package contains portfolio-related job modules:
- update.py: UpdatePortfolios class for updating portfolio NAVs
- monitor.py: MonitorPortfolio class for drift detection
- detections.py: Detection functions for allocation drift, drawdowns, correlations
- utils.py: Utility functions for ticker classification
- models.py: Data models for portfolio monitoring

Usage:
    from prophitai_data.jobs.portfolio import UpdatePortfolios

    with UpdatePortfolios() as updater:
        updater.update_portfolios()
"""

from prophitai_data.jobs.portfolio.update import UpdatePortfolios

__all__ = [
    'UpdatePortfolios',
]
