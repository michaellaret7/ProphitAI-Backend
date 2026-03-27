"""Real-time minute bar publisher using Alpaca WebSocket + ZMQ."""

import os
import asyncio
import zmq
from datetime import datetime
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

# === CONFIG ===
ZMQ_BIND_ADDR = "tcp://*:5555"


class Bar(BaseModel):
    date: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def publish(symbols: list[str]):
    """Stream real-time minute bars from Alpaca and publish over ZMQ.

    Args:
        symbols: List of ticker symbols to stream (e.g. ['AAPL', 'MSFT']).
    """
    # Reason: import here to avoid circular imports and keep module importable without alpaca
    from alpaca.data.live import StockDataStream
    from alpaca.data.enums import DataFeed

    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')

    if not api_key or not secret_key:
        raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set in environment.")

    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.bind(ZMQ_BIND_ADDR)
    
    print(f"[tick-server] Publishing on {ZMQ_BIND_ADDR} for {symbols}")

    stream = StockDataStream(api_key, secret_key, feed=DataFeed.IEX)

    async def on_bar(bar):
        """Handle incoming minute bar from Alpaca WebSocket."""
        msg = Bar(
            date=bar.timestamp,
            symbol=bar.symbol,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=int(bar.volume),
        )
        socket.send_json(msg.model_dump(mode='json'))
        print("[tick-server]", msg)

    stream.subscribe_bars(on_bar, *symbols)

    try:
        stream.run()

    except KeyboardInterrupt:
        print("\n[tick-server] Shutting down...")
    finally:
        socket.close()
        ctx.term()


if __name__ == "__main__":
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
    publish(tickers)
