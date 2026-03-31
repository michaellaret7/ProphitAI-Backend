"""Declarative indicator specs for shared and strategy-local composition."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from prophitai_algo_trading.indicators.base import BaseIndicator


IndicatorScope = Literal["shared", "strategy"]
IndicatorKey = str | type[BaseIndicator]


@dataclass(frozen=True, slots=True)
class IndicatorSpec:
    """Declarative description of one indicator instance in a pipeline."""

    indicator: IndicatorKey
    params: dict[str, Any] = field(default_factory=dict)
    scope: IndicatorScope = "shared"
    owner: str | None = None
    description: str | None = None

