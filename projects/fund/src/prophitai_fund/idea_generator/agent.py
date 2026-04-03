"""Idea Generator Agent — autonomous trade idea generation.

Researches trading strategies via RAG tools (strategy_research, theory_research),
combines findings with macro context, and produces a structured trade idea
with implementation guidelines. Does NOT select specific tickers or build portfolios.
"""

from pathlib import Path
from typing import Optional, List, Union

from pydantic import BaseModel, Field

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_fund.idea_generator.tool_registry import IDEA_GENERATOR_TOOLS


# ================================
# --> Output models
# ================================

class TickerUniverse(BaseModel):
    """Describes characteristics of ideal securities — no specific tickers."""

    asset_classes: List[str] = Field(
        ..., description="Target asset classes (e.g., US large-cap equities, investment-grade bonds)"
    )
    characteristics: List[str] = Field(
        ..., description="Key traits securities should exhibit (e.g., high accruals, low P/B, strong momentum)"
    )
    sector_preferences: Optional[List[str]] = Field(
        None, description="Preferred sectors or industries, if applicable"
    )
    exclusions: Optional[List[str]] = Field(
        None, description="Types of securities to exclude and why"
    )
    liquidity_requirements: str = Field(
        ..., description="Minimum liquidity, market cap, or volume thresholds"
    )


class StrategyIdea(BaseModel):
    """Research-backed trading strategy concept with implementation guidelines."""

    strategy_name: str = Field(..., description="Descriptive name for the strategy")
    strategy_type: str = Field(
        ..., description="Category: momentum, mean_reversion, factor, thematic, macro, statistical_arbitrage, etc."
    )
    investment_thesis: str = Field(
        ..., description="Deep, multi-paragraph thesis covering the core anomaly/factor, "
        "academic backing, empirical evidence, and expected behavior"
    )
    time_horizon: str = Field(
        ..., description="Expected holding period with rationale"
    )
    ticker_universe: TickerUniverse
    entry_signals: List[str] = Field(
        ..., description="Conditions and signals that trigger entering positions"
    )
    exit_signals: List[str] = Field(
        ..., description="Conditions and signals that trigger exiting positions"
    )
    rebalance_guidelines: str = Field(
        ..., description="Rebalancing approach, frequency, and triggers"
    )
    risk_factors: List[str] = Field(
        ..., description="Key risks, drawdown scenarios, and regime sensitivities"
    )
    risk_management: str = Field(
        ..., description="Position sizing approach, stop-loss philosophy, and hedging considerations"
    )
    macro_context: str = Field(
        ..., description="Current macro environment assessment and how it affects strategy viability"
    )
    research_backing: List[str] = Field(
        ..., description="Key research findings from strategy_research and theory_research that support this strategy"
    )


# ================================
# --> Agent wrapper
# ================================

class IdeaGeneratorAgent:
    """Autonomous trade idea generator.

    Runs without user input. Researches trading strategies via RAG tools
    and generates a trade idea with implementation guidelines.
    Does not select specific tickers or build portfolios.
    """

    TASK = (
        "Generate a new trade idea. "
        "Use the research tools extensively to find a compelling edge, "
        "assess its macro viability, and produce a complete trade idea proposal."
    )

    def __init__(
        self,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "idea_generator",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):
        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = prompt_path.read_text().format(date=date)

        self._agent = Agent(
            deferred_tools=IDEA_GENERATOR_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider,
            model=model,
            print_mode=print_mode,
        )

    def run(self) -> AgentResponse:
        """Execute the idea generator agent.

        Returns:
            AgentResponse with answer, parsed_output (StrategyIdea), and metadata.
        """
        return self._agent.run(
            self.TASK,
            plan_first=True,
            format_output=StrategyIdea,
        )


if __name__ == "__main__":
    agent = IdeaGeneratorAgent()
    response = agent.run()
    print(response.answer)
    print(response.parsed_output)
