"""Universe of liquid US equities traded by the intraday long/short strategy.

Chosen for high intraday volume and sector diversification — a starter
set the data export can hit in minutes. Scale up once the pipeline is proven.
"""

UNIVERSE = [
    # Mega-cap tech
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "TSLA",
    # Financials
    "JPM", "BAC", "GS", "WFC",
    # Healthcare
    "JNJ", "UNH", "PFE", "LLY",
    # Consumer
    "PG", "KO", "WMT", "HD", "DIS",
    # Industrials / Energy
    "CAT", "BA", "XOM", "CVX",
]
