"""Build Portfolio Simulation Module.

This module provides simulation frameworks for running portfolio construction agents
with a historical cutoff date (September 30, 2024) to enable immediate portfolio
validation and backtesting.

All simulation agents use the EXACT same prompts and architecture as production agents,
but with date-filtered data tools that only return information available as of the cutoff date.

Submodules:
    - cio: CIO agent simulation
    - industry_agents: Industry agent simulation
"""
