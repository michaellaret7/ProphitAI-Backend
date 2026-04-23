"""Real-time minute bar publisher using Alpaca WebSocket + ZMQ."""

from __future__ import annotations

import os
from datetime import datetime

import zmq
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

ZMQ_BIND_ADDR = "tcp://*:5555"


class Bar(BaseModel):
    date: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def publish(symbols: list[str]) -> None:
    """Stream real-time minute bars from Alpaca and publish over ZMQ.

    Args:
        symbols: Tickers to subscribe to on the Alpaca WebSocket.
    """
    # Reason: import here to keep the module importable without alpaca installed.
    from alpaca.data.live import StockDataStream
    from alpaca.data.enums import DataFeed

    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")

    if not api_key or not secret_key:
        raise ValueError("ALPACA_API_KEY and ALPACA_SECRET_KEY must be set.")

    ctx = zmq.Context()
    socket = ctx.socket(zmq.PUB)
    socket.bind(ZMQ_BIND_ADDR)

    print(f"[tick-server] Publishing on {ZMQ_BIND_ADDR} for {symbols}")

    stream = StockDataStream(api_key, secret_key, feed=DataFeed.IEX)

    async def on_bar(bar):
        msg = Bar(
            date=bar.timestamp,
            symbol=bar.symbol,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=int(bar.volume),
        )
        socket.send_json(msg.model_dump(mode="json"))
        print("[tick-server]", msg)

    stream.subscribe_bars(on_bar, *symbols)

    try:
        stream.run()
    except KeyboardInterrupt:
        print("\n[tick-server] Shutting down...")
    finally:
        socket.close()
        ctx.term()
