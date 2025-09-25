from app.core.agentic_framework.tool_lib.agent_specific_tools.cro import GET_FINAL_PORTFOLIO_DICT_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.corr_matrix import CORRELATION_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.agent_specific_tools.cro import GET_FINAL_PORTFOLIO_DICT_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.vol_es import VOL_ES_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.asset_risk_contrib import RISK_CONTRIBUTION_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.drawdown_profile import DRAWDOWN_PROFILE_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.cov_matrix import CALCULATE_COVARIANCE_MATRIX_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.stress_test import STRESS_TEST_TOOL
from app.core.agentic_framework.tool_lib.risk_tools.pairwise_corr_analysis import PAIRWISE_CORR_ANALYSIS_TOOL
from app.core.agentic_framework.tool_lib.portfolio_tools.concentration import EXPOSURE_CALCULATOR_TOOL

def register_cro_tools(agent):
    """
    Register all CRO agent tools with the provided agent instance.
    
    All portfolio analysis tools require the 'portfolio_dict' parameter with actual portfolio data.
    Common GPT-5 mistake: Calling tools with empty arguments '{}' instead of passing portfolio data.
    ALWAYS pass the portfolio you want to analyze - never call with empty parameters.
    
    Args:
        agent: The CROAgent instance to register tools with
    """
    # Agent-specific
    agent.add_tool(**GET_FINAL_PORTFOLIO_DICT_TOOL)

    # Portfolio analytics
    agent.add_tool(**CORRELATION_MATRIX_TOOL)

    # Risk tools
    agent.add_tool(**CALCULATE_COVARIANCE_MATRIX_TOOL)
    agent.add_tool(**VOL_ES_TOOL)
    agent.add_tool(**RISK_CONTRIBUTION_TOOL)
    agent.add_tool(**DRAWDOWN_PROFILE_TOOL)
    agent.add_tool(**STRESS_TEST_TOOL)
    agent.add_tool(**PAIRWISE_CORR_ANALYSIS_TOOL)

    # Portfolio analytics (concentration)
    agent.add_tool(**EXPOSURE_CALCULATOR_TOOL)

