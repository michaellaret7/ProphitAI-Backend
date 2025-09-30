"""CIO Agent Simulation Module.

This module provides a simulation framework for running the CIO agent with a historical
cutoff date (September 30, 2024) to enable immediate portfolio validation and backtesting.

The simulation agent uses the EXACT same prompts and architecture as the production CIO agent,
but with date-filtered data tools that only return information available as of the cutoff date.
The model is "tricked" into thinking today is September 30, 2024 via a natural date injection.

Key Components:
    - CIOSimulationAgent: Main agent class for simulation mode
    - config: Simulation configuration (cutoff dates, data availability)
    - simulation_tools: Date-filtered versions of data-fetching tools
    - simulation_tool_registry: Tool registration for simulation agent

How the Trick Works:
    The agent uses the original production CIO prompts with a simple date injection:
    "Today's date is September 30, 2024." at the start of the system prompt.
    The model believes it's operating on that date, and all tools return only pre-cutoff data.
    The model has NO IDEA it's in a simulation - it thinks it's making real-time decisions.

Usage:
    from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.simulation import (
        CIOSimulationAgent
    )

    # Run simulation agent (model thinks it's Sept 30, 2024)
    agent = CIOSimulationAgent(verbose=True)
    portfolio = agent.run()

    # The portfolio can now be tracked from Oct 2024 onwards to validate performance
"""

from .simulation_agent import CIOSimulationAgent, CIOPortfolioItem, FinalPortfolio
from .config import SIMULATION_CUTOFF_DATE, AVAILABLE_DATA_TYPES, UNAVAILABLE_DATA_TYPES

__all__ = [
    "CIOSimulationAgent",
    "CIOPortfolioItem",
    "FinalPortfolio",
    "SIMULATION_CUTOFF_DATE",
    "AVAILABLE_DATA_TYPES",
    "UNAVAILABLE_DATA_TYPES",
]

__version__ = "1.0.0"