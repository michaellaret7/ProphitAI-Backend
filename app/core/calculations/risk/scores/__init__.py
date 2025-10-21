"""
Risk scoring system for tickers and portfolios.

This module provides comprehensive risk scoring across multiple dimensions:
- Market Risk: Volatility, VaR, drawdowns, beta
- Liquidity Risk: Trading liquidity and market impact
- Credit Risk: Financial health and solvency (future)
- Composite Risk: Combined multi-dimensional scoring
- Portfolio Risk: Portfolio-level aggregation

Each scorer calculates raw metrics, normalizes them, and produces a 0-1 score.
"""

from .market import calculate_market_risk


__all__ = [
    'calculate_market_risk'
]
