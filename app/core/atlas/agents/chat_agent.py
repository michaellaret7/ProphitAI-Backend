"""ChatAgent - Conversational agent for interactive tool-assisted chat."""

from __future__ import annotations

import re
from typing import List, Dict, Any, Optional

from app.core.agentic_framework.tool_lib.foundry_tools.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.core.atlas.models import PrintMode, ChatResponse, ChatSession
from app.core.atlas.prompts import CHAT_SYSTEM_PROMPT
from app.core.atlas.execution import ChatExecutionLoop
from app.core.agentic_framework.chat_agent.base_tool_registry import register_chat_tools
from app.core.agentic_framework.base_agent.execution.tool_handler import ToolHandler

from .base import AgentBase

# ANSI color codes for terminal formatting
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[36m"
_GREEN = "\033[32m"
_BLUE = "\033[34m"
_RESET = "\033[0m"


class ChatAgent(AgentBase):
    """Conversational agent for interactive tool-assisted chat.

    Key differences from DeepAgent:
    - No planning phase - direct to tool calling
    - Bounded iterations (default: 20)
    - Terminates when LLM produces text without tool calls
    - Optimized for fast, interactive use cases
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
        if provider is None:
            provider = "fireworks"
        if model is None:
            model = "Kimi-K2-instruct"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.system_prompt = system_prompt or CHAT_SYSTEM_PROMPT

        # Execution components
        self.tool_handler = ToolHandler(self)  # type: ignore[arg-type]
        self.execution_loop = ChatExecutionLoop(self)

        # Attributes expected by ToolHandler (BaseAgent compatibility)
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        self.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> List[Dict[str, Any]]:
        """Build the message list for the LLM call."""
        messages = []

        messages.append({
            "role": "system",
            "content": self.system_prompt
        })

        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })

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
                line = re.sub(r"\*\*(.+?)\*\*", rf"{_BOLD}\1{_RESET}", line)
                line = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", rf"{_DIM}\1{_RESET}", line)

            formatted.append(line)

        return "\n".join(formatted)

    def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> ChatResponse:
        """Run the agent execution loop for a user query."""
        self.total_tokens = 0
        self.tool_handler.tool_call_history = []

        self.messages = self._build_messages(user_message, conversation_history)

        result = self.execution_loop.execute()

        return ChatResponse(
            answer=result["answer"],
            tool_calls_made=result["tool_calls"],
            tokens_used=result["total_tokens"],
            iterations=result["iterations"],
            stop_reason=result["stop_reason"]
        )

    def run_interactive(self, session_id: str = "interactive") -> None:
        """Start an interactive chat session in the terminal."""
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
        provider=None,
        model=None,
        print_mode=PrintMode.PRODUCTION
    )
    agent.run_interactive(session_id="test")
    
