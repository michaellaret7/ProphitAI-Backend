"""Trade Idea Agent — generates publication-ready Substack articles.

Runs deep research across theory, macro, fundamentals, and market data tools,
then synthesizes findings into a polished trade idea article. Can deploy
general worker sub-agents for parallel deep research tasks.
"""

from functools import partial
from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_atlas.tools.base.worker_agent.deploy_general import (
    DEPLOY_GENERAL_WORKER_TOOL,
    deploy_general_worker,
)

from prophitai_substack.trade_idea.tool_registry import TRADE_IDEA_TOOLS


class TradeIdeaAgent:
    """Generates trade idea articles for the ProphitAI Substack.

    Conducts deep research via theory, macro, fundamentals, and market data
    tools. Can spawn general worker sub-agents for parallel research tasks.
    Produces a free-form markdown article — no rigid output schema.
    """

    DEFAULT_TASK = (
        "Research and write a compelling trade idea article for the ProphitAI "
        "Substack. Use research tools extensively to find a timely, evidence-backed "
        "trading opportunity, assess the macro context, identify specific instruments "
        "to express the trade, and produce a complete, publication-ready article."
    )

    def __init__(
        self,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "trade_idea",
        provider: Optional[str] = None,
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):
        """Initialize the Trade Idea agent.

        Args:
            chat_callback: Optional callback for streaming progress.
            session_id: Identifier for the agent session.
            provider: LLM provider override.
            model: LLM model override.
            print_mode: Console output verbosity.
        """

        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "prompts" / "system.md"
        system_prompt = prompt_path.read_text(encoding="utf-8").format(date=date)

        self.agent = Agent(
            tools=TRADE_IDEA_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            provider=provider,
            model=model,
            print_mode=print_mode,
        )

        # Reason: deploy_general_worker needs notebook, callback, and user_id
        # pre-bound. The LLM only sees task, tools, plan_task_id, context.
        self.agent.add_tool(
            **DEPLOY_GENERAL_WORKER_TOOL,
            function=partial(
                deploy_general_worker,
                self.agent.notebook,
                chat_callback or NoOpChatCallback(),
                None,
            ),
        )

    def run(self, task: Optional[str] = None) -> AgentResponse:
        """Execute the trade idea agent.

        Args:
            task: Optional topic or direction override. When provided, the agent
                focuses on that specific theme (e.g. "Write a trade idea about
                yield curve inversion and its implications for bank stocks").
                Defaults to autonomous discovery.

        Returns:
            AgentResponse with the article in the answer field.
        """
        return self.agent.run(
            task or self.DEFAULT_TASK,
            plan_first=True,
        )
