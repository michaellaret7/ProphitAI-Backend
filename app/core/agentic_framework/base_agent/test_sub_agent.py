from datetime import datetime
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.tool_lib.sub_agents.ticker_analyst import (
    TICKER_ANALYST_TOOL,
)
from app.core.agentic_framework.base_agent.utils.models import PrintMode

SIMPLE_BASE_AGENT_SYSTEM_PROMPT = """
You are a portfolio analyst agent.

Your Goal is to compare two tickers and provide a comprehensive assessment of the two tickers, then followed by a recommendation on which ticker to buy.

Rules:
- If using sub-agent tools, I suggest you call some of them in parallel (at the same time) to speed up the process only when deemed appropriate.
"""


class SimpleBaseAgent(BaseAgent):
    """
    Minimal base agent that registers the TickerAnalyst sub-agent as a tool
    and delegates execution to it. The LLM is explicitly instructed to run
    the sub-agent tool and finalize the result.
    """

    def __init__(self, task: str) -> None:
        super().__init__(
            system_prompt=SIMPLE_BASE_AGENT_SYSTEM_PROMPT,
            user_prompt=task,
            provider="anthropic",
            model="claude-haiku-4-5-20251001",
            max_iterations=100,
            print_mode=PrintMode.DEBUG,
            reasoning_effort="medium",
            temperature=0.7,
            plan_first=True,
            simulation_date=None
        )

        # Register the TickerAnalyst sub-agent tool
        self.add_tool(
            name=TICKER_ANALYST_TOOL["name"],
            description=TICKER_ANALYST_TOOL["description"],
            parameters=TICKER_ANALYST_TOOL["parameters"],
            function=TICKER_ANALYST_TOOL["function"],
        )


def main():
    task = "Review/compare the two tickers AAL and JBLU."
    agent = SimpleBaseAgent(
        task=task,
    )
    result = agent.run()
    print(result)


if __name__ == "__main__":
    main()

