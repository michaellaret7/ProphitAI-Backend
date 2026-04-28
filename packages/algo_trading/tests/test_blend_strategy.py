"""Vectorized backtest of the intraday blended strategy (hourly bars).

Mirrors ``test_intraday_blend_strategy.py``'s strategy spec but routes
through ``VectorAlgorithm`` + ``VectorBacktest`` instead of the event-
driven ``Algorithm`` + ``Backtest``. Both engines should produce
similar headline metrics — the vector engine is ~50× faster and useful
for parameter sweeps; the event engine is the production-realistic
path with explicit fills, costs per fill, and risk gates.

    Alphas blended (Sharpe-weighted from the hourly isolation report):

        opening_hour_momentum   35%
        vwap_deviation          30%
        hourly_rsi              20%
        anchored_vwap_breakout  15%

    Engine: VectorBacktest (panel-vectorized, no portfolio/positions/
    fills — the L/S weights are multiplied by per-bar returns to
    compute the equity curve directly).

Run::

    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \\
        packages/algo_trading/tests/test_blend_strategy.py
"""

from __future__ import annotations

import time
from datetime import timedelta

import numpy as np
import pandas as pd

from prophitai_algo_trading import (
    VectorAlgorithm,
    VectorBacktest,
    panel_from_per_ticker,
)
from prophitai_algo_trading.alpha_signals.intraday import (
    AnchoredVWAPBreakoutAlpha,
    HourlyRSIAlpha,
    OpeningHourMomentumAlpha,
    SessionVWAPDeviationAlpha,
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortConstructor,
    MultiAlphaBlender,
)
from prophitai_data.db.models.market import Ticker
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_data.session.decorators import with_session


#     ================================
# --> Universe + window
#     ================================

UNIVERSE_SIZE = 250
BENCHMARK_TICKER = "SPY"
START = "2024-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


@with_session('market')
def _load_universe(size: int = UNIVERSE_SIZE, session=None) -> list[str]:
    rows = (
        session.query(Ticker.ticker)
        .filter(Ticker.is_etf.is_(False))
        .filter(Ticker.is_actively_trading.is_(True))
        .filter(Ticker.market_cap.isnot(None))
        .order_by(Ticker.market_cap.desc())
        .limit(size)
        .all()
    )
    return [row[0] for row in rows]


#     ================================
# --> Helper funcs
#     ================================

def _benchmark_returns() -> pd.Series:
    print(f"\nFetching benchmark ({BENCHMARK_TICKER}) hourly {START} -> {END}")

    bulk = fetch_bulk_ohlcv_data_for_tickers(
        [BENCHMARK_TICKER], START, END, "hourly",
    )

    df = bulk.get(BENCHMARK_TICKER)

    if df is None or df.empty:
        return pd.Series(dtype=float)

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df["close"].pct_change().dropna()


def _benchmark_stats(
    equity_curve: pd.DataFrame, benchmark: pd.Series,
) -> dict[str, float]:
    """Beta/alpha/correlation/R² of strategy vs. benchmark on hourly bars."""
    if equity_curve.empty or benchmark.empty:
        return {}

    strat_ret = equity_curve["equity"].pct_change().dropna()
    strat_ret.index = pd.to_datetime(strat_ret.index)

    aligned = pd.concat(
        [strat_ret.rename("strat"), benchmark.rename("bench")],
        axis=1,
        join="inner",
    ).dropna()

    if len(aligned) < 10:
        return {}

    strat = aligned["strat"].to_numpy(dtype=float)
    bench = aligned["bench"].to_numpy(dtype=float)

    bench_var = float(np.var(bench, ddof=1))

    if bench_var <= 0.0:
        return {}

    cov = float(np.cov(strat, bench, ddof=1)[0, 1])
    beta = cov / bench_var

    alpha_per_bar = float(strat.mean() - beta * bench.mean())
    alpha_annual_pct = alpha_per_bar * 1750.0 * 100.0  # ~1750 hourly bars/yr

    correlation = float(np.corrcoef(strat, bench)[0, 1])
    r_squared = correlation ** 2

    return {
        "beta": beta,
        "correlation": correlation,
        "r_squared": r_squared,
        "alpha_annual_pct": alpha_annual_pct,
        "n_obs": float(len(aligned)),
    }


def _load_panel(tickers: list[str]):
    print(f"\nFetching hourly OHLCV for {len(tickers)} tickers {START} -> {END}")

    t0 = time.perf_counter()
    bulk = fetch_bulk_ohlcv_data_for_tickers(tickers, START, END, "hourly")
    print(f"Fetched in {time.perf_counter() - t0:.1f}s")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in tickers:
        df = bulk.get(ticker)

        if df is None or df.empty:
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(tickers)} tickers")

    panel = panel_from_per_ticker(ready)

    print(
        f"Panel shape: {len(panel.index)} hourly bars x "
        f"{len(panel.tickers)} tickers",
    )

    return panel


def _build_algo() -> VectorAlgorithm:
    pcm = MultiAlphaBlender(
        weights={
            "opening_hour_momentum":  0.35,
            "vwap_deviation":         0.30,
            "hourly_rsi":             0.20,
            "anchored_vwap_breakout": 0.15,
        },
        inner=MagnitudeWeightedLongShortConstructor(
            gross_exposure=1.5,
            per_position_cap=0.10,
            quantile=0.20,
            min_abs_score=0.05,
            rebalance_every=timedelta(days=1),
        ),
    )

    return VectorAlgorithm(
        alphas=[
            OpeningHourMomentumAlpha(),
            SessionVWAPDeviationAlpha(),
            HourlyRSIAlpha(),
            AnchoredVWAPBreakoutAlpha(),
        ],
        pcm=pcm,
        initial_capital=INITIAL_CAPITAL,
        cost_per_turnover=0.0001,
    )


#     ================================
# --> Main
#     ================================

def main() -> None:
    print("\n=== Vectorized intraday blended-strategy backtest ===")

    tickers = _load_universe()
    panel = _load_panel(tickers)
    benchmark = _benchmark_returns()

    algo = _build_algo()

    print(f"\n{len(algo.alphas)} alphas: {algo.alpha_names}")

    engine = VectorBacktest(verbose=True)

    t0 = time.perf_counter()
    result = engine.run(algo, panel)
    elapsed = time.perf_counter() - t0

    print(f"\nVectorBacktest.run total: {elapsed * 1000:.1f} ms")

    print("\n--- Metrics ---")
    for key, value in result.metrics.items():
        if isinstance(value, float):
            print(f"  {key:30s} {value:.4f}")
        else:
            print(f"  {key:30s} {value}")

    final_equity = float(result.equity_curve["equity"].iloc[-1])
    initial = float(result.equity_curve["equity"].iloc[0])

    print(
        f"\nFinal equity: ${final_equity:,.0f} "
        f"(initial ${initial:,.0f}, multiplier {final_equity / initial:.3f}x)",
    )

    bench_stats = _benchmark_stats(result.equity_curve, benchmark)

    if bench_stats:
        print(f"\nBENCHMARK ({BENCHMARK_TICKER}) STATS:")
        print(f"  beta:              {bench_stats['beta']:.3f}")
        print(f"  correlation:       {bench_stats['correlation']:.3f}")
        print(f"  r_squared:         {bench_stats['r_squared']:.3f}")
        print(f"  alpha (annual %):  {bench_stats['alpha_annual_pct']:+.2f}")
        print(f"  aligned obs:       {int(bench_stats['n_obs'])}")

    print("\nVector backtest completed.")


if __name__ == "__main__":
    main()
