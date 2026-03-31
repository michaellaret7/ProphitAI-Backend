"""Registry for shared indicator implementations."""

from __future__ import annotations

from typing import TypeAlias

from prophitai_algo_trading.indicators.base import BaseIndicator


IndicatorType: TypeAlias = type[BaseIndicator]


class IndicatorRegistry:
    """Lookup table for shared indicator classes."""

    def __init__(self) -> None:
        self._registry: dict[str, IndicatorType] = {}

    def register(self, key: str, indicator_cls: IndicatorType) -> None:
        normalized = key.strip().lower()
        if not normalized:
            raise ValueError("Indicator key cannot be empty")
        self._registry[normalized] = indicator_cls

    def resolve(self, key: str) -> IndicatorType:
        normalized = key.strip().lower()
        if normalized not in self._registry:
            raise KeyError(
                f"Unknown indicator '{key}'. Available: {sorted(self._registry)}"
            )
        return self._registry[normalized]

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._registry))


INDICATOR_REGISTRY = IndicatorRegistry()

