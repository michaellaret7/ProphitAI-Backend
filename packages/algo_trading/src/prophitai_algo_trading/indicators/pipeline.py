"""Composition utilities for indicator pipelines and strategy-local suites."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

import pandas as pd

from prophitai_algo_trading.indicators.base import BaseIndicator
from prophitai_algo_trading.indicators.registry import (
    INDICATOR_REGISTRY,
    IndicatorRegistry,
)
from prophitai_algo_trading.indicators.specs import IndicatorSpec
from prophitai_algo_trading.utils.normalize_columns import normalize_columns


class IndicatorPipeline:
    """Sequentially apply shared and strategy-local indicators."""

    def __init__(
        self,
        specs: Sequence[IndicatorSpec],
        registry: IndicatorRegistry | None = None,
    ) -> None:
        self.specs = tuple(specs)
        self.registry = registry or INDICATOR_REGISTRY
        self._instances: list[BaseIndicator] = []

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        data = normalize_columns(df.copy())
        self._instances = []

        for spec in self.specs:
            indicator_cls = self._resolve_indicator(spec)
            indicator = indicator_cls(data, **spec.params)
            data = indicator.df
            self._instances.append(indicator)

        return data

    def update_last_row(self, df: pd.DataFrame) -> pd.DataFrame:
        data = normalize_columns(df.copy())
        if len(self._instances) != len(self.specs):
            return self.calculate(data)

        for indicator in self._instances:
            previous = indicator.df.reindex(data.index)
            for column in previous.columns:
                if column in data.columns:
                    data[column] = data[column].combine_first(previous[column])
                else:
                    data[column] = previous[column]
            data = indicator.update_last_row(data)

        return data

    def _resolve_indicator(self, spec: IndicatorSpec) -> type[BaseIndicator]:
        if isinstance(spec.indicator, str):
            return self.registry.resolve(spec.indicator)
        return spec.indicator


class BaseIndicatorSuite(ABC):
    """Strategy-local indicator suite built from declarative specs."""

    def __init__(self, registry: IndicatorRegistry | None = None) -> None:
        self._pipeline = IndicatorPipeline(self.indicator_specs(), registry=registry)

    @abstractmethod
    def indicator_specs(self) -> Sequence[IndicatorSpec]:
        """Return the ordered indicator specs for this suite."""

    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._pipeline.calculate(df)

    def update_last_row(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._pipeline.update_last_row(df)
