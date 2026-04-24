# Engines — Backtest and Live

Engines drive the bar loop.  Both wrap the same `BarRunner.step` — the only difference is where bars come from.

## `BarRunner` — the shared per-bar pipeline

`engines/runner.py`.  One class, one public method: `step(ctx)`.

```python
class BarRunner:
    def __init__(self, algorithm: Algorithm): ...

    def step(self, ctx: AlgorithmContext) -> None:
        """Alphas -> PCM -> risk -> execute -> lifecycle diff."""

    def force_flatten(self, ctx: AlgorithmContext) -> None:
        """Close every open position through the normal execution path."""
```

### `step()` — sequence per bar

1. Each alpha's `update(ctx)` → `list[Insight]`.  All insights concatenated.
2. `algorithm.portfolio_construction.create_targets(ctx, insights)` → `list[PortfolioTarget]`.
3. `algorithm.risk_management.manage(ctx, targets)` → `list[PortfolioTarget]` (possibly modified).
4. Snapshot pre-execute positions + trade count.
5. `algorithm.execution.execute(ctx, targets)` — mutates portfolio via sink.
6. Diff pre vs post, fire lifecycle hooks if `risk` satisfies `LifecycleAwareRiskModel`.

### `force_flatten()` — end-of-run cleanup

Synthesizes `PortfolioTarget(symbol, 0.0)` for every open symbol and pushes through `ExecutionModel.execute` + lifecycle.  Bypasses alphas, PCM, risk — it's unconditional.  Used by `Backtest.run` at the end so:

- Final trades land in the trade log.
- `on_position_closed` fires for every exit.
- Final equity reflects the fully-closed book.

## `Backtest`

`engines/backtest.py`.  Event-driven, bar-by-bar.

### Constructor

```python
from prophitai_algo_trading import Backtest, CostModel

engine = Backtest(
    algorithm=algo,                           # fully-configured Algorithm
    initial_capital=1_000_000.0,
    cost_model=CostModel(ptc=0.0001, ftc=1.0),
)
```

### `run(data, benchmark=None)`

```python
result = engine.run(
    data={"AAPL": df_aapl, "MSFT": df_msft, ...},
    benchmark=spy_series,                     # optional pd.Series for beta + alpha
)
```

Returns a `BacktestResult` with:

- `result.equity_curve` — DataFrame indexed by timestamp with `equity`, `cash`, `positions`.
- `result.trades` — DataFrame of closed trades.
- `result.metrics` — dict of performance metrics (see `analytics.md`).

### Data shape

`data` is `{ticker: DataFrame}` where each DataFrame:

- Is datetime-indexed (daily or intraday).
- Has columns `open, high, low, close, volume` (lowercase).
- Is sorted ascending by index.

Use `load_csv_data()` from `data/csv_loader.py` for CSV-based data, or `fetch_bulk_ohlcv_data_for_tickers` from `prophitai_data.repositories.price` for DB-backed tests.

### What `Backtest.run` does internally

1. Build a single `Portfolio` from `initial_capital` + `cost_model`.
2. Compute the sorted union of every ticker's `DatetimeIndex` — this is the bar schedule.
3. For each timestamp:
   - Slice each ticker's history up to that bar: `df.iloc[: idx + 1]`.
   - Mark last-known prices.
   - Build `AlgorithmContext(timestamp, portfolio, data=bar_data, warmup=bar_idx < max_lookback)`.
   - `BarRunner.step(ctx)`.
   - `portfolio.record_equity(timestamp, prices)`.
4. After the last bar, `BarRunner.force_flatten(last_ctx)` + record final equity.
5. Compute metrics via `calculate_metrics` with `warmup=max_lookback`.

### Warmup

`ctx.warmup = True` for the first `algorithm.max_lookback` bars.  `ExecutionModel` no-ops during warmup.  Alphas still tick so indicators populate.  Metrics are computed on post-warmup bars only (see `analytics.md`).

## `LiveRunner`

`engines/live.py`.  Subscribes to the ZMQ bar stream, batches bars by timestamp, drives the same `BarRunner`.

### Constructor

```python
from prophitai_algo_trading import LiveRunner, Alpaca, CostModel
from prophitai_algo_trading.execution import ExecutionModel, BrokerSink

broker = Alpaca(paper=True)

algo = Algorithm(
    alphas=[...],
    portfolio_construction=...,
    risk_management=...,
    execution=ExecutionModel(sink=BrokerSink(broker)),    # broker sink here
)

runner = LiveRunner(
    algorithm=algo,
    broker=broker,                            # same broker for hydration
    tickers=["AAPL", "MSFT", "GOOGL"],
    cost_model=CostModel(),
)
```

The broker is used for **startup snapshot + hydrate** only.  Order routing goes through `algorithm.execution`, which holds the `BrokerSink`.

### Three-phase lifecycle

```python
await runner.warmup(history_provider)       # seed indicators
await runner.hydrate()                      # pull broker state
await runner.run()                          # ingest the bar stream
```

#### `warmup(history)`

Seeds each ticker's rolling frame with historical bars so alphas have enough lookback before live bars arrive.  `history` is either:

- `{ticker: DataFrame}` — precomputed histories.
- `callable(ticker) -> DataFrame` — lazy fetcher.

Tickers with empty history are dropped from the active universe.  If ALL tickers fail, raises `RuntimeError`.

#### `hydrate()`

Pulls a `BrokerStartupSnapshot` from the broker and seeds the mirror `Portfolio`:

- `cash`, `equity` from the snapshot.
- Every `BrokerPositionSnapshot` becomes a `Position` in the mirror.

**Unmanaged positions abort the run.**  If the broker account holds a symbol not in `tickers`, `hydrate()` raises with the offending names — either add them to the universe or close them manually before restarting.

#### `run()`

Async generator consuming from `async_subscribe(symbol_filter=self.tickers)`.  Strategy for batching:

- Bars for different tickers at the same timestamp may arrive out-of-order.
- Keep accumulating bars in `self._batch_tickers` until either (a) a bar for a NEW timestamp arrives — flush the previous batch first — or (b) every ticker in the universe has reported for the current timestamp.
- On flush, build `AlgorithmContext`, call `BarRunner.step`, record equity.

### Error handling

- Broker rejections inside `BrokerSink` are logged and swallowed per-symbol.  One bad order doesn't kill the bar.
- Mirror state is only updated after a successful broker call — rejected orders don't drift the mirror out of sync.
- Bar ingest exceptions per ticker are logged and skipped.

### Warmup semantics (live)

`ctx.warmup = self._bar_count <= self.algorithm.max_lookback` — counts **live bars**, not historical ones pre-loaded via `warmup()`.  Historical data seeds the indicator state; live bars are what the warmup gate counts against.

In practice, if you prefer live trading to start immediately after startup, pre-load enough history in `warmup()` and the gate never engages (well, it does for the first `max_lookback` live bars).  If you want a fresh lookback window of live data, seed minimally.

## Running the live publisher

Start the publisher in one process:

```bash
python -m prophitai_algo_trading.data.streaming.publisher --symbols AAPL MSFT ...
```

It binds `tcp://*:5555` and streams Alpaca minute bars over ZMQ PUB.  See `data.md`.

Then start your `LiveRunner` in another process.  The subscriber connects to `tcp://localhost:5555`.

## Writing a custom engine

If you need a different bar source (e.g. another vendor's WebSocket, a replay-from-parquet engine for faster backtests), implement your own engine by:

1. Build an `AlgorithmContext` per bar.
2. Call `BarRunner.step(ctx)`.
3. Record equity if you care.

The full pipeline + lifecycle logic lives in `BarRunner`, so the engine only owns the bar-acquisition concern.
