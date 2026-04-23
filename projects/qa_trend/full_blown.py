"""Full-blown institutional long/short equity — the framework's maximum flex.

Demonstrates what a *complete* strategy looks like using every layer of
the framework:

    8 alphas blended cross-sectionally by theme
           │
           ▼
    MultiAlphaBlendPCM -> MagnitudeWeightedLongShortPCM
        (z-score per alpha, weighted sum, quintile cut, dollar-neutral)
           │
           ▼
    4-layer Composite risk stack:
        1. PortfolioLimits     circuit breakers   (block new entries)
             - PortfolioDrawdownLimit  20%
             - DailyLossLimit          3%
             - ConsecutiveLossCooldown 8-losses-in-a-row -> 10 bars off
        2. MaxDrawdown         book-wide delever  (scale all targets 0.5x)
             - 12% DD -> 20-day cooldown, then reset
        3. PositionStops       per-symbol exits   (override targets to 0)
             - StopLossExit         6% hard
             - TrailingStopExit     4% retrace from favorable extreme
             - TimeStop             30 bars max hold
             - ProfitTargetExit     15% take-profit
             - ReentryCooldown      3 bars after any exit
        4. MaxGrossExposure    final guard        (downscale to fit 1.5x)
           │
           ▼
    SimulatedExecutionModel
        (diff portfolio vs targets; close+reopen on material changes;
         $1 + 1bp commission via CostModel)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from alphas import (
    PriceAccelerationAlpha,
    RiskAdjustedMomentumAlpha,
    VolatilityContractionAlpha,
)
from universe import BENCHMARK, UNIVERSE

from prophitai_algo_trading import Algorithm, CostModel, EventDrivenBacktest
from prophitai_algo_trading.alphas import (
    BreakoutAlpha,
    LowVolAlpha,
    MomentumAlpha,
    ShortTermReversalAlpha,
    TrendVolumeAlpha,
)
from prophitai_algo_trading.framework.execution import SimulatedExecutionModel
from prophitai_algo_trading.framework.portfolio_construction import (
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    ConsecutiveLossCooldown,
    DailyLossLimit,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    PortfolioDrawdownLimit,
    ProfitTargetExit,
    ReentryCooldown,
    StopLossExit,
    TimeStop,
    TrailingStopExit,
)
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


START = "2022-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Alpha weighting — grouped by thesis family
#     ================================

ALPHA_WEIGHTS = {
    # ---- Medium-term trend family (35%): slow signals, long hold period.
    "momentum":          0.15,   # 12-1 Jegadeesh-Titman
    "risk_adj_momentum": 0.20,   # 63-day Sharpe-style (custom)

    # ---- Short-term technical family (35%): fast signals, weekly decay.
    "breakout":           0.15,  # Donchian 20 position
    "price_acceleration": 0.10,  # 30d vs prior-30d delta (custom)
    "trend_vol":          0.10,  # MACD * volume z-score

    # ---- Mean-reversion / regime family (30%): countertrend + vol regime.
    "reversal":         0.10,    # 5-day neg return
    "low_vol":          0.10,    # 60-day sigma cross-sec
    "vol_contraction":  0.10,    # vol_20 / vol_60 cross-sec (custom)
}


#     ================================
# --> Data
#     ================================

def load_data() -> tuple[dict[str, pd.DataFrame], pd.Series | None]:
    print(f"Fetching {len(UNIVERSE)} tickers + benchmark {BENCHMARK} ...")

    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE + [BENCHMARK], START, END, "daily")

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

    bench_df = bulk.get(BENCHMARK)
    benchmark: pd.Series | None = None

    if bench_df is not None and not bench_df.empty:
        bench_df = bench_df.copy()
        bench_df.index = pd.to_datetime(bench_df.index)
        bench_df = bench_df.sort_index()
        bench_df = bench_df[~bench_df.index.duplicated(keep="last")]
        benchmark = bench_df["close"]

    print(f"  loaded {len(ready)}/{len(UNIVERSE)} + benchmark {'OK' if benchmark is not None else 'MISSING'}")

    return ready, benchmark


#     ================================
# --> Algorithm factory
#     ================================

def build_algorithm() -> Algorithm:
    """The complete institutional long/short specification.

    Composes 8 alphas + 4-layer risk + simulated exec. Every layer of
    the framework is exercised; every concrete risk rule in the library
    is wired.
    """
    return Algorithm(
        alphas=[
            # Built-in 5
            MomentumAlpha(lookback_days=252, skip_days=21, hold_days=5),
            BreakoutAlpha(lookback_days=20, hold_days=3),
            ShortTermReversalAlpha(lookback_days=5, hold_days=3),
            LowVolAlpha(lookback_days=60, hold_days=20),
            TrendVolumeAlpha(hold_days=5),
            # Custom 3 (from this project's alphas.py)
            RiskAdjustedMomentumAlpha(lookback_days=63, hold_days=5),
            PriceAccelerationAlpha(fast_days=30, slow_days=60, hold_days=5),
            VolatilityContractionAlpha(recent_days=20, long_days=60, hold_days=10),
        ],

        portfolio_construction=MultiAlphaBlendPCM(
            weights=ALPHA_WEIGHTS,
            winsor_at=3.0,  # clip per-alpha z-scores at ±3σ before blending
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5,
                per_position_cap=0.08,
                quantile=0.15,          # top/bottom 15% of universe each side
                min_abs_score=0.20,     # don't trade on weak composite scores
                rebalance_every=timedelta(days=5),
            ),
        ),

        risk_management=CompositeRiskModel([
            # Layer 1 — portfolio-wide circuit breakers.
            # block_entry fires → all new entries dropped; positions untouched.
            PortfolioDrawdownLimit(dd_pct=0.20),
            DailyLossLimit(loss_pct=0.03),
            ConsecutiveLossCooldown(max_losses=8, bars=10),

            # Layer 2 — book-wide delever on drawdown.
            # Scales ALL targets by 0.5x during cooldown; resets peak after.
            MaxDrawdownRiskModel(
                max_drawdown_pct=0.12,
                delever_factor=0.5,
                cooldown_days=20,
            ),

            # Layer 3 — per-symbol entry/exit rules.
            # force_exit overrides target to 0; block_entry drops new targets.
            StopLossExit(pct=0.06),           # hard 6% adverse move
            TrailingStopExit(pct=0.04),       # 4% pullback from favorable extreme
            TimeStop(max_bars=30),            # max 30 bars held
            ProfitTargetExit(pct=0.15),       # take profit at +15%
            ReentryCooldown(bars=3),          # 3 bars off-limits after exit

            # Layer 4 — final gross exposure cap.
            # Any upstream scaling respected; downscales if still over cap.
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),

        execution=SimulatedExecutionModel(min_change_pct=0.005),
    )


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    start_wall = datetime.now()

    print("=" * 60)
    print("Full-Blown Institutional Long/Short — 8 alphas, full risk stack")
    print("=" * 60)
    print(f"Period:   {START} -> {END}")
    print(f"Capital:  ${INITIAL_CAPITAL:,.0f}")
    print(f"Universe: {len(UNIVERSE)} tickers   Benchmark: {BENCHMARK}")
    print(f"Alpha weights:")
    for name, w in ALPHA_WEIGHTS.items():
        print(f"  {name:22s}  {w:.2f}")
    print()

    data, benchmark = load_data()

    algo = build_algorithm()

    print(f"\nAlgorithm: {len(algo.alphas)} alphas, max_lookback={algo.max_lookback}")
    print(f"Running backtest ...")

    engine = EventDrivenBacktest(
        algorithm=algo,
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),
    )

    result = engine.run(data, benchmark=benchmark)

    elapsed = (datetime.now() - start_wall).total_seconds()
    print(f"Backtest complete in {elapsed:.1f}s\n")

    m = result.metrics

    print("=" * 60)
    print("PERFORMANCE")
    print("=" * 60)
    print(f"  Total return:         {m['total_return_pct']:+.2f}%")
    print(f"  Annualized return:    {m['annualized_return_pct']:+.2f}%")
    print(f"  Sharpe ratio:         {m['sharpe_ratio']:+.2f}")
    print(f"  Max drawdown:         {m['max_drawdown_pct']:+.2f}%")
    print(f"  Win rate:             {m['win_rate_pct']:.1f}%")
    print(f"  Profit factor:        {m['profit_factor']:.2f}")
    print(f"  Total trades:         {m['total_trades']}")
    print(f"  Avg win / loss:       {m['avg_win_pct']:+.2f}% / {m['avg_loss_pct']:+.2f}%")
    print(f"  Long / short trades:  {m['long_trades']} / {m['short_trades']}")

    if m.get("beta_vs_benchmark") is not None:
        print(f"\n  Benchmark ({BENCHMARK}):    {m['benchmark_return_pct']:+.2f}%")
        print(f"  Beta vs benchmark:    {m['beta_vs_benchmark']:+.3f}")
        print(f"  Alpha vs benchmark:   {m['alpha_vs_benchmark_pct']:+.2f}%")

    # Reason: print a trade-type breakdown to show the risk rules are firing.
    trades = result.trades
    if not trades.empty:
        avg_hold_bars = None
        if {"entry_time", "exit_time"}.issubset(trades.columns):
            hold_days = (trades["exit_time"] - trades["entry_time"]).dt.days
            avg_hold_bars = float(hold_days.mean())

        print(f"\n  Avg hold (calendar days):  {avg_hold_bars:.1f}" if avg_hold_bars else "")

    print("\n" + "=" * 60)
    print("OK — full-blown strategy ran clean through the framework.")
    print("=" * 60)


if __name__ == "__main__":
    main()
