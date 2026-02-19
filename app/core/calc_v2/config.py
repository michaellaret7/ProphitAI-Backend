"""Shared constants for calc_v2."""

TRADING_DAYS = 252

DEFAULT_RF_ANNUAL = 0.045  # 10-Year UST yield (~4.5%)

# Reason: constant universe ensures all portfolios are z-scored against the
# same broad, diversified reference population (~52 tickers, all 11 GICS sectors).
UNIVERSE_TICKERS: list[str] = [
    # Information Technology
    'AAPL', 'MSFT', 'NVDA', 'ADBE', 'CRM', 'INTC', 'AMD', 'CSCO',
    # Health Care
    'JNJ', 'UNH', 'LLY', 'ABBV', 'MRK', 'ABT', 'PFE',
    # Financials
    'JPM', 'BAC', 'GS', 'MS',
    # Consumer Discretionary
    'AMZN', 'TSLA', 'HD', 'LOW', 'NKE',
    # Consumer Staples
    'PG', 'KO', 'PEP', 'WMT', 'COST',
    # Energy
    'XOM', 'CVX', 'COP', 'SLB',
    # Industrials
    'CAT', 'HON', 'UPS', 'GE', 'RTX',
    # Communication Services
    'GOOG', 'META', 'DIS', 'NFLX',
    # Utilities
    'NEE', 'DUK', 'SO',
    # Real Estate
    'AMT', 'PLD', 'SPG',
    # Materials
    'LIN', 'APD', 'FCX',
]
