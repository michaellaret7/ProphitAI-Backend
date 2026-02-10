"""OrchestratorAgent - Decomposes complex tasks and delegates to worker agents."""

from typing import Optional, List, Dict, Any

from app.core.atlas.agents.base import AgentBase
from app.core.atlas.models import PrintMode, NoOpChatCallback
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.worker_agent.setup import DEPLOY_WORKER_TOOL
from app.core.atlas.tools.base.search_engine import LLM_WEB_SEARCH_TOOL
from app.core.atlas.prompts.chat_agent_prompts.orchestrator_agent import ORCHESTRATOR_SYSTEM_PROMPT

class OrchestratorAgent(AgentBase):
    """Decomposes complex tasks and delegates sub-tasks to worker agents.

    The orchestrator's only action tools are think and deploy_worker_agent.
    It plans the work, spawns focused workers with scoped tool sets,
    and synthesizes their results into a final answer.
    """

    def __init__(
        self,
        task: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 50,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
    ):
        provider = provider or "gemini"
        model = model or "gemini-3-pro-preview"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.task = task

        # Attributes required by ExecutionLoop and ToolHandler (duck typing)
        self.chat_callback = NoOpChatCallback()
        self.session_id = "orchestrator"
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(self, self.printer, chat_callback=self.chat_callback)
        self.execution_loop = ExecutionLoop(self)

        # Register orchestrator-specific tools (think + calculator come from AgentBase)
        self.add_tool(**DEPLOY_WORKER_TOOL)
        self.add_tool(**LLM_WEB_SEARCH_TOOL)

    def run(self) -> Dict[str, Any]:
        """Execute the orchestrator's task decomposition and delegation loop."""
        self.messages = [
            {"role": "system", "content": ORCHESTRATOR_SYSTEM_PROMPT},
            {"role": "user", "content": self.task},
        ]

        result = self.execution_loop.execute()

        return {
            "answer": result["answer"],
            "tool_calls_made": result["tool_calls"],
            "tokens_used": result["total_tokens"],
            "iterations": result["iterations"],
            "stop_reason": result["stop_reason"],
        }


if __name__ == "__main__":
    orchestrator_agent = OrchestratorAgent(
        task="Write me an in depth research report on CUBE and give an investment thesis for the company(whether to buy, sell, or hold).",
        provider="anthropic",
        model="claude-opus-4-6",
        max_iterations=50,
        print_mode=PrintMode.PRODUCTION,
        temperature=0.7,
    )
    result = orchestrator_agent.run()
    print(result["answer"])
    for i, msg in enumerate(orchestrator_agent.messages):
        # Handle both dict and Pydantic message objects
        m = msg if isinstance(msg, dict) else msg.model_dump()
        print(f"\n{'='*60}")
        print(f"Message {i} | Role: {m.get('role', 'N/A')}")
        print(f"{'='*60}")
        if m.get("content"):
            print(m["content"])
        if m.get("tool_calls"):
            for tc in m["tool_calls"]:
                fn = tc if isinstance(tc, dict) else tc.model_dump()
                fn = fn.get("function", fn)
                print(f"\n  Tool Call: {fn.get('name')}")
                print(f"  Args: {fn.get('arguments')}")