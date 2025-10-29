"""Simple Base Agent - Phase 1

Minimal autonomous agent with clean separation of concerns.
"""

from typing import List, Dict, Any, Callable, Union
from dotenv import load_dotenv
from app.core.agentic_framework.base_agent_v2.utils.resolve_llm import resolve_llm_and_client
from app.core.agentic_framework.base_agent_v2.execution.execution_loop import ExecutionLoop
from app.core.agentic_framework.base_agent_v2.execution.tool_handler import ToolHandler
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode
from app.core.agentic_framework.base_agent_v2.tool_registry import register_base_tools
from app.core.agentic_framework.base_agent_v2.utils.path_utils import create_agent_output_dir
from app.core.agentic_framework.base_agent_v2.logging.notes import ensure_notes_file

load_dotenv()

class BaseAgent:
    """Minimal autonomous agent implementing ReAct pattern.

    Responsibilities:
    - Initialize LLM client and configuration
    - Manage tool registry
    - Coordinate execution loop and tool handler
    - Return structured results
    """

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str = None,
        provider: str = None,
        max_iterations: int = 30,
        print_mode: Union[str, PrintMode] = PrintMode.VERBOSE,
        reasoning_effort: str = None,
        temperature: float = None,
        plan_first: bool = True,
    ):
        """Initialize agent.

        Args:
            system_prompt: System instructions for the agent
            user_prompt: User task/query
            model: LLM model name
            max_iterations: Maximum number of ReAct iterations
            print_mode: Output verbosity ('production', 'verbose', or 'debug')
            reasoning_effort: Reasoning effort level
            temperature: Temperature for the API call
        """
        self.provider = provider
        self.model, self.client = resolve_llm_and_client(provider=self.provider, model=model)

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
      
        self.print_mode = print_mode

        # API Call parameters
        self.reasoning_effort = reasoning_effort
        self.temperature = temperature

        # State and planning args
        self.plan_first = plan_first
        self.plan = None  # Parsed plan from planning phase

        # Tool registry
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Any] = {}

        # Execution state
        self.messages: List[Dict[str, Any]] = []
        self.total_tokens: int = 0

        # Agent identity and per-run output location
        self.agent_name = self.__class__.__name__
        self.output_dir = create_agent_output_dir(self.agent_name)
        ensure_notes_file(getattr(self, "output_dir", None), getattr(self, "agent_name", "Agent"))

        # Initialize components
        self.tool_handler = ToolHandler(self)
        self.execution_loop = ExecutionLoop(self)

        # Base Tool Registry
        register_base_tools(self)

        print(f"Initialized Agent with model: {self.model}")

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable
    ) -> None:
        """Register a tool for the agent to use.

        Args:
            name: Tool name
            description: Tool description for LLM
            parameters: JSON schema for parameters
            function: Python callable
        """
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function
        self.tool_schemas[name] = parameters

        print(f"Registered tool: {name}")

    def run(self) -> Dict[str, Any]:
        """Execute the agent's main ReAct loop.

        Returns:
            Dictionary with final_answer, iterations, total_tokens, stop_reason
        """
        # Build initial messages
        self.messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "system", "content": "## PER-TURN OUTPUT SCHEMA\nThinking: Why this step? What am I getting out of this step? Is this step productive and helpful? Be thorough, detailed, and precise in your thinking. \nNextStep: next actionable step to take.\n"},
            {"role": "user", "content": self.user_prompt}
        ]

        print(f"\n{'='*60}")
        print(f"Starting agent run")
        print(f"Task: {self.user_prompt}")
        print(f"{'='*60}\n")

        # Delegate to execution loop
        result = self.execution_loop.execute()

        print(f"\n{'='*60}")
        print(f"Agent run complete")
        print(f"Iterations: {result['iterations']}")
        print(f"Total tokens: {result['total_tokens']}")
        print(f"Stop reason: {result['stop_reason']}")
        print(f"{'='*60}\n")

        return result
