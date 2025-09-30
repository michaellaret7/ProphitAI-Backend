"""Tool registry for CIO simulation agent.

This module registers simulation-aware versions of all CIO tools that respect
the September 30, 2024 cutoff date.
"""

from datetime import datetime
from functools import wraps
from typing import Callable, Dict, Any

from app.core.agentic_framework.tool_lib.agent_specific_tools.cio import (
    GET_ANALYST_PICKS_TOOL, PULL_REST_OF_TICKER_POOL_TOOL
)
from app.core.agentic_framework.tool_lib.data_tools.industry_factors import GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.sub_industry_factors import GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL
from app.core.agentic_framework.tool_lib.data_tools.stock_screener import STOCK_SCREENER_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.group_performance import CALCULATE_GROUP_PERFORMANCES_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.ticker_performance import CALCULATE_TICKER_PERFORMANCES_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.build_allocations import BUILD_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.beta import CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL, INDUSTRY_CONCENTRATION_TOOL, VAR_CALCULATOR_TOOL
)
from app.core.agentic_framework.tool_lib.ticker_tools.factors import CALCULATE_TICKER_FACTORS_TOOL
from app.core.agentic_framework.tool_lib.ticker_tools.performance import GET_TICKER_PERFORMANCE_AND_RISK_TOOL
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation.config import SIMULATION_CUTOFF_DATE

# OLD imports removed - no longer using old simulation_tools.py and simulation_tools_extended.py files
# All simulation tools are now created via the wrapper factory

# ==================== Simulation Wrapper Factory ==================== #

def create_simulation_tool(production_tool: Dict[str, Any], cutoff_date: datetime) -> Dict[str, Any]:
    """Create a simulation version of a production tool.

    This function wraps a production tool function to inject the simulation cutoff date
    without exposing it to the agent. The agent sees the exact same interface as production.

    Args:
        production_tool: The production tool dict with name, description, parameters, function
        cutoff_date: The simulation cutoff date to inject

    Returns:
        New tool dict with wrapped function that injects _simulation_date parameter
    """
    base_function = production_tool["function"]

    @wraps(base_function)
    def simulation_wrapper(*args, **kwargs):
        # Inject _simulation_date parameter (internal use only)
        kwargs['_simulation_date'] = cutoff_date
        return base_function(*args, **kwargs)

    return {
        "name": production_tool["name"],  # Keep same name
        "description": f"{production_tool['description']} (SIMULATION MODE - data up to Sept 30, 2024)",
        "parameters": production_tool["parameters"],  # Keep same parameters
        "function": simulation_wrapper,  # Use wrapped function
    }

# ==================== NEW Simulation Tools (Using Wrapper Factory) ==================== #

# Data tools
from app.core.agentic_framework.tool_lib.data_tools.repository import FETCH_TICKER_REPOSITORY_DATA_TOOL
from app.core.agentic_framework.tool_lib.data_tools.ticker_fundamentals import GET_TICKER_FUNDAMENTAL_DATA_TOOL

FETCH_TICKER_REPOSITORY_DATA_SIMULATION_TOOL_NEW = create_simulation_tool(
    FETCH_TICKER_REPOSITORY_DATA_TOOL,
    SIMULATION_CUTOFF_DATE
)

GET_TICKER_FUNDAMENTAL_DATA_SIMULATION_TOOL_NEW = create_simulation_tool(
    GET_TICKER_FUNDAMENTAL_DATA_TOOL,
    SIMULATION_CUTOFF_DATE
)

# Ticker tools
GET_TICKER_PERFORMANCE_AND_RISK_SIMULATION_TOOL_NEW = create_simulation_tool(
    GET_TICKER_PERFORMANCE_AND_RISK_TOOL,
    SIMULATION_CUTOFF_DATE
)

CALCULATE_TICKER_FACTORS_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_TICKER_FACTORS_TOOL,
    SIMULATION_CUTOFF_DATE
)

# Portfolio tools
CALCULATE_PORTFOLIO_RETURNS_METRICS_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL,
    SIMULATION_CUTOFF_DATE
)

CORRELATION_MATRIX_SIMULATION_TOOL_NEW = create_simulation_tool(
    CORRELATION_MATRIX_TOOL,
    SIMULATION_CUTOFF_DATE
)

CALCULATE_PORTFOLIO_PERFORMANCE_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_PORTFOLIO_PERFORMANCE_TOOL,
    SIMULATION_CUTOFF_DATE
)

CALCULATE_PORTFOLIO_BETA_VS_INDEX_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_PORTFOLIO_BETA_VS_INDEX_TOOL,
    SIMULATION_CUTOFF_DATE
)

CALCULATE_GROUP_PERFORMANCES_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_GROUP_PERFORMANCES_TOOL,
    SIMULATION_CUTOFF_DATE
)

CALCULATE_TICKER_PERFORMANCES_SIMULATION_TOOL_NEW = create_simulation_tool(
    CALCULATE_TICKER_PERFORMANCES_TOOL,
    SIMULATION_CUTOFF_DATE
)


def register_cio_simulation_tools(agent):
    """Register all CIO tools with simulation-aware versions for data fetching.

    Args:
        agent: The CIOSimulationAgent instance to register tools on
    """
    # Data tools (no date dependency - use production versions)
    agent.add_tool(**GET_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)
    agent.add_tool(**GET_SUB_INDUSTRY_BENCHMARK_CALCULATIONS_TOOL)

    # Data tools - NEW simulation versions (using wrapper factory)
    agent.add_tool(**GET_TICKER_FUNDAMENTAL_DATA_SIMULATION_TOOL_NEW)
    agent.add_tool(**FETCH_TICKER_REPOSITORY_DATA_SIMULATION_TOOL_NEW)

    # Agent-specific tools (these don't need simulation wrapping)
    agent.add_tool(**GET_ANALYST_PICKS_TOOL)

    # Ticker analytics - NEW simulation versions (using wrapper factory)
    agent.add_tool(**GET_TICKER_PERFORMANCE_AND_RISK_SIMULATION_TOOL_NEW)
    agent.add_tool(**CALCULATE_TICKER_FACTORS_SIMULATION_TOOL_NEW)

    # Portfolio analytics - NEW simulation versions (using wrapper factory)
    agent.add_tool(**CALCULATE_PORTFOLIO_RETURNS_METRICS_SIMULATION_TOOL_NEW)
    agent.add_tool(**CORRELATION_MATRIX_SIMULATION_TOOL_NEW)
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_SIMULATION_TOOL_NEW)
    agent.add_tool(**CALCULATE_PORTFOLIO_BETA_VS_INDEX_SIMULATION_TOOL_NEW)
    agent.add_tool(**CALCULATE_GROUP_PERFORMANCES_SIMULATION_TOOL_NEW)
    agent.add_tool(**CALCULATE_TICKER_PERFORMANCES_SIMULATION_TOOL_NEW)

    # Pure calculation tools (no date dependency - use production versions)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)
    agent.add_tool(**INDUSTRY_CONCENTRATION_TOOL)
    agent.add_tool(**VAR_CALCULATOR_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)

    # Agent-specific (continued)
    agent.add_tool(**PULL_REST_OF_TICKER_POOL_TOOL)