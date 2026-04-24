# Data Layer

`data/` handles historical loading and live streaming.  The framework itself is data-source agnostic — it takes `{ticker: DataFrame}` at the engine boundary, however you build it.

## Required DataFrame shape

Every ticker's DataFrame must have:

- **`DatetimeIndex`**, sorted ascending, unique (no duplicate timestamps).
- **Columns**: `open`, `high`, `low`, `close`, `volume` (lowercase).
- All numeric (`float`).
- Daily or intraday — the framework doesn't care about frequency as long as it's consistent across tickers.

Missing bars are okay (tickers can have gaps); the backtest engine walks the **union** of all tickers' indexes and skips tickers without data at each bar.

## CSV loading — `load_csv_data`

`data/csv_loader.py`.  Reads one CSV per ticker into the required shape.

### Conventions

- One CSV per ticker, filename `<TICKER>.csv` (stem is uppercased to get ticker).
- Columns: `date, open, high, low, close, volume` (case-insensitive).
- `close` is the **adjusted close** — named simply `close`.
- Date column is parsed as-is (daily or intraday both work).

### Usage

```python
from prophitai_algo_trading import load_csv_data

data = load_csv_data(
    data_dir="path/to/csvs",
    tickers=["AAPL", "MSFT"],      # optional whitelist; None = load every CSV
    date_column="date",            # column name for the timestamp
)

# data == {"AAPL": df_aapl, "MSFT": df_msft}
```

Raises:

- `FileNotFoundError` — directory missing, no CSVs, missing specific ticker file.
- `ValueError` — CSV missing the date column, missing an OHLCV column, or zero rows.

### Internal normalization

Per file:

1. Lowercase every column name.
2. Parse `date_column` via `pd.to_datetime`.
3. Set index = date, sort ascending, rename index to `"date"`.
4. Select columns in canonical order (`open, high, low, close, volume`), cast to `float`.

## DB-backed loading (ProphitAI internals)

For strategies inside ProphitAI, use the platform data repositories:

```python
from prophitai_data.repositories.price import fetch_bulk_ohlcv_data_for_tickers

bulk = fetch_bulk_ohlcv_data_for_tickers(
    tickers=["AAPL", "MSFT", "GOOGL"],
    start="2023-01-01",
    end="2024-12-31",
    frequency="daily",
)
```

Returns `{ticker: DataFrame}` in the required shape (OHLCV, DatetimeIndex, ascending, unique).  See `packages/algo_trading/tests/test_strategy/universe.py::load_data` for the reference pattern — sanitization, index dedup, dropping empty frames.

## Live streaming

ZMQ publisher/subscriber for real-time bars.  `data/streaming/`.

### Publisher — `data/streaming/publisher.py`

Streams Alpaca minute bars over ZMQ PUB on `tcp://*:5555`.

```python
from prophitai_algo_trading.data.streaming.publisher import publish

publish(symbols=["AAPL", "MSFT", "GOOGL"])
```

Requires `ALPACA_API_KEY` and `ALPACA_SECRET_KEY` env vars.  Uses Alpaca's `StockDataStream` with the IEX feed.  Each bar is serialized to JSON as a `Bar` pydantic model:

```python
class Bar(BaseModel):
    date: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
```

Runs in blocking mode — typically launched in its own process.

### Subscriber — `data/streaming/subscriber.py`

Three flavors:

```python
from prophitai_algo_trading.data.streaming.subscriber import (
    async_subscribe,
    subscribe,
)

# async — for asyncio-based engines (LiveRunner uses this)
async for bar in async_subscribe(symbol_filter=["AAPL"]):
    ...

# synchronous generator
for bar in subscribe(stype="generator", symbol_filter=["AAPL"]):
    ...

# callback-style (blocking)
def on_bar(bar):
    ...
subscribe(stype="callback", callback=on_bar, symbol_filter=["AAPL"])
```

All three connect to `tcp://localhost:5555`.  `symbol_filter` is an optional allowlist — messages for other symbols are silently dropped.

### Live bar format (dict on the wire)

```json
{
  "date": "2026-04-24T14:31:00Z",
  "symbol": "AAPL",
  "open": 180.12,
  "high": 180.35,
  "low": 180.02,
  "close": 180.29,
  "volume": 14230
}
```

`LiveRunner` consumes these from `async_subscribe`, batches by timestamp, appends to per-ticker rolling DataFrames, and feeds the result to `BarRunner.step`.

## Benchmark data

For beta / Jensen's alpha in metrics, pass a benchmark price **Series** (not returns) to `Backtest.run`:

```python
benchmark = spy_prices    # pd.Series indexed by date, values are prices

result = Backtest(algo, initial_capital=1_000_000).run(data, benchmark=benchmark)
```

Cadence doesn't need to match the equity curve — `calculate_metrics` intersects on the datetime index before computing returns.

## Data-shape gotchas

- **Timezone handling** — index timestamps can be naive OR timezone-aware; just keep it consistent across tickers.  The framework compares with `<` / `>=` only.
- **Duplicate timestamps** — deduplicate before feeding to the engine.  The loaders drop duplicates with `keep="last"`; if you build DataFrames yourself, do the same.
- **Fractional shares** — fine.  `Portfolio`/`Trade`/`Position.shares` are all `float`.
- **Negative prices** — rejected by `weight_to_shares` and `_get_fill_price` (return `None`).  Drop / forward-fill before ingest.
- **Missing volume** — required column.  If a source doesn't provide it, fill with 0 (volume is only read by alphas that declare it in `required_columns`).

## Building a custom loader

Any function returning `{ticker: DataFrame}` in the canonical shape works:

```python
def load_parquet_data(parquet_dir: Path) -> dict[str, pd.DataFrame]:
    data = {}
    for file in parquet_dir.glob("*.parquet"):
        df = pd.read_parquet(file)
        df.columns = [c.lower() for c in df.columns]
        df = df.set_index(pd.to_datetime(df["date"])).sort_index()
        df = df[["open", "high", "low", "close", "volume"]].astype(float)
        data[file.stem.upper()] = df[~df.index.duplicated(keep="last")]
    return data
```

Feed to `Backtest.run(data)` directly.
