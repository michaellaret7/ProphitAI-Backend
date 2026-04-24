# Execution

Stage 4 of the pipeline.  Takes risk-managed `PortfolioTarget`s, diffs against current holdings, and produces side effects — either a portfolio mutation (backtest) or a broker order plus a mirror update (live).

## The sink pattern

One `ExecutionModel` class owns the full decision matrix.  Its sink is the ONLY thing that differs between backtest and live:

```
ExecutionModel(sink=PortfolioSink())     # backtest
ExecutionModel(sink=BrokerSink(broker))  # live
```

## Protocol

```python
class ExecutionModel(Protocol):
    def execute(
        self,
        ctx: AlgorithmContext,
        targets: list[PortfolioTarget],
    ) -> None: ...
```

Pure side-effect stage.  Returns nothing.

## Decision matrix

For each target, compute the diff against current portfolio state and pick one action:

| Target | Current position | Action |
|--------|------------------|--------|
| `target_shares == 0` | flat | no-op |
| `target_shares == 0` | held | `sink.close` |
| `target_shares != 0` | flat | `sink.open(direction, abs(shares))` |
| `target_shares != 0` | same direction, material change | `sink.close` then `sink.open` |
| `target_shares != 0` | same direction, immaterial change | no-op |
| `target_shares != 0` | opposite direction | `sink.close` then `sink.open` (flip) |

Neither `Portfolio` nor the broker has a "resize" primitive — close-then-reopen is the way to crystallize prior P&L AND land on the exact new share count.  It also handles flips cleanly since close-then-open doesn't care about the previous sign.

## The built-in `ExecutionModel`

`execution/model.py`.  99% of strategies use this class directly; parameterize it with a sink, not a subclass.

```python
ExecutionModel(
    sink=PortfolioSink(),              # or BrokerSink(alpaca)
    min_change_pct=0.005,              # 0.5% notional delta threshold
)
```

### `min_change_pct` — material-change filter

Skip rebalances where the delta is trivial notional.  "100 shares held, target 101 shares" isn't worth a commission.  Check:

```python
|target_shares - current_shares| * price  >  min_change_pct * equity
```

Notional-based so the threshold scales with position size.  Set to `0` to rebalance on every target.

### Warmup

`execute()` early-returns when `ctx.warmup` is True.  No orders fire, no positions change.  Alphas still tick, PCM still computes targets, risk still manages — but nothing reaches the portfolio or broker.

### Fill price

Fills happen at the **current bar's close** (`df["close"].iloc[-1]`).  Daily-frequency strategies are fine with this; there's no close-of-bar lookahead guard yet.  If you need `next_open` fills, that's a future extension — open an issue.

## Order sinks (`execution/sinks.py`)

### `OrderSink` protocol

```python
class OrderSink(Protocol):
    def open(
        self, ctx, symbol, direction, shares, price,
    ) -> None: ...

    def close(
        self, ctx, symbol, price,
    ) -> None: ...
```

The sink is responsible for ALL state changes that follow the decision — including mirror-portfolio updates when the primary side-effect is a broker call.

### `PortfolioSink`

In-memory sink — mutates `ctx.portfolio` directly.  Used for backtests.

```python
class PortfolioSink:
    def open(self, ctx, symbol, direction, shares, price):
        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def close(self, ctx, symbol, price):
        ctx.portfolio.close(symbol, price, ctx.timestamp)
```

`ExecutionModel(sink=PortfolioSink())` is the legacy `SimulatedExecutionModel` — identical behavior, different seam.

### `BrokerSink`

Routes orders through a broker and **mirrors the fill into the local `Portfolio` on success**.  If the broker rejects an order, the exception is logged and swallowed per-symbol, and the mirror is NOT updated — so the mirror doesn't drift out of sync with the real account:

```python
class BrokerSink:
    def __init__(self, broker):                       # any object with buy/sell/close_position
        self._broker = broker

    def open(self, ctx, symbol, direction, shares, price):
        try:
            if direction == 1:
                self._broker.buy(symbol, qty=shares)
            else:
                self._broker.sell(symbol, qty=shares)
        except Exception:
            logger.exception("Broker open failed for %s", symbol)
            return                                    # mirror NOT updated

        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def close(self, ctx, symbol, price):
        try:
            self._broker.close_position(symbol)
        except Exception:
            logger.exception("Broker close failed for %s", symbol)
            return

        ctx.portfolio.close(symbol, price, ctx.timestamp)
```

The broker interface `BrokerSink` needs is three methods:

```python
class _BrokerLike(Protocol):
    def buy(self, symbol: str, qty: Any) -> Any: ...
    def sell(self, symbol: str, qty: Any) -> Any: ...
    def close_position(self, symbol: str) -> Any: ...
```

`prophitai_algo_trading.brokers.alpaca.facade.Alpaca` satisfies this.

## Wiring in `Algorithm`

### Backtest

```python
from prophitai_algo_trading.execution import ExecutionModel, PortfolioSink

algo = Algorithm(
    alphas=[...],
    portfolio_construction=...,
    risk_management=...,
    execution=ExecutionModel(sink=PortfolioSink(), min_change_pct=0.005),
)
```

### Live

```python
from prophitai_algo_trading import Alpaca
from prophitai_algo_trading.execution import ExecutionModel, BrokerSink

broker = Alpaca(paper=True)

algo = Algorithm(
    alphas=[...],
    portfolio_construction=...,
    risk_management=...,
    execution=ExecutionModel(sink=BrokerSink(broker)),
)
```

**The SAME `Algorithm` instance** runs in both modes — the sink is the only switch.

## Custom sinks

Write a custom sink if you need:

- Paper-trading against a non-Alpaca broker.
- A record-only sink for dry runs (log every intent without firing orders).
- A throttled sink that batches many targets into a single broker call.

Shape:

```python
class LoggingSink:
    def open(self, ctx, symbol, direction, shares, price):
        logger.info("OPEN %s %s @ %s × %s", symbol, direction, price, shares)
        ctx.portfolio.open(symbol, direction, shares, price, ctx.timestamp)

    def close(self, ctx, symbol, price):
        logger.info("CLOSE %s @ %s", symbol, price)
        ctx.portfolio.close(symbol, price, ctx.timestamp)
```

As long as the sink implements `open` and `close` with the documented signatures, `ExecutionModel` will accept it — structural typing.

## End-of-backtest flatten

`Backtest.run` calls `BarRunner.force_flatten(last_ctx)` after the final bar — it synthesizes `PortfolioTarget(symbol, 0.0)` for every open position and pushes them through the normal `ExecutionModel.execute` path.  That way every final trade:

- Appears in the trade log (realized P&L captured).
- Fires `on_position_closed` so lifecycle-aware risk rules see the exit.
- Uses the fill price from the last bar's close.

`force_flatten` bypasses alphas, PCM, and risk — it's an unconditional wind-down, not a normal bar.
