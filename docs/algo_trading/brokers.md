# Brokers — Live Trading

`brokers/` is vendor-scoped: each brokerage gets its own subpackage under `brokers/` (today: `alpaca`).  Shared cross-vendor data types live at the top level.

## Public surface

```python
from prophitai_algo_trading import Alpaca
from prophitai_algo_trading.brokers import (
    BrokerStartupSnapshot,
    BrokerPositionSnapshot,
    BrokerOrderSnapshot,
)
```

## `Alpaca` facade

`brokers/alpaca/facade.py`.  Unified interface for all Alpaca operations — trading, portfolio reads, options, startup snapshots.

### Construction

```python
from prophitai_algo_trading import Alpaca

alpaca = Alpaca(
    api_key=None,                # falls back to ALPACA_API_KEY env var
    secret_key=None,              # falls back to ALPACA_SECRET_KEY env var
    paper=True,                   # paper trading by default
    options_feed="indicative",    # or "opra"
)
```

Internal components (accessible for advanced use):

- `alpaca.client` — raw `AlpacaClient` (credential / connection management).
- `alpaca.trading` — `AlpacaTrading` (order placement).
- `alpaca.portfolio` — `AlpacaPortfolio` (account + positions).
- `alpaca.options` — `OptionsService` (options data).

### Account / portfolio reads

```python
alpaca.get_account()                        # full account dict
alpaca.get_buying_power()                   # float
alpaca.get_cash()                           # float
alpaca.get_equity()                         # float
alpaca.get_positions()                      # list of position dicts
alpaca.get_position(symbol)                 # single position dict or None
alpaca.get_orders(status="open")            # list of order dicts
alpaca.get_portfolio_history(period="1M", timeframe="1D")
```

### Trading

```python
# simple orders
alpaca.buy("AAPL", qty=10)
alpaca.sell("AAPL", qty=5)

# dollar-denominated
alpaca.buy("AAPL", notional=1000)

# limit
alpaca.buy("AAPL", qty=10, limit_price=180.00)

# trailing stop
alpaca.sell("AAPL", qty=10, trail_percent=2.0)

# bracket (entry + TP + SL)
alpaca.buy(
    "AAPL", qty=10,
    take_profit=185.0, stop_loss=175.0,
    order_class="bracket",
)

# close
alpaca.close_position("AAPL")                   # full
alpaca.close_position("AAPL", qty=5)            # partial by shares
alpaca.close_position("AAPL", percentage=0.5)   # partial by %
alpaca.close_all_positions()
alpaca.cancel_order(order_id)
alpaca.cancel_all_orders()
```

Parameters for `buy` / `sell`:

| Param | Purpose |
|-------|---------|
| `qty` | Number of shares |
| `notional` | Dollar amount (use `qty` OR `notional`, not both) |
| `limit_price` | Limit order price |
| `stop_price` | Stop trigger price |
| `trail_price` | Dollar offset for trailing stop |
| `trail_percent` | Percent offset for trailing stop |
| `take_profit` | Take profit limit price (exit leg) |
| `stop_loss` | Stop loss trigger price (exit leg) |
| `stop_loss_limit` | Stop loss limit (omit for market-on-trigger) |
| `order_class` | `"bracket"`, `"oco"`, `"oto"` |
| `time_in_force` | `"day"`, `"gtc"`, `"ioc"`, `"fok"`, `"opg"`, `"cls"` |

### Options

```python
alpaca.get_option_expirations(underlying="SPY")
alpaca.get_options_chain(underlying="SPY", expiration="2026-05-15")
alpaca.get_option_contracts(
    underlying="SPY", contract_type="call",
    strike_range=(580, 600), limit=10,
)

alpaca.buy_option(symbol="SPY260515C00580000", qty=1)
alpaca.sell_option(symbol="SPY260515C00580000", qty=1)
alpaca.exercise_options_position("SPY260515C00580000")

alpaca.submit_multi_leg_order(
    legs=[
        {"symbol": "SPY260515C00580000", "ratio_qty": 1, "side": "buy"},
        {"symbol": "SPY260515C00590000", "ratio_qty": 1, "side": "sell"},
    ],
    qty=1,
    limit_price=2.5,
)

alpaca.get_option_bars(symbol="SPY260515C00580000", timeframe="1d")
alpaca.get_option_latest_quote(symbol="...")
alpaca.get_option_snapshot(symbol="...")
```

## Wiring into the framework

### Order routing — `BrokerSink`

```python
from prophitai_algo_trading import Alpaca, Algorithm
from prophitai_algo_trading.execution import ExecutionModel, BrokerSink

broker = Alpaca(paper=True)

algo = Algorithm(
    alphas=[...],
    portfolio_construction=...,
    risk_management=...,
    execution=ExecutionModel(sink=BrokerSink(broker)),
)
```

`BrokerSink` needs exactly three broker methods: `buy(symbol, qty)`, `sell(symbol, qty)`, `close_position(symbol)`.  The `Alpaca` facade satisfies this by duck typing.

### Startup hydration — `get_startup_snapshot`

Used by `LiveRunner.hydrate` to seed the mirror `Portfolio`:

```python
snapshot: BrokerStartupSnapshot = alpaca.get_startup_snapshot()
```

Returns normalized data:

```python
@dataclass
class BrokerStartupSnapshot:
    cash: float
    equity: float
    positions: list[BrokerPositionSnapshot]
    open_orders: list[BrokerOrderSnapshot]
    captured_at: datetime | None


@dataclass
class BrokerPositionSnapshot:
    symbol: str
    shares: float
    direction: Direction          # LONG / SHORT enum
    entry_price: float
    entry_date: datetime | None


@dataclass
class BrokerOrderSnapshot:
    order_id: str
    symbol: str
    side: str
    qty: float | None
    status: str
    order_type: str
```

`LiveRunner.hydrate` uses these to seed `Portfolio.cash`, `Portfolio.positions`, and to validate that no unmanaged symbols exist before starting the bar loop.

## Credentials

- **`.env`** at repo root, loaded via `dotenv`.
- `ALPACA_API_KEY`, `ALPACA_SECRET_KEY` — used by `Alpaca(...)` and `publish(...)`.
- Paper vs live is a constructor flag (`paper=True` by default).  **Always test in paper first.**
- `alpaca.is_paper()` → bool.

## Adding a new vendor

The `brokers/` package is vendor-scoped — each vendor is its own subpackage exposing a top-level facade.  To add IBKR:

1. Create `brokers/ibkr/` with client, trading, account, facade modules.
2. Expose a top-level `IBKR` class with methods matching `_BrokerLike` (`buy`, `sell`, `close_position`).
3. Add `get_startup_snapshot()` returning `BrokerStartupSnapshot`.
4. Export `IBKR` from `brokers/__init__.py`.

Then strategies can swap vendors without changing anything upstream:

```python
broker = IBKR(...)                           # instead of Alpaca(...)
algo.execution = ExecutionModel(sink=BrokerSink(broker))
```

The framework never sees vendor internals — only the minimal `buy`/`sell`/`close_position` surface.
