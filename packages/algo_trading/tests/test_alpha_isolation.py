"""Smoke test — run_alpha_isolation across every pre-built alpha.

Loops every pre-built alpha alone through the same PCM and prints a
comparison table. ~70ms per alpha — a 5-alpha sweep finishes in
under half a second on the same data the multi-alpha smoke test uses.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \\
        packages/algo_trading/tests/test_alpha_isolation.py
"""

from __future__ import annotations

import time
from datetime import timedelta

import pandas as pd

from prophitai_algo_trading import (
    panel_from_per_ticker,
    run_alpha_isolation,
)
from prophitai_algo_trading.alpha_signals import (
    ADXAlpha,
    AccelerationAlpha,
    AccumulationDistributionAlpha,
    AmihudIlliquidityAlpha,
    BetaToMarketAlpha,
    BreakoutAlpha,
    ChaikinMoneyFlowAlpha,
    CloseLocationAlpha,
    ConnorsRSIAlpha,
    DispersionReversalAlpha,
    FiftyTwoWeekHighAlpha,
    GapFadeAlpha,
    GarmanKlassVolAlpha,
    IdiosyncraticVolAlpha,
    IntradayReversalAlpha,
    KaufmanEfficiencyAlpha,
    LotteryAlpha,
    LowVolAlpha,
    MomentumAlpha,
    MovingAverageRibbonAlpha,
    NarrowRange7Alpha,
    OBVSlopeAlpha,
    OvernightDriftAlpha,
    RSIAlpha,
    RangeCompressionAlpha,
    ShortTermReversalAlpha,
    SkewnessAlpha,
    StochasticOscillatorAlpha,
    TrendVolumeAlpha,
    TurnOfMonthAlpha,
    VolOfVolAlpha,
    VolumeShockAlpha,
)
from prophitai_algo_trading.construction import (
    MagnitudeWeightedLongShortPCM,
)
from prophitai_data.db.models.market import Ticker
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers
from prophitai_data.session.decorators import with_session


#     ================================
# --> Universe + window
#     ================================

UNIVERSE_SIZE = 500

BENCHMARK_TICKER = "SPY"

START = "2021-01-01"
END = "2025-12-31"


@with_session('market')
def _load_universe(size: int = UNIVERSE_SIZE, session=None) -> list[str]:
    """Top ``size`` non-ETF tickers by market cap from the market_data DB."""
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


UNIVERSE: list[str] = _load_universe()


#     ================================
# --> Helper funcs
#     ================================

def _load_benchmark() -> pd.Series:
    print(f"\nFetching benchmark ({BENCHMARK_TICKER}) {START} -> {END}")

    bulk = fetch_bulk_ohlcv_data_for_tickers(
        [BENCHMARK_TICKER], START, END, "daily",
    )

    df = bulk.get(BENCHMARK_TICKER)

    if df is None or df.empty:
        print(f"Benchmark {BENCHMARK_TICKER} unavailable — skipping")

        return pd.Series(dtype=float)

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df["close"]


def _load_panel():
    print(f"\nFetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END}")

    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in UNIVERSE:
        df = bulk.get(ticker)

        if df is None or df.empty:
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")

    panel = panel_from_per_ticker(ready)

    print(
        f"Panel shape: {len(panel.index)} bars x "
        f"{len(panel.tickers)} tickers",
    )

    return panel


def _build_pcm():
    """Fresh PCM factory — called once per isolated alpha run."""
    return MagnitudeWeightedLongShortPCM(
        gross_exposure=1.5,
        per_position_cap=0.10,
        quantile=0.20,
        min_abs_score=0.0,
        rebalance_every=timedelta(weeks=1),
    )


#     ================================
# --> Main
#     ================================

def main() -> None:
    print("\n=== Alpha isolation sweep ===")

    panel = _load_panel()
    benchmark = _load_benchmark()

    alphas = [
        # Trend / momentum
        MomentumAlpha(),
        BreakoutAlpha(),
        TrendVolumeAlpha(),
        MovingAverageRibbonAlpha(),
        AccelerationAlpha(),
        ADXAlpha(),
        KaufmanEfficiencyAlpha(),
        FiftyTwoWeekHighAlpha(),
        # Mean reversion / oscillators
        ShortTermReversalAlpha(),
        RSIAlpha(),
        DispersionReversalAlpha(),
        GapFadeAlpha(),
        StochasticOscillatorAlpha(),
        ConnorsRSIAlpha(),
        IntradayReversalAlpha(),
        # Volatility / squeeze / risk
        LowVolAlpha(),
        RangeCompressionAlpha(),
        GarmanKlassVolAlpha(),
        LotteryAlpha(),
        VolOfVolAlpha(),
        SkewnessAlpha(),
        IdiosyncraticVolAlpha(),
        BetaToMarketAlpha(),
        # Volume / flow
        VolumeShockAlpha(),
        OBVSlopeAlpha(),
        ChaikinMoneyFlowAlpha(),
        AccumulationDistributionAlpha(),
        AmihudIlliquidityAlpha(),
        # Range / candle / overnight
        CloseLocationAlpha(),
        NarrowRange7Alpha(),
        OvernightDriftAlpha(),
        # Calendar
        TurnOfMonthAlpha(),
    ]

    print(f"\nIsolating {len(alphas)} alphas through identical PCM ...")

    t0 = time.perf_counter()

    report = run_alpha_isolation(
        alphas=alphas,
        pcm_factory=_build_pcm,
        panel=panel,
        initial_capital=1_000_000.0,
        cost_per_turnover=0.0001,
        benchmark=benchmark if not benchmark.empty else None,
    )

    elapsed = time.perf_counter() - t0

    print(f"\nSweep complete in {elapsed * 1000:.1f} ms total")

    report.print_summary()


if __name__ == "__main__":
    main()
