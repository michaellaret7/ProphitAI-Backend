import asyncio

from prophitai_algo_trading.execution.position_sizer import InverseVolatilitySizer
from prophitai_algo_trading.strategies.macd_momentum import MACDMomentum
from prophitai_algo_trading.engines import LiveRunner
from prophitai_algo_trading.execution.cost_model import CostModel
from prophitai_algo_trading.broker.alpaca import Alpaca

strategy = MACDMomentum()

tickers = [
    # Consumer Staples
    "PG", "KO", "PEP", "WMT", "COST", "PM", "CL", "KMB", "GIS", "MDLZ",
    # Technology
    "AAPL", "MSFT", "NVDA", "GOOGL", "META", "AVGO", "ORCL", "AMD", "QCOM", "TXN",
    "AMAT", "MU", "INTC", "ADI", "KLAC", "LRCX", "NOW", "CRM", "ADBE", "INTU",
    # Financials
    "JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "AXP", "COF", "USB",
    # Healthcare
    "JNJ", "UNH", "LLY", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "AMGN",
    # Industrials
    "CAT", "DE", "HON", "UPS", "RTX", "LMT", "GE", "MMM", "EMR", "ETN",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG",
    # Consumer Discretionary
    "AMZN", "TSLA", "HD", "MCD", "NKE",
    # Communication Services
    "NFLX", "DIS", "CMCSA", "VZ", "T",
]

broker = Alpaca(paper=True)

engine = LiveRunner(
    strategy=strategy,
    broker=broker,
    tickers=tickers,
    sizer=InverseVolatilitySizer(
        max_positions=len(tickers),
        cost_model=CostModel(ptc=0.00005)
    ),
    max_positions=len(tickers),
    warmup_bars=200,
)
asyncio.run(engine.run())