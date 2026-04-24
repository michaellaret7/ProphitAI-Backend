# Accounting

`accounting/` is pure in-memory bookkeeping — cash, open positions, completed trades, equity history, transaction costs.  The sink mutates it; alphas / PCM / risk read from it.

## `Portfolio`

Full replacement for the old PortfolioTracker + PositionTracker + mixins.  Flat, explicit, ~180 LOC.

```python
from prophitai_algo_trading import Portfolio, CostModel

portfolio = Portfolio(
    initial_capital=1_000_000.0,
    cost_model=CostModel(ptc=0.0001, ftc=1.0),   # 1 bp + $1 per trade
)
```

Passed as `ctx.portfolio` every bar.  The ONLY mutable attribute on `AlgorithmContext`.

### Reading state

| API | Returns |
|-----|---------|
| `portfolio.cash` | Available cash (float) |
| `portfolio.initial_capital` | Starting equity |
| `portfolio.positions` | `{symbol: Position}` for open positions |
| `portfolio.position_count` | `len(positions)` |
| `portfolio.get_position(symbol)` | `+1` (long), `-1` (short), `0` (flat) |
| `portfolio.equity(prices=None)` | Mark-to-market equity using `prices` or last-known |
| `portfolio.latest_prices` | Read-only copy of last-known prices |
| `portfolio.trades` | List of closed `Trade`s |
| `portfolio.equity_curve()` | Equity history as a DataFrame |
| `portfolio.trades_df()` | Trade log as a DataFrame |

### Mutating state (sinks only)

| API | Purpose |
|-----|---------|
| `portfolio.open(symbol, direction, shares, price, timestamp)` | Open a new position.  Returns `False` if already held, `shares <= 0`, or (for longs) insufficient cash |
| `portfolio.close(symbol, price, timestamp)` | Close a position.  Returns the `Trade` record or `None` if not held |
| `portfolio.mark(prices)` | Update last-known prices without recording equity |
| `portfolio.record_equity(timestamp, prices)` | Snapshot equity for the equity curve |

**Don't call these from alphas / PCM / risk.**  Only the sink (via `ExecutionModel`) should mutate the portfolio.

### Long / short accounting

Cash flows differ by direction:

| Direction | `open` cash flow | `close` cash flow | P&L formula |
|-----------|------------------|-------------------|-------------|
| long (+1) | `-shares * price - cost` | `+shares * price - exit_cost` | `(exit - entry) * shares - total_costs` |
| short (-1) | `-entry_cost` (no cash reserved) | `+pnl + entry_cost` | `(entry - exit) * shares - total_costs` |

Shorts don't reserve cash at entry — only the entry commission is deducted.  Mark-to-market equity for shorts:

```python
equity += shares * (entry_price - mark)
```

## `Position`

```python
@dataclass
class Position:
    symbol: str
    shares: float
    direction: int               # +1 or -1
    entry_price: float
    entry_time: datetime
    entry_cost: float            # commission paid at entry
```

Read-only from the alpha / PCM / risk perspective.  Use `portfolio.positions[symbol]` to inspect.

## `Trade`

```python
@dataclass
class Trade:
    symbol: str
    direction: int
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    shares: float
    pnl: float                   # realized, net of costs
    return_pct: float            # pnl / (shares * entry_price) * 100
```

Produced by `portfolio.close()`.  Appended to `portfolio.trades`.  Available via `portfolio.trades_df()` as a DataFrame:

```
columns: [symbol, direction, entry_time, exit_time, entry_price, exit_price,
          shares, pnl, return_pct]
```

Where `direction` is stringified to `"long"` / `"short"` in the DataFrame.

## `CostModel`

`accounting/cost_model.py`.  Proportional + fixed transaction costs.

```python
CostModel(
    ptc=0.0001,          # proportional — 1 bp of notional
    ftc=1.0,             # fixed — $1 per trade
)
```

API:

- `cost(price, shares)` → `|shares| * price * ptc + ftc`
- `max_shares(price, cash)` → largest share count affordable after costs

Default is `CostModel()` = zero cost.  The backtest engine attaches a CostModel to the Portfolio:

```python
Backtest(algo, initial_capital=1_000_000.0, cost_model=CostModel(ptc=0.0005, ftc=0.5))
```

Costs are debited on every `open` and `close`.

## Equity curve

`portfolio.record_equity(timestamp, prices)` snapshots:

```python
{
    "timestamp": ...,
    "equity": <mark-to-market>,
    "cash": <available>,
    "positions": <open count>,
}
```

The engine calls this every bar.  `portfolio.equity_curve()` returns the curve as a DataFrame indexed by timestamp, de-duplicated (last wins).

## Reading from alphas / PCM / risk

Read-only patterns you'll see in signal code:

```python
# equity for sizing math
equity = ctx.portfolio.equity()

# currently invested symbols
for symbol, pos in ctx.portfolio.positions.items():
    ...

# net position direction for a symbol
sign = ctx.portfolio.get_position(symbol)      # +1 / -1 / 0

# cash available
cash = ctx.portfolio.cash

# entry info for an open position
pos = ctx.portfolio.positions.get(symbol)
if pos is not None:
    entry_price = pos.entry_price
    entry_time = pos.entry_time
    bars_held = len(ctx.data[symbol]) - (some entry row index)
```

## Don't

- **Don't** call `portfolio.open` / `portfolio.close` from alphas, PCM, or risk.  Only the sink does that, via `ExecutionModel`.
- **Don't** mutate `portfolio.positions` directly.  Use `open` / `close`.
- **Don't** assume integer shares.  `Position.shares` and `Trade.shares` are `float` — Alpaca supports fractional shares natively.
