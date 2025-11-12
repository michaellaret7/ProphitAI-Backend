from datetime import datetime
from datetime import datetime
from typing import Any, Dict, Optional

from app.core.agentic_framework.base_agent.agent import BaseAgent
from app.core.agentic_framework.tool_lib.sub_agents.sector_analyst import (
    SECTOR_ANALYST_TOOL,
)

SIMPLE_BASE_AGENT_SYSTEM_PROMPT = """
You are a delegator agent.

Your ONLY job:
- Immediately call the `run_sector_analyst` tool with the full user prompt as the `task` parameter.
- Do not perform additional analysis yourself.
- After the tool returns, call `finalize` with the tool's output as the final answer.
"""


class SimpleBaseAgent(BaseAgent):
    """
    Minimal base agent that registers the SectorAnalyst sub-agent as a tool
    and delegates execution to it. The LLM is explicitly instructed to run
    the sub-agent tool and finalize the result.
    """

    def __init__(
        self,
        task: str,
        *,
        provider: Optional[str] = "anthropic",
        model: Optional[str] = "claude-haiku-4-5-20251001",
        simulation_date: Optional[datetime] = None,
    ) -> None:
        super().__init__(
            system_prompt=SIMPLE_BASE_AGENT_SYSTEM_PROMPT,
            user_prompt=task,
            provider=provider,
            model=model,
            plan_first=True,
            max_iterations=10,
            temperature=0.7,
        )
        self.simulation_date = simulation_date

        # Register the SectorAnalyst sub-agent tool
        self.add_tool(
            name=SECTOR_ANALYST_TOOL["name"],
            description=SECTOR_ANALYST_TOOL["description"],
            parameters=SECTOR_ANALYST_TOOL["parameters"],
            function=SECTOR_ANALYST_TOOL["function"],
        )


def main():
    task = "Review the real estate sector and provide a comprehensive assessment of the sector. Use the available tools to gather evidence before making conclusions. Be concise in your final answer."
    agent = SimpleBaseAgent(
        task=task,
        simulation_date=datetime(2023, 1, 1),
    )
    result = agent.run()
    print(result)


if __name__ == "__main__":
    main()

