"""ChatAgent - Conversational agent for interactive tool-assisted chat.

Optimized for fast, interactive conversations with bounded iterations.
Shares infrastructure with BaseAgent (ToolHandler, parallel execution, tool library).
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Callable, Optional, TYPE_CHECKING

from app.core.agentic_framework.tool_lib.foundry_tools.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.utils.choose_model_and_client import get_model_and_client
from app.core.agentic_framework.base_agent.utils.models import PrintMode

from .models import ChatResponse, ChatSession
from .prompts import CHAT_SYSTEM_PROMPT
from .execution_loop import ChatExecutionLoop
from .base_tool_registry import register_chat_tools

# ANSI color codes for terminal formatting
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_BLUE = "\033[34m"
_RESET = "\033[0m"

if TYPE_CHECKING:
    pass

# Import ToolHandler at runtime (duck typing will work for ChatAgent)
from app.core.agentic_framework.base_agent.execution.tool_handler import ToolHandler  # noqa: E402

# IDEA: The tool calls and their results in the mini execution loop get cached in the chat agent class and then the tool call names and ids get stored in the chat session class so that the llm knows what tools were called.
# Then we can have a tool called pull from cache that pulls the tool call results from the chat agent class and returns them to the llm, instead of having to re-execute the tool calls.

class ChatAgent:
    """Conversational agent for interactive tool-assisted chat.

    Key differences from BaseAgent:
    - No planning phase - direct to tool calling
    - Bounded iterations (default: 5)
    - Terminates when LLM produces text without tool calls
    - Optimized for fast, interactive use cases

    Example:
        agent = ChatAgent()
        response = agent.run("Search for AAPL earnings guidance")
        print(response.answer)
    """

    def __init__(
        self,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        max_iterations: int = 20,
        print_mode: PrintMode = PrintMode.PRODUCTION,
        temperature: Optional[float] = None,
        system_prompt: Optional[str] = None,
    ):
        """Initialize the ChatAgent.

        Args:
            provider: LLM provider (openai, anthropic, etc). Defaults to env var.
            model: Model name. Defaults to provider's env var.
            max_iterations: Max LLM round-trips (default: 5)
            print_mode: Output verbosity level
            temperature: LLM temperature (defaults to provider default)
            system_prompt: Custom system prompt (defaults to CHAT_SYSTEM_PROMPT)
        """
        # LLM client setup (reuse get_model_and_client)
        if provider is None:
            provider = "openai"  # Default provider

        self.model, self.client = get_model_and_client(provider='anthropic', model='claude-sonnet-4-5-20250929')

        # Configuration
        self.max_iterations = max_iterations
        self.print_mode = print_mode
        self.temperature = temperature
        self.system_prompt = system_prompt or CHAT_SYSTEM_PROMPT

        # Tool registry (same structure as BaseAgent)
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable] = {}
        self.tool_schemas: Dict[str, Any] = {}

        # Token tracking
        self.total_tokens: int = 0

        # Message history (set per request)
        self.messages: List[Dict[str, Any]] = []

        # Execution components
        # ToolHandler expects BaseAgent, but ChatAgent provides compatible interface (duck typing)
        self.tool_handler = ToolHandler(self)  # type: ignore[arg-type]
        self.execution_loop = ChatExecutionLoop(self)

        # Attributes expected by ToolHandler (BaseAgent compatibility)
        self.simulation_date = None  # ChatAgent doesn't use simulation
        self.note_titles: List[str] = []  # For write_note compatibility
        self.output_dir = None  # No YAML logging for chat

        # Register chat tools
        register_chat_tools(self)
        self.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Build the message list for the LLM call.

        Args:
            user_message: Current user query
            conversation_history: Previous messages

        Returns:
            List of messages in OpenAI format
        """
        messages = []

        # System prompt
        messages.append({
            "role": "system",
            "content": self.system_prompt
        })

        # Add conversation history if provided
        if conversation_history:
            for msg in conversation_history:
                # Only include user/assistant messages from history
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })

        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    @staticmethod
    def _format_markdown(text: str) -> str:
        """Convert markdown to ANSI-colored terminal output."""
        lines = text.split("\n")
        formatted = []

        for line in lines:
            if line.startswith("###"):
                line = f"{_BLUE}{_BOLD}{line.lstrip('#').strip()}{_RESET}"
            elif line.startswith("##"):
                line = f"{_CYAN}{_BOLD}{line.lstrip('#').strip()}{_RESET}"
            elif line.startswith("#"):
                line = f"{_GREEN}{_BOLD}{line.lstrip('#').strip()}{_RESET}"
            else:
                # Bold: **text** -> bold
                line = re.sub(r"\*\*(.+?)\*\*", rf"{_BOLD}\1{_RESET}", line)
                # Italic: *text* -> dim (avoid matching ** patterns)
                line = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", rf"{_DIM}\1{_RESET}", line)

            formatted.append(line)

        return "\n".join(formatted)
    
    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ) -> None:
        """Register a tool with the agent.

        Same signature as BaseAgent.add_tool() for compatibility.

        Args:
            name: Tool name (used in tool calls)
            description: Description of what the tool does
            parameters: JSON Schema for tool parameters
            function: Python callable to execute
        """
        # Store function for execution
        self.tool_functions[name] = function
        self.tool_schemas[name] = parameters

        # Add to tools list (OpenAI function calling format)
        self.tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
    
    def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        """Run the agent execution loop for a user query.

        Args:
            user_message: The user's query
            conversation_history: Previous messages (optional, from ChatSession.get_history())

        Returns:
            ChatResponse with answer, tool_calls_made, tokens_used, iterations
        """
        # Reset state for new request
        self.total_tokens = 0
        self.tool_handler.tool_call_history = []

        # Build messages from history + system prompt + new query
        self.messages = self._build_messages(user_message, conversation_history)

        # Run mini execution loop
        result = self.execution_loop.execute()

        return ChatResponse(
            answer=result["answer"],
            tool_calls_made=result["tool_calls"],
            tokens_used=result["total_tokens"],
            iterations=result["iterations"],
            stop_reason=result["stop_reason"]
        )
    
    def run_interactive(self, session_id: str = "interactive") -> None:
        """Start an interactive chat session in the terminal.

        Args:
            session_id: Identifier for the session (default: "interactive")
        """
        print("=" * 60)
        print("ChatAgent Interactive Session")
        print("Press Ctrl+C to exit")
        print("=" * 60)

        session = ChatSession(session_id=session_id)

        while True:
            try:
                user_input = input("\n[You]: ").strip()

                if not user_input:
                    continue

                response = self.run(user_input, session.get_history())

                session.add_user_message(user_input)
                session.add_assistant_message(response.answer)

                print(f"\n[Agent]: {self._format_markdown(response.answer)}")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue


if __name__ == "__main__":
    agent = ChatAgent(
        provider='fireworks',
        model='Kimi-K2.5'
    )
    agent.run_interactive()