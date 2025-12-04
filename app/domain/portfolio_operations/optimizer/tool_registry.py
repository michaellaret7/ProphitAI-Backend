from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.performance import CALCULATE_PORTFOLIO_PERFORMANCE_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.returns import CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.factor_tilts import FACTOR_TILTS_FOR_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import (
    EXPOSURE_CALCULATOR_TOOL, INDUSTRY_CONCENTRATION_TOOL, VAR_CALCULATOR_TOOL
)
from app.core.agentic_framework.tool_lib.agent_specific_tools.optimizer import GET_USER_PORTFOLIO_TOOL
from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst import SECTOR_ANALYST_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.build_allocations import BUILD_PORTFOLIO_TOOL

def register_optimizer_tools(agent):
    # Get user portfolio tool
    agent.add_tool(**GET_USER_PORTFOLIO_TOOL)

    # Sector Analyst tool
    agent.add_tool(**SECTOR_ANALYST_TOOL)

    # Portfolio construction tools
    agent.add_tool(**CORRELATION_MATRIX_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_PERFORMANCE_TOOL)
    agent.add_tool(**CALCULATE_PORTFOLIO_RETURNS_METRICS_TOOL)
    agent.add_tool(**FACTOR_TILTS_FOR_PORTFOLIO_TOOL)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)
    agent.add_tool(**INDUSTRY_CONCENTRATION_TOOL)
    agent.add_tool(**VAR_CALCULATOR_TOOL)
    agent.add_tool(**BUILD_PORTFOLIO_TOOL)