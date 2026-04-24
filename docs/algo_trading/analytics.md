# Analytics — Metrics and Results

`analytics/` computes performance metrics from an equity curve + trade log.  `BacktestResult` is the canonical return type from `Backtest.run`.

## `BacktestResult`

`analytics/metrics.py`.

```python
@dataclass
class BacktestResult:
    equity_curve: pd.DataFrame       # index=timestamp, cols=[equity, cash, positions]
    trades: pd.DataFrame             # closed trades
    metrics: dict[str, float | int]  # computed performance metrics
```

Access:

```python
result = Backtest(algo, initial_capital=1_000_000).run(data, benchmark=spy)

print(result.metrics["total_return_pct"])
print(result.metrics["sharpe_ratio"])
print(result.metrics["max_drawdown_pct"])

result.equity_curve.plot()                         # standard pandas
result.trades.sort_values("pnl", ascending=False)  # inspect largest wins
```

## `calculate_metrics`

Called automatically by `Backtest.run` — you rarely call it directly.  Signature:

```python
calculate_metrics(
    equity_curve: pd.DataFrame,
    trades: pd.DataFrame,
    benchmark: pd.Series | None = None,
    risk_free_rate: float = 0.0,
    warmup: int = 0,
    active_start: datetime | pd.Timestamp | None = None,
) -> dict[str, float | int | None]
```

### Active-window trim (front-only)

Metrics are computed over an "active window" — skip the leading bars where the curve is still flat at initial capital.  Precedence:

1. If `active_start` is given, slice from there.
2. Else if `warmup > 0`, drop the first `warmup` bars.
3. Else **auto-detect**: trim leading bars where `|equity - initial| / |initial| < 1e-6`.

This matters when an alpha has a long lookback (e.g. 252-day momentum + 252-day beta).  Measuring Sharpe over the flat warmup stretch dilutes toward zero.

`Backtest.run` passes `warmup=max_lookback` by default, so the active window starts right after alpha warmup.

### Metrics returned

#### Return

| Key | Meaning |
|-----|---------|
| `total_return_pct` | `(final / initial - 1) * 100` |
| `annualized_return_pct` | Geometric annualized |

#### Risk

| Key | Meaning |
|-----|---------|
| `max_drawdown_pct` | Worst peak-to-trough on the equity curve |
| `sharpe_ratio` | Annualized, using log returns with per-bar risk-free subtraction |

Bars-per-year is derived from the active window's actual elapsed time, so daily and intraday curves annualize correctly without a fixed multiplier.

#### Trades

Always computed on the **full** trade log (not filtered by active window):

| Key | Meaning |
|-----|---------|
| `total_trades` | Count |
| `win_rate_pct` | `winners / total * 100` |
| `profit_factor` | `gross_profit / gross_loss` (`inf` if no losses) |
| `avg_trade_return_pct` | Mean `return_pct` |
| `avg_win_pct` | Mean `return_pct` of winners |
| `avg_loss_pct` | Mean `return_pct` of losers |
| `largest_win` | Max `pnl` |
| `largest_loss` | Min `pnl` |
| `long_trades` | Count |
| `short_trades` | Count |

#### Benchmark-relative (if `benchmark` provided)

| Key | Meaning |
|-----|---------|
| `benchmark_return_pct` | Total return of the benchmark over the intersected date range |
| `beta_vs_benchmark` | OLS beta of portfolio returns on benchmark returns |
| `alpha_vs_benchmark_pct` | Jensen's alpha: `port_annualized - (rf + beta * (bench_annualized - rf))` in percent |

Beta/alpha go through `prophitai_calculations.risk.benchmark.calc_beta`.  The portfolio equity and benchmark series are strictly intersected on their datetime indexes before computing any returns — no `ffill`, no hidden shifts.  Returns `None` for beta/alpha if the intersection is too small (< 2 points) or `calc_beta` fails.

## Hard error: negative equity

`calculate_metrics` raises:

```
ValueError: Equity curve has non-positive values — accounting is broken.
```

If you see this, the bug is in accounting (short margin math, cost model, position tracking) — metrics can't be computed over non-positive equity.  Treat as a pipeline-break signal, not a strategy failure.

## Plotting

The framework doesn't ship plots.  Standard workflow:

```python
import matplotlib.pyplot as plt

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))

result.equity_curve["equity"].plot(ax=ax1, title="Equity")

# drawdown
eq = result.equity_curve["equity"]
dd = (eq - eq.cummax()) / eq.cummax() * 100
dd.plot(ax=ax2, title="Drawdown %", color="red")

plt.tight_layout()
plt.show()
```

## Grading — `tests/test_strategy/grading.py`

Reference implementation of a pipeline-break smoke test.  Asserts:

1. Equity curve non-empty.
2. Every equity point positive.
3. At least one trade fired.
4. Total return in `(-50%, +300%)` — not a P&L validator, just a sanity band.

Prints metrics, long/short breakdown, and top 10 most-traded symbols.  Useful as a harness for iterating on strategy plumbing before caring about P&L quality.

## Comparing multiple runs

No built-in comparison tool.  Collect `result.metrics` dicts into a DataFrame:

```python
results = {
    "v1": Backtest(algo_v1, initial_capital=1_000_000).run(data).metrics,
    "v2": Backtest(algo_v2, initial_capital=1_000_000).run(data).metrics,
}

pd.DataFrame(results).T
```

For walk-forward or parameter sweeps, run N backtests and aggregate metrics externally.  The framework is intentionally quiet on sweep orchestration — compose with your preferred harness.
