import uuid
from typing import TYPE_CHECKING, Dict, Optional

from pydantic import BaseModel, Field
from typing_extensions import Literal

from app.core.agentic_framework.base_agent import BaseAgent
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.utils.decorators.timer import timer
from app.utils.time_utils import get_utc_date_str

from .prompts import system_prompt, user_prompt
from .tool_registry import register_optimizer_tools

if TYPE_CHECKING:
    from app.core.agentic_framework.base_agent.callbacks import StateCallback

# NOTE: Tool add --> Add a portfolio compare tool to compare the new proposed portfolio to the old one that needed optimizaiton

class PortfolioPosition(BaseModel):
    allocation: float
    position: Literal["long", "short"]
    thesis: str

class PortfolioChanges(BaseModel):
    added: Optional[Dict[str, str]] = Field(default_factory=dict, description="Tickers added and reasons")
    removed: Optional[Dict[str, str]] = Field(default_factory=dict, description="Tickers removed and reasons")
    adjusted: Optional[Dict[str, str]] = Field(default_factory=dict, description="Adjustments made and descriptions")

class OptimizedPortfolio(BaseModel):
    portfolio: Dict[str, PortfolioPosition] = Field(description="Optimized portfolio with ticker -> position details")
    changes: PortfolioChanges = Field(description="Portfolio changes made during optimization")

class OptimizerAgent(BaseAgent):
    def __init__(
        self,
        portfolio_id: str,
        risk_tolerance: str = None,
        time_horizon: str = None,
        investment_goals: str = None,
        sectors_to_exclude: str = None,
        sectors_to_include: str = None,
        tickers_to_keep: str = None,
        tickers_to_exclude: str = None,
        state_callback: Optional["StateCallback"] = None,
    ):
        """
        Initialize OptimizerAgent with a specific portfolio to optimize.

        Args:
            portfolio_id: UUID of the portfolio to optimize (must be a valid UUID format)
            risk_tolerance: User's risk tolerance (optional)
            time_horizon: User's investment time horizon (optional)
            investment_goals: User's investment goals (optional)
            sectors_to_exclude: Sectors to exclude from portfolio (optional)
            sectors_to_include: Sectors to include in portfolio (optional)
            tickers_to_keep: Tickers that must be kept in portfolio (optional)
            tickers_to_exclude: Tickers to exclude from portfolio (optional)
            state_callback: Optional callback for streaming task state updates to frontend.

        Raises:
            ValueError: If portfolio_id is not provided or is invalid format
        """
        if not portfolio_id:
            raise ValueError("portfolio_id is required")

        # Basic UUID format validation
        try:
            uuid.UUID(portfolio_id)
        except (ValueError, AttributeError) as e:
            raise ValueError(
                f"Invalid portfolio_id format: '{portfolio_id}'. "
                f"Must be a valid UUID (e.g., 'b07e9c3b-01a1-4431-9b5f-2048c1bc7e11'). "
                f"Error: {str(e)}"
            )

        self.portfolio_id = portfolio_id
        self.risk_tolerance = risk_tolerance
        self.time_horizon = time_horizon
        self.investment_goals = investment_goals
        self.sectors_to_exclude = sectors_to_exclude
        self.sectors_to_include = sectors_to_include
        self.tickers_to_keep = tickers_to_keep
        self.tickers_to_exclude = tickers_to_exclude

        # Build dynamic prompt with proper None handling
        self.dynamic_user_prompt = self._build_dynamic_prompt()

        super().__init__(
            # provider="anthropic",
            # model="claude-haiku-4-5",
            provider="deepseek",
            model="deepseek-chat",
            system_prompt=system_prompt,
            user_prompt=self.dynamic_user_prompt,
            max_iterations=200,
            plan_first=True,
            print_mode=PrintMode.DEBUG,
            state_callback=state_callback,
        )

        register_optimizer_tools(self)

    def _build_dynamic_prompt(self) -> str:
        """
        Build the user prompt with proper handling of None/empty values.
        Replaces template placeholders with actual values or 'Not specified' for None values.
        """
        prompt = user_prompt.replace("{{PORTFOLIO_ID}}", self.portfolio_id)

        # Replace each field, using 'Not specified' for None values
        replacements = {
            "{{RISK_TOLERANCE}}": self.risk_tolerance or "Not specified",
            "{{INVESTMENT_GOALS}}": self.investment_goals or "Not specified",
            "{{TIME_HORIZON}}": self.time_horizon or "Not specified",
            "{{SECTORS_TO_INCLUDE}}": self.sectors_to_include or "Not specified",
            "{{SECTORS_TO_EXCLUDE}}": self.sectors_to_exclude or "Not specified",
            "{{TICKERS_TO_KEEP}}": self.tickers_to_keep or "Not specified",
            "{{TICKERS_TO_EXCLUDE}}": self.tickers_to_exclude or "Not specified",
            "{{TODAYS_DATE}}": get_utc_date_str()
        }

        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        return prompt

