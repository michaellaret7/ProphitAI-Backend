"""Async ZMQ subscriber for live market data."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

import zmq
import zmq.asyncio


ZMQ_CONNECT_ADDR = "tcp://localhost:5555"

logger = logging.getLogger(__name__)


async def async_subscribe(
    symbol_filter: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async ZMQ subscriber that yields bars without blocking the event loop."""
    ctx = zmq.asyncio.Context()
    socket = ctx.socket(zmq.SUB)
    socket.connect(ZMQ_CONNECT_ADDR)
    socket.subscribe("")

    logger.info("Connected to %s (async)", ZMQ_CONNECT_ADDR)

    try:
        while True:
            msg = await socket.recv_json()

            if symbol_filter and msg.get("symbol") not in symbol_filter:
                continue

            yield msg
    except (asyncio.CancelledError, GeneratorExit):
        logger.info("Async subscriber shutting down")
    finally:
        socket.close()
        ctx.term()
