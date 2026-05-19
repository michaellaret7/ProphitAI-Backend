"""Validator Agent — Stage 6 of the fund pipeline.

Takes a fully-built strategy in the sandbox plus its upstream artifacts
(idea text, manifest, execution result) and produces a pass/fail verdict
on whether the strategy shows a pulse at reasonable params. Screens the
universe, populates ticker_universe.py, runs up to 12 vectorized backtests
across a bounded tuning grid, and writes the verdict to past_ideas.md.

Explicitly not an optimizer. Rule/param optimization is the future
Testing Agent's job — this agent answers "is it alive?" only.
"""

from functools import partial
from pathlib import Path
from typing import Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_shared.time_utils import get_current_utc_time

from prophitai_atlas.tools.base.worker_agent.deploy_scoped import (
    DEPLOY_SCOPED_WORKER_TOOL,
    deploy_scoped_worker,
)

from prophitai_fund.tools import append_memory, build_skill, edit_skill, load_skill, past_ideas, retrieve_memory
from prophitai_fund.tools.worker_registry import WORKERS
from prophitai_fund.validation.models import ValidationVerdict
from prophitai_fund.validation.tool_registry import VALIDATOR_TOOLS


class ValidatorAgent:
    """Runs the validation stage against a fully-built strategy in the sandbox.

    Screens the universe → writes ticker_universe.py → runs up to 12 vectorized
    backtests tuning only `config_defaults.strategy` + `.sizing` → picks the
    highest Sharpe → marks passed (>0.5) or failed in past_ideas.md.

    The agent reads IDEA.md and MANIFEST.json directly from the sandbox — the
    caller only has to pass `strategy_id`.
    """

    DEFAULT_TASK_TEMPLATE = (
        "Validate the built strategy at "
        "`strategies/development/{strategy_id}/`. Read IDEA.md and MANIFEST.json "
        "from that directory to get the universe criteria and tunable params. "
        "Screen the universe into a concrete ticker list, write them to "
        "`ticker_universe.py`, run the vectorized backtest up to 12 times across "
        "a bounded tuning grid on strategy + sizing params only, then mark the "
        "verdict in past_ideas.md (passed if best Sharpe > 0.5, else failed).\n\n"
        "STRATEGY ID: {strategy_id}"
    )

    def __init__(
        self,
        *,
        sandbox_id: str,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "validator",
        model: Optional[str] = None,
        print_mode: PrintMode = PrintMode.VERBOSE,
    ):
        date = get_current_utc_time().strftime("%m/%d/%Y")
        prompt_path = Path(__file__).parent / "system.md"
        system_prompt = prompt_path.read_text().format(date=date, sandbox_id=sandbox_id)

        self.agent = Agent(
            tools=VALIDATOR_TOOLS,
            system_prompt=system_prompt,
            chat_callback=chat_callback,
            session_id=session_id,
            model=model,
            print_mode=print_mode,
        )

        self.memory_file = Path(__file__).parent / "memory.md"
        self.ideas_file = Path(__file__).parent.parent / "past_ideas.md"

        skills_dir = Path(__file__).parent / "skills"
        skills_dir.mkdir(exist_ok=True)

        self.agent.add_tool(**{**append_memory.tool, "function": partial(append_memory, self.memory_file)})
        self.agent.add_tool(**{**retrieve_memory.tool, "function": partial(retrieve_memory, self.memory_file)})
        self.agent.add_tool(**{**load_skill.tool, "function": partial(load_skill, skills_dir)})
        self.agent.add_tool(**{**build_skill.tool, "function": partial(build_skill, skills_dir)})
        self.agent.add_tool(**{**edit_skill.tool, "function": partial(edit_skill, skills_dir)})
        self.agent.add_tool(**{**past_ideas.tool, "function": partial(past_ideas, self.ideas_file)})

        self.agent.add_tool(
            **DEPLOY_SCOPED_WORKER_TOOL,
            function=partial(
                deploy_scoped_worker,
                self.agent.notebook,
                chat_callback or NoOpChatCallback(),
                None,
                WORKERS,
            ),
        )

    def _build_context_history(self) -> list[dict]:
        """Pre-read memory file into conversation history messages."""
        memory_content = (
            self.memory_file.read_text(encoding="utf-8").strip()
            if self.memory_file.exists()
            else "No memories recorded yet."
        )

        return [
            {"role": "user", "content": f"<your_memory>\n{memory_content}\n</your_memory>"},
            {"role": "assistant", "content": "Memory loaded. Ready to begin."},
        ]

    def run(self, strategy_id: str) -> AgentResponse:
        """Validate a built strategy end-to-end.

        The agent reads IDEA.md + MANIFEST.json from the sandbox on its own.

        Args:
            strategy_id: Snake_case strategy identifier (e.g. 'omfm_15').
                Used to resolve `strategies/development/{strategy_id}/` paths
                inside the sandbox.

        Returns:
            AgentResponse with parsed_output containing a ValidationVerdict.
        """
        task = self.DEFAULT_TASK_TEMPLATE.format(strategy_id=strategy_id)
        context_history = self._build_context_history()

        return self.agent.run(
            task,
            conversation_history=context_history,
            plan_first=True,
            format_output=ValidationVerdict,
        )
