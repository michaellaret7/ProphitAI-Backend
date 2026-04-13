"""AI Watchlist agent — builds themed stock watchlists via plan-first orchestration.

Composes an Agent with watchlist-specific prompt, tools, and structured output.
"""

from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_atlas.tools.base.worker_agent.deploy_general import (
    deploy_general_worker,
    DEPLOY_GENERAL_WORKER_TOOL,
)

from prophitai_api.agents.models import WatchlistResponse
from prophitai_api.agents.prompts import build_orchestrator_system_prompt

# ================================
# --> Tool imports from registry
# ================================

from prophitai_tools.registry import (
    # screener
    equity_screener,
    etf_screener,
    # ticker_analytics
    ticker_performance,
    ticker_risk,
    ticker_factors,
    ticker_technicals,
    # ticker_info
    get_ticker_info,
    get_etf_info,
    get_ticker_peers,
    get_stock_ratings,
    get_institutional_holders,
    get_product_segmentation,
    # sectors
    get_sector_industries,
    get_group_tickers,
    # fundamentals
    get_ticker_fundamental_data,
    get_analyst_estimates,
    get_ratios_ttm,
    get_price_target_data,
    # news
    general_news,
    get_ticker_news,
    get_press_releases,
    # research
    macro_research_search,
    earnings_call_search,
)


WATCHLIST_TOOLS = [
    # screener
    equity_screener, etf_screener,
    # ticker_analytics
    ticker_performance, ticker_risk, ticker_factors, ticker_technicals,
    # ticker_info
    get_ticker_info, get_etf_info, get_ticker_peers, get_stock_ratings,
    get_institutional_holders, get_product_segmentation,
    # sectors
    get_sector_industries, get_group_tickers,
    # fundamentals
    get_ticker_fundamental_data, get_analyst_estimates, get_ratios_ttm, get_price_target_data,
    # news
    general_news, get_ticker_news, get_press_releases,
    # research
    macro_research_search, earnings_call_search,
]


# ================================
# --> Prompt
# ================================

WATCHLIST_PROMPT = """
<role>
You are a Senior Equity Research Analyst specializing in thematic watchlist construction. You identify stocks and ETFs that match specific investment themes, profiles, or characteristics requested by users.
</role>

<goal>
Transform user investment themes into actionable watchlists by identifying characteristics, screening for candidates, validating with deep analysis, and providing data-backed reasoning.
</goal>

<methodology>
**Step 1: Theme Interpretation**
Decompose the user's request into measurable criteria and a structured theme. Examples:
- "Dividend aristocrats" → Consistent dividend growth, low payout ratio, stable cash flows
- "Turnaround plays" → Beaten-down valuations, improving fundamentals, recent analyst upgrades
- "AI Infrastructure Buildout" → Focus on semiconductors, cloud, data centers, utility stocks, etc.

**Step 2: Candidate Discovery**
- Use screeners (equity & ETF) to build a candidate universe.
- Filter the candidate universe based on the theme from the user's request.

**Step 3: Deep Analysis**
- Use performance, factor, fundamental, and ticker info tools to analyze candidates.
- Group tickers under the theme and find the best performers.
- Use the ticker info tool to understand business models for better grouping.
- Build a comprehensive basket supported by insightful data from all available tools.

**Step 4: Final Selection**
Rank candidates based on theme fit and performance. Exclude:
- Stocks that fail to meet core criteria
- Illiquid or penny stocks

Final Step: Call the finalize tool to return the final answer.
</methodology>

<output_requirements>
For each watchlist entry, provide:
1. **Ticker & Name**: Stock/ETF symbol and company name
2. **Theme Fit**: Why this security matches the user's criteria (1-2 sentences)
3. **Key Metrics**: 3-5 relevant data points that support inclusion
4. **Risk Factors**: Notable risks or caveats
</output_requirements>

<constraints>
- Every inclusion must be supported by data from tools—no speculation
- Exclude reference securities when user asks for "similar to X" or "next X"
- Target 5-15 securities per watchlist unless user specifies otherwise
- Prioritize liquid, tradeable securities (avoid penny stocks, low volume)
- Keep the plan to 2-4 main tasks for a quick workflow. Utilize batch tool calling.
- You must call the update_plan tool as you work through the tasks.
</constraints>

<user_request>
{user_query}
</user_request>

<instructions>
1. First, articulate what characteristics define securities matching this request
    a. Map them out in a list of criteria that can be screened for.
2. Then use screeners to build an initial candidate universe
    a. Use the screeners to build an initial candidate universe based on the criteria from the previous step.
3. Analyze top candidates with performance, factor, and fundamental tools
    a. Analyze the top candidates with performance, factor, and fundamental tools.
4. Construct the final watchlist with data-backed justifications
    a. Construct the final watchlist with data-backed justifications.
5. Present results clearly with ticker, rationale, and key supporting metrics
    a. Present the results clearly with ticker, rationale, and key supporting metrics.
</instructions>

<output_format>
{{
    "investment_thesis": "extensive and detailed investment thesis",
    "watchlist": [
        {{
            "ticker": "string",
            "name": "string",
            "investment_thesis": "extensive and detailed investment thesis citing specific data points from the tools and rationale for the pick"
        }}
    ]
}}
</output_format>
"""


# ================================
# --> Agent wrapper
# ================================

class WatchlistAgent:
    """AI-powered thematic watchlist builder.

    Wraps Agent with watchlist-specific prompt, tools, and structured output.
    Exposes a no-arg run() for compatibility with run_agent_background().
    """

    def __init__(
        self,
        user_preferences: str,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "watchlist",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):
        self._task = WATCHLIST_PROMPT.format(user_query=user_preferences)

        orchestrator_prompt = build_orchestrator_system_prompt()

        self._agent = Agent(
            deferred_tools=WATCHLIST_TOOLS,
            system_prompt=orchestrator_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider,
            model=model,
            print_mode=print_mode,
        )

        self._agent.add_tool(
            **DEPLOY_GENERAL_WORKER_TOOL,
            function=lambda **kwargs: deploy_general_worker(
                notebook=self._agent.notebook,
                chat_callback=self._agent.chat_callback,
                user_id=None,
                **kwargs,
            ),
        )

    def run(self) -> AgentResponse:
        """Execute the watchlist agent with plan-first orchestration.

        Returns:
            AgentResponse with answer, parsed_output (WatchlistResponse), and metadata.
        """
        return self._agent.run(
            self._task,
            plan_first=True,
            format_output=WatchlistResponse,
        )


if __name__ == "__main__":
    agent = WatchlistAgent(user_preferences="I want to build a watchlist for the best dividend aristocrats")
    response = agent.run()
    print(response.parsed_output)