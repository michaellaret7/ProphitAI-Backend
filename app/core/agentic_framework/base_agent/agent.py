"""Simple Base Agent - Phase 1

Minimal autonomous agent with clean separation of concerns.
"""

from typing import List, Dict, Any, Callable, Union, Optional
from datetime import datetime

from dotenv import load_dotenv

from app.core.agentic_framework.base_agent.callbacks import NoOpCallback, StateCallback
from app.core.agentic_framework.base_agent.execution.execution_loop import ExecutionLoop
from app.core.agentic_framework.base_agent.execution.tool_handler import ToolHandler
from app.core.agentic_framework.base_agent.logging.notes import ensure_notes_file
from app.core.agentic_framework.base_agent.tool_registry import register_base_tools
from app.core.agentic_framework.base_agent.utils.agent_message import UNIVERSAL_AGENT_MESSAGE
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.utils.path_utils import create_agent_output_dir
from app.core.agentic_framework.base_agent.utils.resolve_llm import resolve_llm_and_client

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
        max_iterations: int = 100,
        print_mode: Union[str, PrintMode] = PrintMode.VERBOSE,
        reasoning_effort: str = None,
        temperature: float = None,
        plan_first: bool = True,
        simulation_date: Optional[datetime] = None,
        state_callback: Optional[StateCallback] = None,
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
            simulation_date: Optional datetime for backtesting. If provided, automatically
                           injects _simulation_date into all tool calls to enable historical
                           data filtering and prevent look-ahead bias.
            state_callback: Optional callback for streaming task state updates to frontend.
                          Defaults to NoOpCallback (does nothing).
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
        self.simulation_date = simulation_date  # For simulation mode: inject _simulation_date into all tool calls
        self.state_callback = state_callback if state_callback is not None else NoOpCallback() # this is new for the purposes of showing the agent stream on the frontend

        # Tool registry
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Any] = {}

        # Execution state
        self.messages: List[Dict[str, Any]] = []
        self.total_tokens: int = 0
        self.note_titles: List[str] = []  # Track note titles for display

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

    # NOTE: add a register tool function that takes a list of tool schemas and runs this add tool code internally. This will normalize the tool registration process.
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
            {"role": "system", "content": UNIVERSAL_AGENT_MESSAGE},
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]

        if self.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG, PrintMode.PRODUCTION]:
            print(f"\n{'='*60}")
            print(f"Starting agent run")
            print(f"Task: {self.user_prompt}")
            print(f"{'='*60}\n")
        elif self.print_mode == PrintMode.SUBAGENT:
            print(f"Starting sub-agent run")
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
