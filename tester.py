from app.domain.portfolio_operations.optimization.portfolio_analysis.performance import calculate_ticker_performances

long_short_portfolio = {
    "AAPL": {"position": "long", "allocation": 0.05},
    "MSFT": {"position": "long", "allocation": 0.05},
    "GOOGL": {"position": "long", "allocation": 0.05},
    "AMZN": {"position": "long", "allocation": 0.05},
    "NVDA": {"position": "long", "allocation": 0.85},
    "PG": {"position": "long", "allocation": 0.04},
    "JNJ": {"position": "long", "allocation": 0.04},
    "XOM": {"position": "long", "allocation": 0.04},
    "JPM": {"position": "long", "allocation": 0.04},
    "SPY": {"position": "long", "allocation": 0.05},
    
    "TSLA": {"position": "short", "allocation": 0.04},
    "NFLX": {"position": "short", "allocation": 0.04},
    "ZM": {"position": "short", "allocation": 0.03},
    "COIN": {"position": "short", "allocation": 0.03},
    "RIVN": {"position": "short", "allocation": 0.03},
    "MARA": {"position": "short", "allocation": 0.03},
    "GME": {"position": "short", "allocation": 0.03},
    "AMC": {"position": "short", "allocation": 0.03},
    "ARKK": {"position": "short", "allocation": 0.04},
    "IWM": {"position": "short", "allocation": 0.03},
    "EEM": {"position": "short", "allocation": 0.03},
    "BYND": {"position": "short", "allocation": 0.02}
}

print(calculate_ticker_performances(long_short_portfolio))