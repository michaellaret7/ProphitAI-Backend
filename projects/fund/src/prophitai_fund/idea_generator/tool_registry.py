"""Tool registry for the Idea Generator agent.

Curated subset of research and macro tools for autonomous strategy
idea generation. No ticker-specific or portfolio construction tools —
this agent researches strategy concepts, not specific securities.
"""

from typing import Callable, List

# ================================
# --> Research tools
# ================================
from prophitai_tools.research.strategy_research import strategy_research
from prophitai_tools.research.theory_research import theory_research
from prophitai_tools.research.macro_research import macro_research
from prophitai_tools.research.economics_research import economics_research_search

# ================================
# --> Macro tools
# ================================
from prophitai_tools.macro.commodity_prices import commodity_prices
from prophitai_tools.macro.us_rates import us_treasury_rates
from prophitai_tools.macro.indicators import macro_indicators

# ================================
# --> News
# ================================
from prophitai_tools.news.general_news import general_news


IDEA_GENERATOR_TOOLS: List[Callable] = [
    # research (core)
    strategy_research, theory_research, macro_research, economics_research_search,
    # macro context
    commodity_prices, us_treasury_rates, macro_indicators,
    # news
    general_news,
]
