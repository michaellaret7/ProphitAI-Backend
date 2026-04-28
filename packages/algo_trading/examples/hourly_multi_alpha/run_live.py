r"""Run the hourly multi-alpha strategy live/paper against the ZMQ bar stream.

Default is paper trading:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_live.py

Real trading requires an explicit flag:
    .\.venv\Scripts\python.exe packages\algo_trading\examples\hourly_multi_alpha\run_live.py --real
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PKG_SRC = CURRENT_DIR.parents[1] / "src"
sys.path.insert(0, str(CURRENT_DIR))
sys.path.insert(0, str(PKG_SRC))

from prophitai_algo_trading import Alpaca, CostModel, LiveRunner

from config import Config
from data import load_hourly_data, load_universe
from strategy import build_live_algorithm


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run hourly multi-alpha live strategy.")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use real Alpaca trading. Default is paper trading.",
    )
    parser.add_argument(
        "--universe-size",
        type=int,
        default=250,
        help="Number of top active non-ETF stocks to trade.",
    )

    return parser.parse_args()


async def main_async() -> None:
    args = parse_args()
    cfg = Config(universe_size=args.universe_size)

    mode = "REAL" if args.real else "PAPER"
    print(f"\n=== Hourly multi-alpha live runner ({mode}) ===")

    tickers = load_universe(cfg)
    warmup_history = load_hourly_data(tickers, cfg)
    broker = Alpaca(paper=not args.real)
    algo = build_live_algorithm(broker, cfg)
    runner = LiveRunner(
        algorithm=algo,
        broker=broker,
        tickers=tickers,
        cost_model=CostModel(ptc=cfg.cost_per_turnover, ftc=1.0),
    )

    await runner.warmup(warmup_history)
    await runner.hydrate()
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main_async())
