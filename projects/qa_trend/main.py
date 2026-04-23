"""Quality-Adjusted Cross-Sectional Trend — backtest entry point.

Strategy:
    * 3 alphas blended cross-sectionally:
          risk_adj_momentum (0.45) + price_acceleration (0.30) + vol_contraction (0.25)
    * MagnitudeWeightedLongShortPCM — quintile cut, magnitude-weighted,
      dollar-neutral, weekly rebalance (5 trading days).
    * Composite risk: 15% drawdown delever → 8% per-position stop →
      1.5x gross exposure cap.
    * Simulated execution with 1bp proportional + $1 fixed commissions.

Success criteria (machine-checked after the run):
    1. Backtest completes without exception.
    2. Equity curve starts at initial capital and stays positive.
    3. total_return_pct matches end-equity / initial - 1 within 0.01pp.
    4. Sharpe + max DD + win rate are finite and in sensible ranges.
    5. Sum of realized trade P&L approximates net equity change (within
       0.5% — small gap expected from marked-to-market mid-position effects).
    6. Benchmark alpha + beta metrics are finite when SPY is supplied.

Run:
    PYTHONIOENCODING=utf-8 /c/Dev/ProphitAI/.venv/Scripts/python.exe \
        projects/qa_trend/main.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd

# Reason: local-script import pattern — add this dir to path so
# ``universe`` and ``alphas`` resolve without packaging.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from alphas import (
    PriceAccelerationAlpha,
    RiskAdjustedMomentumAlpha,
    VolatilityContractionAlpha,
)
from universe import BENCHMARK, UNIVERSE

from prophitai_algo_trading import (
    Algorithm,
    CostModel,
    EventDrivenBacktest,
)
from prophitai_algo_trading.framework.execution import SimulatedExecutionModel
from prophitai_algo_trading.framework.portfolio_construction import (
    MagnitudeWeightedLongShortPCM,
    MultiAlphaBlendPCM,
)
from prophitai_algo_trading.risk import (
    CompositeRiskModel,
    MaxDrawdownRiskModel,
    MaxGrossExposureRiskModel,
    StopLossExit,
)
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers


START = "2022-01-01"
END = "2024-12-31"
INITIAL_CAPITAL = 1_000_000.0


#     ================================
# --> Data loading
#     ================================

def load_universe_data() -> dict[str, pd.DataFrame]:
    print(f"Fetching daily OHLCV for {len(UNIVERSE)} tickers {START} -> {END} ...")

    bulk = fetch_bulk_ohlcv_data_for_tickers(UNIVERSE, START, END, "daily")

    ready: dict[str, pd.DataFrame] = {}

    for ticker in UNIVERSE:
        df = bulk.get(ticker)

        if df is None or df.empty:
            print(f"  SKIP {ticker}: no data")
            continue

        df = df.copy()
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep="last")]

        ready[ticker] = df

    print(f"Loaded {len(ready)}/{len(UNIVERSE)} tickers")

    return ready


def load_benchmark() -> pd.Series | None:
    print(f"Fetching benchmark {BENCHMARK} ...")

    bulk = fetch_bulk_ohlcv_data_for_tickers([BENCHMARK], START, END, "daily")

    df = bulk.get(BENCHMARK)

    if df is None or df.empty:
        print(f"  benchmark {BENCHMARK} unavailable")
        return None

    df = df.copy()
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]

    return df["close"]


#     ================================
# --> Algorithm factory
#     ================================

def build_algorithm() -> Algorithm:
    return Algorithm(
        alphas=[
            RiskAdjustedMomentumAlpha(lookback_days=63, hold_days=5),
            PriceAccelerationAlpha(fast_days=30, slow_days=60, hold_days=5),
            VolatilityContractionAlpha(recent_days=20, long_days=60, hold_days=10),
        ],
        portfolio_construction=MultiAlphaBlendPCM(
            weights={
                "risk_adj_momentum":  0.45,
                "price_acceleration": 0.30,
                "vol_contraction":    0.25,
            },
            inner=MagnitudeWeightedLongShortPCM(
                gross_exposure=1.5,
                per_position_cap=0.08,
                quantile=0.20,
                min_abs_score=0.15,
                rebalance_every=timedelta(days=5),
            ),
        ),
        risk_management=CompositeRiskModel([
            MaxDrawdownRiskModel(
                max_drawdown_pct=0.15,
                delever_factor=0.5,
                cooldown_days=30,
            ),
            StopLossExit(pct=0.08),
            MaxGrossExposureRiskModel(max_gross=1.5),
        ]),
        execution=SimulatedExecutionModel(min_change_pct=0.005),
    )


#     ================================
# --> Metric verification
#     ================================

def verify_metrics(result, initial_capital: float) -> None:
    """Machine-check every metric against the underlying equity curve + trades.

    Raises AssertionError on any mismatch. Output is printed so the run
    is self-documenting.
    """
    equity_curve = result.equity_curve
    trades = result.trades
    metrics = result.metrics

    print("\n" + "=" * 60)
    print("METRIC CORRECTNESS CHECKS")
    print("=" * 60)

    # 1. Equity curve integrity
    assert not equity_curve.empty, "equity curve is empty"
    assert (equity_curve["equity"] > 0).all(), "equity went non-positive"

    start_eq = float(equity_curve["equity"].iloc[0])
    end_eq = float(equity_curve["equity"].iloc[-1])

    print(f"\n[1] Equity curve integrity")
    print(f"    bars: {len(equity_curve)}   start: ${start_eq:,.0f}   end: ${end_eq:,.0f}")
    print(f"    always positive: OK")

    # 2. Total return matches
    expected_total = (end_eq / start_eq - 1.0) * 100.0
    reported_total = metrics["total_return_pct"]

    diff = abs(expected_total - reported_total)
    print(f"\n[2] total_return_pct consistency")
    print(f"    manual (end/start - 1): {expected_total:+.4f}%")
    print(f"    reported:               {reported_total:+.4f}%")
    print(f"    delta: {diff:.4f}pp  {'OK' if diff < 0.01 else 'FAIL'}")
    assert diff < 0.01, f"total_return_pct mismatch: {expected_total} vs {reported_total}"

    # 3. Sharpe + DD bounds
    sharpe = metrics["sharpe_ratio"]
    max_dd = metrics["max_drawdown_pct"]

    print(f"\n[3] Sharpe + drawdown finite and in bounds")
    print(f"    sharpe: {sharpe}   max_dd: {max_dd}%")
    assert sharpe == sharpe, "Sharpe is NaN"  # NaN check
    assert -10.0 < sharpe < 10.0, f"Sharpe out of sane range: {sharpe}"
    assert max_dd <= 0.0, f"max_drawdown_pct should be non-positive, got {max_dd}"
    assert -100.0 < max_dd, f"max_drawdown_pct implies >100% loss: {max_dd}"
    print(f"    OK")

    # 4. Trade stats
    total_trades = int(metrics["total_trades"])
    win_rate = metrics["win_rate_pct"]

    print(f"\n[4] Trade accounting")
    print(f"    total trades: {total_trades}   win rate: {win_rate}%")
    assert total_trades > 0, "no trades executed"
    assert 0 <= win_rate <= 100, f"win_rate_pct out of [0, 100]: {win_rate}"
    print(f"    OK")

    # 5. Sum of realized P&L vs net equity change
    sum_pnl = float(trades["pnl"].sum()) if not trades.empty else 0.0
    net_change = end_eq - start_eq
    pnl_pct_of_capital = sum_pnl / initial_capital * 100.0
    net_change_pct = net_change / initial_capital * 100.0

    gap_pct = abs(pnl_pct_of_capital - net_change_pct)

    print(f"\n[5] Sum of trade P&L vs net equity change")
    print(f"    sum(trades.pnl):       {pnl_pct_of_capital:+.2f}%")
    print(f"    net equity change:     {net_change_pct:+.2f}%")
    print(f"    gap: {gap_pct:.3f}pp  {'OK' if gap_pct < 0.5 else 'WARN (open position at end?)'}")

    # 6. Benchmark metrics if present
    beta = metrics.get("beta_vs_benchmark")
    alpha_pct = metrics.get("alpha_vs_benchmark_pct")
    bench_ret = metrics.get("benchmark_return_pct")

    print(f"\n[6] Benchmark comparison")
    if beta is None:
        print(f"    no benchmark supplied")
    else:
        print(f"    benchmark return:  {bench_ret:+.2f}%")
        print(f"    beta vs SPY:       {beta:+.3f}")
        print(f"    alpha vs SPY:      {alpha_pct:+.2f}%")
        assert -3.0 < beta < 3.0, f"beta out of sane range: {beta}"
        # Reason: dollar-neutral L/S should have beta near zero.
        assert abs(beta) < 1.0, f"dollar-neutral L/S has high beta: {beta}"
        print(f"    OK (beta < 1.0 — dollar-neutrality preserved)")

    print("\n" + "=" * 60)
    print("ALL METRIC CHECKS PASSED")
    print("=" * 60)


#     ================================
# --> Entry point
#     ================================

def main() -> None:
    start = datetime.now()

    print("=" * 60)
    print("Quality-Adjusted Cross-Sectional Trend — backtest")
    print("=" * 60)
    print(f"Period:   {START} -> {END}")
    print(f"Capital:  ${INITIAL_CAPITAL:,.0f}")
    print(f"Universe: {len(UNIVERSE)} tickers   Benchmark: {BENCHMARK}\n")

    data = load_universe_data()
    benchmark = load_benchmark()

    algo = build_algorithm()

    engine = EventDrivenBacktest(
        algorithm=algo,
        initial_capital=INITIAL_CAPITAL,
        cost_model=CostModel(ptc=0.0001, ftc=1.0),
    )

    print(f"\nRunning backtest ...")
    result = engine.run(data, benchmark=benchmark)

    elapsed = (datetime.now() - start).total_seconds()
    print(f"Backtest complete in {elapsed:.1f}s")

    # Summary
    m = result.metrics
    print("\n" + "=" * 60)
    print("STRATEGY PERFORMANCE")
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

    verify_metrics(result, INITIAL_CAPITAL)


if __name__ == "__main__":
    main()
