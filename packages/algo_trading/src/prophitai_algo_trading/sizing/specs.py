"""Declarative sizing specs for strategy-level configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from prophitai_algo_trading.sizing.base import BasePositionSizer


SizerKey = str | type[BasePositionSizer]


@dataclass(frozen=True, slots=True)
class SizingSpec:
    """Declarative description of a position sizer instance.

    Args:
        sizer: Registry key (str) or direct class reference.
        params: Constructor kwargs for the sizer.
        wrapper: Optional wrapper sizer key/class (e.g. "drawdown_scaled").
        wrapper_params: Constructor kwargs for the wrapper (excluding ``base_sizer``).
        description: Optional human-readable description.
    """

    sizer: SizerKey
    params: dict[str, Any] = field(default_factory=dict)
    wrapper: SizerKey | None = None
    wrapper_params: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
