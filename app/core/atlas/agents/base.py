"""AgentBase - Abstract base class for all agents."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Callable, Optional

from app.core.atlas.models import PrintMode
from app.utils.choose_model_and_client import get_model_and_client

from app.core.atlas.tools.base import CALCULATOR_TOOL, THINK_TOOL

class AgentBase(ABC):
    """Abstract base class providing shared foundation for DeepAgent and ChatAgent."""

    def __init__(
        self,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 100,
        print_mode: PrintMode = PrintMode.VERBOSE,
        temperature: Optional[float] = None,
    ):
        # LLM client setup
        self.provider = provider
        self.model, self.client = get_model_and_client(provider=provider, model=model)

        # Configuration
        self.max_iterations = max_iterations
        self.print_mode = print_mode
        self.temperature = temperature

        # Tool registry
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Any] = {}

        # Execution state
        self.messages: List[Dict[str, Any]] = []
        self.total_tokens: int = 0

        # ---- Register default tools ---- #
        self.add_tool(**THINK_TOOL)
        self.add_tool(**CALCULATOR_TOOL)

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ) -> None:
        """Register a tool for the agent to use."""
        tool_def = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function
        self.tool_schemas[name] = parameters
    
    def get_tool_names(self) -> List[str]:
        """Return list of registered tool names."""
        return list(self.tool_functions.keys())

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self.tool_functions

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the agent's main loop. Subclasses must implement."""
        pass
