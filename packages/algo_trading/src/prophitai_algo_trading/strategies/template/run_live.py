"""Run the scaffold strategy against the live/paper trading engine."""

from __future__ import annotations

import asyncio

from prophitai_algo_trading.strategies.template.config import TemplateLiveConfig
from prophitai_algo_trading.strategies.template.wiring import (
    build_broker,
    build_live_runner,
)


def main() -> None:
    """Instantiate the live runner and start the event loop."""
    config = TemplateLiveConfig()
    broker = build_broker(config)
    runner = build_live_runner(broker=broker, live_config=config)
    asyncio.run(runner.run())


if __name__ == "__main__":
    main()
