"""Base contract for indicator calculators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import ClassVar

import pandas as pd

from prophitai_algo_trading.indicators.data_requirements import DataRequirement
from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class BaseIndicator(ABC):
    """Abstract base for reusable indicator calculators.

    Indicators enrich an OHLCV DataFrame with additional columns. They may
    support full-batch calculation only, or expose an optimized
    ``update_last_row`` path for live/event-driven engines.

    Subclasses that read supplementary data from ``df.attrs`` should declare
    their needs via the ``data_requirements`` class variable so the data
    resolver can fetch and attach everything automatically.
    """

    data_requirements: ClassVar[Sequence[DataRequirement]] = ()

    def __init__(self, df: pd.DataFrame):
        self.df = normalize_columns(df.copy())
        self.calculate()

    @abstractmethod
    def calculate(self) -> pd.DataFrame:
        """Compute indicator columns for the full DataFrame."""

    def update_last_row(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Update indicator columns for the last row.

        Subclasses can override this with a faster incremental path.
        """
        self.df = normalize_columns(new_df.copy())
        return self.calculate()

