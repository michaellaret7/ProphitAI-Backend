"""AgentBase - Abstract base class for all agents."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional, Union

from prophitai_atlas.models import PrintMode, ChatCallback, NoOpChatCallback
from prophitai_shared import get_backend
from prophitai_atlas.execution import ExecutionLoop, ToolHandler
from prophitai_atlas.logging import AgentPrinter
from prophitai_atlas.observability import LangfuseObserver

from prophitai_atlas.tools.base import think, calculator

class AgentBase(ABC):
    """Abstract base class providing shared foundation for all Atlas agents.

    Provides the full execution contract required by ExecutionLoop and ToolHandler:
    LLM client, tool registry, execution state, session callbacks, and execution components.
    Subclasses override max_iterations to fit their use case (e.g. Agent=200, PlannerAgent=5).
    """

    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 100,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "default",
    ):
        # Observability
        self.observer = LangfuseObserver()

        # LLM client setup
        self.provider = provider
        self.backend = get_backend(provider=provider, model=model)
        self.model = self.backend.model
        self.client = self.backend.raw_client

        # Configuration
        self.max_iterations = max_iterations
        self.print_mode = print_mode
        self.temperature = temperature

        # Session state
        self.chat_callback: Union[ChatCallback, NoOpChatCallback] = (
            chat_callback if chat_callback is not None else NoOpChatCallback()
        )
        self.session_id: str = session_id

        # Tool registry
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Any] = {}

        # Execution state
        self.messages: List[Dict[str, Any]] = []
        self.total_tokens: int = 0
        self.cache_creation_input_tokens: int = 0
        self.cache_read_input_tokens: int = 0

        # Execution components
        self.printer = AgentPrinter(self.print_mode)

        self.tool_handler = ToolHandler(
            self,
            self.printer,
            observer=self.observer,
            chat_callback=self.chat_callback,
        )
        
        self.execution_loop = ExecutionLoop(self, observer=self.observer)

        # ---- Register default tools ---- #
        if self.provider not in ('openai', 'anthropic'):
            self.add_tool(**think.tool)

        self.add_tool(**calculator.tool)

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ) -> None:
        """Register a tool for the agent to use. Skips if already registered."""

        # ------ Skip if tool already registered. This gates dupe tool registration for worker agents. ------ #
        if name in self.tool_functions:
            return

        tool_def = {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function
        self.tool_schemas[name] = parameters

    def remove_tool(self, name: str) -> None:
        """Unregister a tool by name. No-op if not registered."""
        if name not in self.tool_functions:
            return
        del self.tool_functions[name]
        del self.tool_schemas[name]
        self.tools = [t for t in self.tools if t["name"] != name]

    def get_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self.tool_functions.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tool_functions

    def get_trace_name(self, *, planned: bool = False) -> str:
        """Return the Langfuse trace name for this concrete agent class."""
        agent_name = self.__class__.__name__
        return f"{agent_name} (planned)" if planned else agent_name

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the agent's main loop. Subclasses must implement."""
        pass
