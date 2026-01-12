"""
Portfolio Jobs Package

This package contains portfolio-related job modules:
- update.py: UpdatePortfolios class for updating portfolio NAVs
- preferences.py: MonitorPortfolio class for drift detection
- detections.py: Detection functions for allocation drift, drawdowns, correlations
- utils.py: Utility functions for ticker classification
- models.py: Data models for portfolio monitoring

Usage:
    from app.db.jobs.portfolio import UpdatePortfolios

    updater = UpdatePortfolios()
    updater.update_portfolios()
    updater.close()
"""

from app.db.jobs.portfolio.update import UpdatePortfolios

__all__ = [
    'UpdatePortfolios',
]
