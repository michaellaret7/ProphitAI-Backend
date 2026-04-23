"""CSV loader for strategy OHLCV data.

Every strategy keeps its historical data as per-ticker CSV files in a
``data/`` folder. One CSV per ticker, named ``<TICKER>.csv``. Columns:
``date, open, high, low, close, volume`` (close is the adjusted close,
named simply ``close``). Daily and intraday share the same format —
the date column is parsed as-is.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")


def load_csv_data(
    data_dir: str | Path,
    tickers: list[str] | None = None,
    date_column: str = "date",
) -> dict[str, pd.DataFrame]:
    """Load every ticker CSV in ``data_dir`` into a {ticker: DataFrame} map.

    Args:
        data_dir: Directory containing ``<TICKER>.csv`` files.
        tickers: Optional whitelist. If None, every CSV in the directory
            is loaded and the ticker is inferred from the filename stem.
        date_column: Name of the date/timestamp column in the CSV.

    Returns:
        ``{ticker: DataFrame}`` indexed by parsed datetime and sorted, with
        columns ``open, high, low, close, volume``.

    Raises:
        FileNotFoundError: ``data_dir`` does not exist or contains no matching CSVs.
        ValueError: A CSV is missing required columns or contains no rows.
    """
    path = Path(data_dir)

    if not path.is_dir():
        raise FileNotFoundError(f"Data directory does not exist: {path}")

    files = (
        [path / f"{t}.csv" for t in tickers]
        if tickers is not None
        else sorted(path.glob("*.csv"))
    )

    if not files:
        raise FileNotFoundError(f"No CSV files found in {path}")

    data: dict[str, pd.DataFrame] = {}

    for file in files:
        if not file.exists():
            raise FileNotFoundError(f"Missing CSV: {file}")

        ticker = file.stem.upper()

        data[ticker] = _read_single(file, date_column)

    return data


def _read_single(file: Path, date_column: str) -> pd.DataFrame:
    """Read and normalize one OHLCV CSV."""
    df = pd.read_csv(file)

    df.columns = [c.lower() for c in df.columns]

    date_col_lower = date_column.lower()

    if date_col_lower not in df.columns:
        raise ValueError(
            f"{file.name} missing date column {date_column!r}. "
            f"Got columns: {list(df.columns)}"
        )

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]

    if missing:
        raise ValueError(f"{file.name} missing required columns: {missing}")

    df[date_col_lower] = pd.to_datetime(df[date_col_lower])
    df = df.set_index(date_col_lower).sort_index()
    df.index.name = "date"

    df = df[list(REQUIRED_COLUMNS)].astype(float)

    if df.empty:
        raise ValueError(f"{file.name} has no rows after parsing.")

    return df
