"""Default execution-layer risk controls for the strategy scaffold."""

from __future__ import annotations

from prophitai_algo_trading.risk.base import RiskControl
from prophitai_algo_trading.risk.controls import (
    ReentryCooldownControl,
    TrailingStopExitControl,
)
from prophitai_algo_trading.strategies.template.config import (
    TemplateRiskControlConfig,
)


def build_template_risk_controls(
    config: TemplateRiskControlConfig,
) -> list[RiskControl]:
    """Build the opt-in risk-control stack for the scaffold strategy."""
    controls: list[RiskControl] = []

    if config.enable_reentry_cooldown:
        controls.append(ReentryCooldownControl(bars=config.reentry_cooldown_bars))

    if config.enable_trailing_stop:
        controls.append(TrailingStopExitControl(pct=config.trailing_stop_pct))

    return controls
