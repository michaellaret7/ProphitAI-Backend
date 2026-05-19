"""Idea Generator Agent — autonomous trade idea generation.

Researches trading strategies via RAG tools (strategy_research, theory_research),
combines findings with macro context, and produces a structured trade idea
with implementation guidelines. Does NOT select specific tickers or build portfolios.
"""

from functools import partial
from pathlib import Path
from typing import Optional, List, Union

from pydantic import BaseModel, Field

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_fund.idea_generation.tool_registry import IDEA_GENERATOR_TOOLS
from prophitai_fund.tools import append_memory, past_ideas, retrieve_memory

class IdeaGeneratorAgent:
    """Autonomous trade idea generator.

    Runs without user input. Researches trading strategies via RAG tools
    and generates a trade idea with implementation guidelines.
    Does not select specific tickers or build portfolios.
    """

    DEFAULT_TASK = (
        "Research and generate a novel trading strategy idea. "
        "Use the research tools extensively to find a compelling edge, "
        "assess its macro viability, check past ideas to avoid repetition, "
        "and produce a complete trade idea proposal."
        "Goal: Build an equity focused long short equity momentum trading strategy. Keep it super simple, have it be technical driven signals only(this means only price data), "
        "and have the data be 15 minute bars. Do not overcomplicate the strategy, keep it simple and technical."
    )

    def __init__(
        self,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "idea_generation",
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.VERBOSE,
    ):
        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system.md"
        system_prompt = prompt_path.read_text().format(date=date)

        self.agent = Agent(
            tools=IDEA_GENERATOR_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            model=model or "anthropic/claude-opus-4.7",
            print_mode=print_mode,
        )

        self.memory_file = Path(__file__).parent / "memory.md"
        self.ideas_file = Path(__file__).parent.parent / "past_ideas.md"

        self.agent.add_tool(**{**append_memory.tool, "function": partial(append_memory, self.memory_file)})
        self.agent.add_tool(**{**retrieve_memory.tool, "function": partial(retrieve_memory, self.memory_file)})
        self.agent.add_tool(**{**past_ideas.tool, "function": partial(past_ideas, self.ideas_file)})
        
    def _build_context_history(self) -> List[dict]:
        """Pre-read memory and past ideas files into conversation history messages."""
        memory_content = (
            self.memory_file.read_text(encoding="utf-8").strip()
            if self.memory_file.exists()
            else "No memories recorded yet."
        )

        ideas_content = (
            self.ideas_file.read_text(encoding="utf-8").strip()
            if self.ideas_file.exists()
            else "No past ideas recorded yet."
        )

        return [
            {
                "role": "user",
                "content": (
                    f"<your_memory>\n{memory_content}\n</your_memory>\n\n"
                    f"<past_ideas>\n{ideas_content}\n</past_ideas>"
                ),
            },
            {
                "role": "assistant",
                "content": "Context loaded. I've reviewed my memory entries and all past strategy ideas. Ready to begin.",
            },
        ]

    def run(self, task: Optional[str] = None) -> AgentResponse:
        """Execute the idea generator agent.

        Args:
            task: Optional task override. Defaults to autonomous strategy discovery.

        Returns:
            AgentResponse with answer, parsed_output (StrategyIdea), and metadata.
        """
        context_history = self._build_context_history()

        return self.agent.run(
            task or self.DEFAULT_TASK,
            conversation_history=context_history,
            plan_first=True,
        )



if __name__ == "__main__":
    agent = IdeaGeneratorAgent()
    response = agent.run()
    print(response)