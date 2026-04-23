"""Universe of 80 liquid US equities across 11 GICS sectors.

Chosen for:
  - Deep daily liquidity (enables realistic L/S execution)
  - Sector breadth (cross-sectional dispersion for ranking alphas)
  - Pre-2021 listing history (so the 60-day warmup doesn't starve early bars)
"""

UNIVERSE = [
    # Technology (20)
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AVGO", "ORCL",
    "CRM", "ADBE", "CSCO", "AMD", "QCOM", "TXN", "IBM", "AMAT",
    "NOW", "INTU", "PYPL", "MRVL",
    # Financials (10)
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "AXP", "SPGI", "SCHW", "PGR",
    # Healthcare (10)
    "JNJ", "UNH", "LLY", "PFE", "ABBV", "MRK", "TMO", "ABT", "AMGN", "BMY",
    # Consumer Discretionary (8)
    "TSLA", "HD", "MCD", "NKE", "LOW", "SBUX", "BKNG", "TJX",
    # Consumer Staples (6)
    "PG", "KO", "PEP", "COST", "WMT", "MDLZ",
    # Industrials (8)
    "CAT", "BA", "HON", "GE", "UPS", "RTX", "DE", "UNP",
    # Energy (6)
    "XOM", "CVX", "COP", "EOG", "SLB", "PSX",
    # Communication Services (4)
    "DIS", "NFLX", "CMCSA", "T",
    # Utilities (3)
    "NEE", "DUK", "SO",
    # Real Estate (3)
    "AMT", "PLD", "EQIX",
    # Materials (2)
    "LIN", "SHW",
]

BENCHMARK = "SPY"
