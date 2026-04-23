"""ZMQ subscriber for live market data.

Exposes three flavors:
  - ``async_subscribe``: async generator for asyncio-based engines.
  - ``subscribe`` with ``stype='generator'``: synchronous generator.
  - ``subscribe`` with ``stype='callback'``: fires a function per message.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator, Callable, Generator

import zmq
import zmq.asyncio


ZMQ_CONNECT_ADDR = "tcp://localhost:5555"


def subscribe(
    stype: str = "generator",
    symbol_filter: list[str] | None = None,
    callback: Callable | None = None,
) -> Generator | None:
    """Synchronous ZMQ subscriber.

    Args:
        stype: ``"generator"`` (yields messages) or ``"callback"``.
        symbol_filter: If set, only yield messages where ``symbol`` matches.
        callback: Required when ``stype='callback'``.
    """
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket.connect(ZMQ_CONNECT_ADDR)
    socket.subscribe("")

    print(f"[subscriber] Connected to {ZMQ_CONNECT_ADDR}")

    if stype == "generator":
        return _generator(ctx, socket, symbol_filter)

    _callback_loop(ctx, socket, symbol_filter, callback)

    return None


def _generator(ctx, socket, symbol_filter):
    try:
        while True:
            msg = socket.recv_json()

            if symbol_filter and msg.get("symbol") not in symbol_filter:
                continue

            yield msg
    except KeyboardInterrupt:
        print("\n[subscriber] Shutting down...")
    finally:
        socket.close()
        ctx.term()


def _callback_loop(ctx, socket, symbol_filter, callback):
    try:
        while True:
            msg = socket.recv_json()

            if symbol_filter and msg.get("symbol") not in symbol_filter:
                continue

            if callback:
                callback(msg)
            else:
                print("[subscriber]", msg)
    except KeyboardInterrupt:
        print("\n[subscriber] Shutting down...")
    finally:
        socket.close()
        ctx.term()


async def async_subscribe(
    symbol_filter: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async ZMQ subscriber that yields bars without blocking the event loop."""
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.connect(ZMQ_CONNECT_ADDR)
    socket.subscribe("")

    print(f"[subscriber] Connected to {ZMQ_CONNECT_ADDR} (async)")

    try:
        while True:
            msg = await socket.recv_json()

            if symbol_filter and msg.get("symbol") not in symbol_filter:
                continue

            yield msg
    except (asyncio.CancelledError, GeneratorExit):
        print("\n[subscriber] Async subscriber shutting down...")
    finally:
        socket.close()
        ctx.term()
