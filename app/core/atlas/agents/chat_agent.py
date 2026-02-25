"""ChatAgent - Conversational agent for interactive tool-assisted chat."""

from __future__ import annotations

from typing import List, Dict, Any, Optional, Union

from app.core.atlas.models import (
    PrintMode,
    AgentResponse,
    ChatSession,
    ChatCallback,
    NoOpChatCallback,
)
from app.core.atlas.prompts import CHAT_SYSTEM_PROMPT
from app.core.atlas.execution import ExecutionLoop, ToolHandler
from app.core.atlas.logging import AgentPrinter

from .base import AgentBase

from langfuse import propagate_attributes

class ChatAgent(AgentBase):
    """Conversational agent for interactive tool-assisted chat.

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
            provider = "anthropic"
        if model is None:
            model = "claude-sonnet-4-6"

        super().__init__(
            provider=provider,
            model=model,
            max_iterations=max_iterations,
            print_mode=print_mode,
            temperature=temperature,
        )

        self.system_prompt = system_prompt if system_prompt is not None else CHAT_SYSTEM_PROMPT

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
        self.execution_loop = ExecutionLoop(self)

        # Attributes expected by ToolHandler (BaseAgent compatibility)
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

        #  Pull user conversation history from the session and inject into the messages list which will be passed to the LLM.
        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") in ("user", "assistant"):
                    messages.append({
                        "role": msg["role"],
                        "content": msg.get("content", "")
                    })

        #  Add the user's message to the messages list.
        messages.append({
            "role": "user",
            "content": user_message
        })

        return messages

    def run(self, user_message: str, conversation_history: Optional[List[Dict[str, Any]]] = None) -> AgentResponse:
        """Run the agent execution loop for a user query."""

        with self.langfuse.start_as_current_observation(
            as_type="span",
            name="chat_agent.run",
            input=user_message,
        ) as run_span:

            self.langfuse.update_current_trace(
                name="ChatAgent",
                input=user_message,
                metadata={
                    "provider": self.provider,
                    "model": self.model,
                    "max_iterations": str(self.max_iterations),
                },
            )

            self.total_tokens = 0

            self.messages = self._build_messages(user_message, conversation_history)

            with propagate_attributes(
                session_id=self.session_id,
                tags=["ChatAgent", self.provider],
                metadata={"model": self.model}
            ):
                result = self.execution_loop.execute()

            self.langfuse.update_current_trace(output=result["answer"])
            run_span.update(output=result["answer"])

            return AgentResponse( 
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

        self.session_id = session_id
        session = ChatSession(session_id=session_id)

        while True:
            try:
                user_input = input("\n[You]: ").strip()
                if not user_input:
                    continue

                response = self.run(user_input, session.get_history()) # Populate the messages list with the user's message and the conversation history.
                session.add_user_message(user_input) # Add the user's message to the session history.
                session.add_assistant_message(response.answer) # Add the agent's response to the session history.

                print(f"\n[Agent]: {response.answer}")

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError: {e}")
                continue


