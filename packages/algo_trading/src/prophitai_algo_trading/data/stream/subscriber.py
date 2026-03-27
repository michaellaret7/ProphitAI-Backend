import asyncio
from typing import AsyncGenerator, Literal, Callable, Generator

import zmq
import zmq.asyncio

ZMQ_CONNECT_ADDR = "tcp://localhost:5555"

def subscribe(
    stype: Literal['generator', 'callback'] = 'generator',
    symbol_filter: list[str] = None,
    callback: Callable = None
) -> Generator | None:
    """
    Subscribe to ZMQ stream.

    Args:
        stype: 'generator' yields messages one at a time, 'callback' calls a function for each message
        symbol_filter: only process messages for these symbols (if None, all symbols)
        callback: function to call with each message (required if stype='callback', ignored otherwise)

    Returns:
        Generator if stype='generator', None if stype='callback'
    """
    ctx = zmq.Context()
    socket = ctx.socket(zmq.SUB)
    socket.connect(ZMQ_CONNECT_ADDR)
    socket.subscribe("")

    print(f"[subscriber] Connected to {ZMQ_CONNECT_ADDR}")

    if stype == 'generator':
        return _subscribe_generator(ctx, socket, symbol_filter)
    else:
        _subscribe_callback(ctx, socket, symbol_filter, callback)


def _subscribe_generator(ctx, socket, symbol_filter: list[str] = None):
    """Internal generator implementation."""
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


async def async_subscribe(
    symbol_filter: list[str] | None = None,
) -> AsyncGenerator[dict, None]:
    """Async ZMQ subscriber that yields bars without blocking the event loop.

    Args:
        symbol_filter: Only yield messages for these symbols (if None, all symbols).

    Yields:
        Bar dicts from the ZMQ stream.
    """
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


def _subscribe_callback(ctx, socket, symbol_filter: list[str] = None, callback: Callable = None):
    """Internal callback implementation."""
    try:
        while True:
            msg = socket.recv_json()

            if symbol_filter and msg.get("symbol") not in symbol_filter:
                continue

            # NOTE: If no callback is provided, the message is printed to the console (like a generator)
            # Logic here is that the function is called with the message as an argument if a callback is provided, otherwise the message is printed to the console
            # for example if on bar was the callback arg, then the on bar function would run here with the message as an argument
            # This is useful for when you want to do something with the message, like print it to the console, or save it to a database, etc.
            # Example: if the callback fun was a func that tool msg as an argument, prints the close price of the bar and then saves it to the database, it would be run on this line
            if callback:
                callback(msg) 
            else:
                print("[subscriber]", msg)

    except KeyboardInterrupt:
        print("\n[subscriber] Shutting down...")
    finally:
        socket.close()
        ctx.term()

