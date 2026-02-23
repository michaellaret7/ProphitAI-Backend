"""Quick test of @agent_tool decorator with docstring parsing."""

import json
from typing import Annotated, Literal, Optional
from datetime import datetime
from app.core.atlas.tools.decorator import agent_tool, Param, Schema
from app.core.atlas.tools.tool_schemas import PORTFOLIO_DICT_SCHEMA


@agent_tool(name="portfolio_stress_test")
def stress_test(
    portfolio_dict: Annotated[dict, Schema(PORTFOLIO_DICT_SCHEMA)],
    scenario: Literal['recession', 'inflation', 'rate_hike', 'black_swan'],
    severity: Annotated[float, Param(min_val=0.1, max_val=5.0)] = 1.0,
    horizon_days: Annotated[int, Param(min_val=1, max_val=252)] = 30,
    include_correlation_shift: bool = False,
    *,
    _simulation_date: Optional[datetime] = None,
) -> str:
    """Run a stress test scenario against a portfolio to estimate potential losses.

    Examples:
        stress_test(portfolio_dict={...}, scenario='recession', severity=2.0)

    Raises:
        ValueError: If portfolio_dict is empty or scenario is invalid

    Args:
        portfolio_dict: Portfolio with all holdings and allocations
        scenario: The macro stress scenario to simulate
        severity: Multiplier on the scenario shock magnitude
        horizon_days: Number of trading days to project the stress over
        include_correlation_shift: Whether to model correlation breakdown under stress

    Returns:
        JSON with projected portfolio loss, per-ticker impact, and risk metrics
    """
    return json.dumps({"stub": True, "scenario": scenario, "severity": severity})


if __name__ == "__main__":
    tool = {k: v for k, v in stress_test.tool.items() if k != "function"}
    print(json.dumps(tool, indent=2))
