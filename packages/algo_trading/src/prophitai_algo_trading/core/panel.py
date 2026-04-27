"""``PricePanel`` — typed OHLCV bundle for the vectorized engine.

The vector engine operates on full ``[date x ticker]`` panels rather
than per-bar dictionaries. Each field is a pandas DataFrame with a
shared DatetimeIndex (rows = bars, columns = tickers). Alphas read
whichever fields they need (most use ``close``; volume-aware alphas
use ``volume``).

Supplementary data (fundamentals, macro series, sector tags) is NOT
carried on this panel by design. An alpha that needs supplementary
data accepts it through its own constructor — that keeps the engine
contract small and stable, and makes each alpha honest about its
inputs.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


#     ================================
# --> Helper funcs
#     ================================

def _validate_aligned(
    name: str, frame: pd.DataFrame, reference: pd.DataFrame,
) -> None:
    """Raise if ``frame`` doesn't share index + columns with ``reference``."""
    if not frame.index.equals(reference.index):
        raise ValueError(
            f"PricePanel.{name} index must equal close index "
            f"(got {len(frame.index)} rows vs {len(reference.index)})",
        )

    if list(frame.columns) != list(reference.columns):
        raise ValueError(
            f"PricePanel.{name} columns must equal close columns "
            f"(got {len(frame.columns)} cols vs {len(reference.columns)})",
        )


#     ================================
# --> Panel
#     ================================

@dataclass(frozen=True)
class PricePanel:
    """OHLCV panel — every field a ``[date x ticker]`` DataFrame.

    All five fields share the same DatetimeIndex and column set. ``close``
    is the single required field; ``open``, ``high``, ``low``, ``volume``
    are optional and may be ``None`` for alphas that don't need them.

    Attributes:
        close:   Close prices.    Required.
        open:    Open prices.     Optional.
        high:    High prices.     Optional.
        low:     Low prices.      Optional.
        volume:  Trade volume.    Optional.

    Construction is validated in ``__post_init__`` — non-None fields
    must match ``close``'s index and columns exactly. Misalignment is
    caught here rather than producing silent NaN math downstream.
    """

    close: pd.DataFrame
    open: pd.DataFrame | None = None
    high: pd.DataFrame | None = None
    low: pd.DataFrame | None = None
    volume: pd.DataFrame | None = None

    def __post_init__(self) -> None:
        if self.close is None or self.close.empty:
            raise ValueError("PricePanel.close cannot be empty")

        if not isinstance(self.close.index, pd.DatetimeIndex):
            raise ValueError("PricePanel.close must have a DatetimeIndex")

        for name in ("open", "high", "low", "volume"):
            frame = getattr(self, name)

            if frame is None:
                continue

            _validate_aligned(name, frame, self.close)

    @property
    def tickers(self) -> list[str]:
        """Column labels of the close panel — the universe."""
        return list(self.close.columns)

    @property
    def index(self) -> pd.DatetimeIndex:
        """Shared DatetimeIndex of every field on the panel."""
        return self.close.index  # type: ignore[return-value]


#     ================================
# --> Convenience constructor
#     ================================

def panel_from_per_ticker(
    data: dict[str, pd.DataFrame],
    columns: tuple[str, ...] = ("open", "high", "low", "close", "volume"),
) -> PricePanel:
    """Build a ``PricePanel`` from a ``{ticker: ohlcv_df}`` dict.

    Same input shape as the event-driven ``Backtest.run(data=...)`` so
    both engines can consume the same upstream loader.

    Tickers are sorted alphabetically for a stable column order; the
    union of all tickers' DatetimeIndex is used (missing bars become
    NaN). Columns absent from every ticker are returned as ``None``.

    Args:
        data: ``{ticker: DataFrame}`` keyed by ticker. Each DataFrame
            should have a DatetimeIndex and OHLCV columns.
        columns: Which OHLCV columns to extract. Default is full OHLCV.

    Returns:
        A validated ``PricePanel``.
    """
    if not data:
        raise ValueError("data is empty — cannot build PricePanel")

    tickers = sorted(data.keys())

    union_index: pd.DatetimeIndex = pd.DatetimeIndex([])

    for df in data.values():
        union_index = union_index.union(df.index)

    union_index = union_index.sort_values()

    panels: dict[str, pd.DataFrame | None] = {}

    for column in columns:
        frames: dict[str, pd.Series] = {}

        for ticker in tickers:
            df = data[ticker]

            if column not in df.columns:
                continue

            frames[ticker] = df[column].reindex(union_index)

        if not frames:
            panels[column] = None
            continue

        panels[column] = pd.DataFrame(frames).reindex(columns=tickers)

    if panels.get("close") is None:
        raise ValueError(
            "panel_from_per_ticker: no ticker had a 'close' column",
        )

    return PricePanel(
        close=panels["close"],
        open=panels.get("open"),
        high=panels.get("high"),
        low=panels.get("low"),
        volume=panels.get("volume"),
    )
