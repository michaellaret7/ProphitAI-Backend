"""ChatAgent - Conversational agent for interactive tool-assisted chat."""

from __future__ import annotations

import os
import re
from typing import List, Dict, Any, Optional, Union

from app.core.atlas.models import (
    PrintMode,
    ChatResponse,
    ChatSession,
    ChatCallback,
    NoOpChatCallback,
)
from app.core.atlas.prompts import CHAT_SYSTEM_PROMPT
from app.core.atlas.execution import ChatExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter

from .base import AgentBase
from app.core.atlas.tools.foundry.credit_research import CREDIT_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.macro_research import MACRO_RESEARCH_SEARCH_TOOL
from app.core.atlas.tools.foundry.earnings_calls import EARNINGS_CALL_SEARCH_TOOL
from app.core.atlas.tools.foundry.user_uploads import USER_UPLOAD_SEARCH_TOOL
from app.core.atlas.tools.foundry.tax_research import TAX_RESEARCH_SEARCH_TOOL

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
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
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

        self.system_prompt = system_prompt if system_prompt else CHAT_SYSTEM_PROMPT

        # Chat streaming callback - defaults to no-op if not provided
        self.chat_callback: Union[ChatCallback, NoOpChatCallback] = (
            chat_callback if chat_callback is not None else NoOpChatCallback()
        )

        # Session identifier for callback events
        self.session_id: str = "default"

        # Execution components
        self.printer = AgentPrinter(self.print_mode)
        self.tool_handler = ToolHandler(
            self, self.printer, chat_callback=self.chat_callback
        )  
        self.execution_loop = ChatExecutionLoop(self)

        # Attributes expected by ToolHandler (BaseAgent compatibility)
        self.simulation_date = None
        self.note_titles: List[str] = []
        self.output_dir = None

        print(f"Initialized Agent with model: {self.model} (provider: {self.provider})")

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

        # Set session_id for callback events
        self.session_id = session_id
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
        provider='anthropic',
        # model='claude-opus-4-5-20251101',
        model='claude-opus-4-6',
        print_mode=PrintMode.PRODUCTION
    )
    # agent.add_tool(**CREDIT_RESEARCH_SEARCH_TOOL)
    # agent.add_tool(**MACRO_RESEARCH_SEARCH_TOOL)
    # agent.add_tool(**EARNINGS_CALL_SEARCH_TOOL)
    # agent.add_tool(**USER_UPLOAD_SEARCH_TOOL)
    agent.add_tool(**TAX_RESEARCH_SEARCH_TOOL)
    agent.run_interactive(session_id="test")


    
