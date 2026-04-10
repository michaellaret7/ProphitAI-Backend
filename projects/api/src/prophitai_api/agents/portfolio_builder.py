"""Portfolio Builder agent — constructs diversified portfolios via plan-first orchestration.

Composes an Agent with portfolio-specific prompt, tools, and structured output.
"""

from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_atlas.tools.base.worker_agent.deploy_general import (
    deploy_general_worker,
    DEPLOY_GENERAL_WORKER_TOOL,
)

from prophitai_api.agents.models import PortfolioResponse
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
    # portfolio
    portfolio_performance,
    portfolio_risk,
    portfolio_stress_test,
    portfolio_factor_exposure,
    portfolio_classification,
    portfolio_covariance,
    portfolio_correlation,
    # portfolio construction
    portfolio_allocator,
    # news
    general_news,
    get_ticker_news,
    get_press_releases,
    # research
    macro_research,
    earnings_call_search,
    credit_research_search,
    economics_research_search,
    theory_research,
    # options (read-only analysis)
    get_option_expirations,
    get_option_contracts,
    get_options_chain,
    get_option_quote,
    get_option_price_history,
)


PORTFOLIO_BUILDER_TOOLS = [
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
    # portfolio
    portfolio_performance, portfolio_risk, portfolio_stress_test,
    portfolio_factor_exposure, portfolio_classification, portfolio_covariance,
    portfolio_correlation,
    # portfolio construction
    portfolio_allocator,
    # news
    general_news, get_ticker_news, get_press_releases,
    # research
    macro_research, earnings_call_search, credit_research_search,
    economics_research_search, theory_research,
    # options (read-only)
    get_option_expirations, get_option_contracts, get_options_chain,
    get_option_quote, get_option_price_history,
]


# ================================
# --> Prompt
# ================================

PORTFOLIO_BUILDER_PROMPT = """
<role>
Senior Portfolio Strategist operating at CIO level. You research, construct, and execute
portfolios grounded in macro analysis, fundamental research, and quantitative risk management.
</role>

<goal>
Transform the user's investment preferences into a fully constructed, data-backed portfolio, then return
the portfolio to the user.

The user has complete flexibility over strategy — longs, shorts, options, equities, ETFs,
or any combination. There are no restrictions on position direction or instrument type.
Honor exactly what they ask for.
</goal>

<capabilities>
You have access to a broad toolkit. Use whatever is relevant to the user's request:
- Equity and ETF screeners for candidate discovery
- Fundamental data, valuation ratios, and financial statements
- Factor exposures, performance history, and peer comparisons
- Risk tools: correlation, beta, VaR/ES, stress testing, drawdown analysis
- Options chain lookup, pricing, and multi-leg order construction
- Web search for current market context
- macro_research_search for deep macro analysis (rates, inflation, Fed policy, sector rotation)
- earnings_call_search for company-level earnings insights, guidance, and management commentary
</capabilities>

<Important Rules>
- Never ever use the execute trade tools. Your job is simply to build a portfolio for the user
and then the user will decide to actually execute the trades or not.
- Never register the trade execution tools with any worker agents.
</Important Rules>

<output_expectations>
Your final answer should give the user a clear picture of the portfolio you built:
- An investment thesis explaining the macro reasoning and strategy
- A holdings table showing every position (ticker, allocation, direction, instrument type)
- Brief rationale per position citing specific data from your analysis
- Portfolio-level risk metrics (volatility, beta, drawdown, VaR — whatever is relevant)
- Presentation of the proposed portfolio for user review

Adapt the depth and structure to the complexity of the request. A simple long-only equity
portfolio needs less than a multi-leg options + equity hedge strategy.
</output_expectations>

<constraints>
- Every inclusion must be supported by tool data — no speculation
- Do NOT use the portfolio_allocations tool
- Utilize batch tool calling for efficiency
- Call update_plan as you work through the plan
</constraints>

<user_request>
{user_preferences}
</user_request>

<output_format>
Your final answer MUST be valid JSON matching this exact structure:
{{
    "thesis": "Your investment thesis here — a detailed narrative covering the macro backdrop, strategic rationale, key themes, risk considerations, and how the portfolio is positioned. Write freely and in depth.",
    "portfolio": [
        {{
            "ticker": "AAPL",
            "allocation": "15%",
            "direction": "long",
            "instrument_type": "equity",
            "reasoning": "In-depth reasoning for this specific position — why it was selected, what data supports it, how it fits the thesis, and what catalysts or risks apply."
        }}
    ]
}}
</output_format>
"""


# ================================
# --> Agent wrapper
# ================================

class PortfolioBuilderAgent:
    """Portfolio construction agent powered by plan-first orchestration.

    Wraps Agent with portfolio-specific prompt, tools, and structured output.
    Exposes a no-arg run() for compatibility with run_agent_background().
    """

    def __init__(
        self,
        user_preferences: str,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "portfolio_builder",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):
        self._task = PORTFOLIO_BUILDER_PROMPT.format(user_preferences=user_preferences)

        orchestrator_prompt = build_orchestrator_system_prompt()

        self._agent = Agent(
            deferred_tools=PORTFOLIO_BUILDER_TOOLS,
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
        """Execute the portfolio builder with plan-first orchestration.

        Returns:
            AgentResponse with answer, parsed_output (PortfolioResponse), and metadata.
        """
        return self._agent.run(
            self._task,
            plan_first=True,
            format_output=PortfolioResponse,
        )
