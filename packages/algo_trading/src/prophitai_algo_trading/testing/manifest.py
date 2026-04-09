"""Declarative test manifest for composable trading strategies.

A strategy's test suite is defined by a single manifest that declares
what to test. The contract test harness uses the manifest to run all
applicable tests automatically — no bespoke test code needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from prophitai_algo_trading.risk.base import RiskControl
    from prophitai_algo_trading.strategies.composable import BaseComposableStrategy


@dataclass
class StrategyTestManifest:
    """Everything the test harness needs to know about a strategy.

    The ``build_strategy`` callable must return a fully-constructed
    ``BaseComposableStrategy`` instance.  The harness accesses
    ``.indicator_suite`` and ``.signal_model`` through the built
    strategy — no need to declare component classes separately.

    Each test method calls ``build_strategy()`` fresh to avoid
    cross-test state leakage from ``IndicatorPipeline._instances``.

    Args:
        name: Human-readable strategy name (used as pytest ID).
        build_strategy: Zero-arg callable returning a configured strategy.
        min_warmup_bars: Bars before signals are meaningful.
        config_class: Frozen dataclass config (for config contract tests).
        build_risk_controls: Callable returning risk control instances.
    """

    name: str
    build_strategy: Callable[[], BaseComposableStrategy]

    min_warmup_bars: int = 50

    config_class: type | None = None
    build_risk_controls: Callable[[], list[RiskControl]] | None = None
