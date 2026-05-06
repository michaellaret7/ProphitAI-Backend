"""Chat agent — interactive financial research analyst.

Composes an Agent with chat-specific prompt, tools, and configuration.
Unlike WatchlistAgent/PortfolioBuilderAgent, this is a long-lived agent
that handles multiple messages within a session.
"""

from typing import Any, Dict, List, Optional, Union

from prophitai_atlas.agents import Agent
from prophitai_atlas.models import PrintMode, AgentResponse
from prophitai_atlas.models.callbacks import ChatCallback, NoOpChatCallback
from prophitai_atlas.tools.base.worker_agent.deploy_general import (
    deploy_general_worker,
    DEPLOY_GENERAL_WORKER_TOOL,
)
from prophitai_tools.registry import CHAT_TOOL_FUNCTIONS

from prophitai_api.agents.prompts import build_chat_system_prompt


class ChatAgent:
    """AI-powered financial research chat agent.

    Wraps Agent with chat-specific prompt, tools, and configuration.
    Exposes chat_callback as a settable property so the controller
    can wire a fresh WebSocket callback per-message.
    """

    def __init__(
        self,
        *,
        chat_callback: Optional[Union[ChatCallback, NoOpChatCallback]] = None,
        session_id: str = "chat",
        user_id: Optional[str] = None,
        provider: str = "anthropic",
        model: str = "claude-opus-4-7",
        # provider: str = "grok",
        # model: str = "grok-4.3",
        max_iterations: int = 200,
        print_mode: PrintMode = PrintMode.PRODUCTION,
    ):
        chat_prompt = build_chat_system_prompt()

        self._agent = Agent(
            provider=provider,
            model=model,
            print_mode=print_mode,
            # temperature=temperature,
            max_iterations=max_iterations,
            user_id=user_id,
            deferred_tools=CHAT_TOOL_FUNCTIONS,
            system_prompt=chat_prompt,
            chat_callback=chat_callback,
        )

        self._agent.session_id = session_id

        self._agent.add_tool(
            **DEPLOY_GENERAL_WORKER_TOOL,
            function=lambda **kwargs: deploy_general_worker(
                notebook=self._agent.notebook,
                chat_callback=self._agent.chat_callback,
                user_id=user_id,
                provider="grok",
                model="grok-4.20-0309-non-reasoning",
                **kwargs,
            ),
        )

    @property
    def chat_callback(self):
        """Get the current chat callback."""
        return self._agent.chat_callback

    @chat_callback.setter
    def chat_callback(self, value):
        """Set the chat callback (refreshed per-message for event loop safety)."""
        self._agent.chat_callback = value

    def run(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> AgentResponse:
        """Process a user message with conversation context.

        Args:
            message: The user's message.
            conversation_history: Previous conversation for context.

        Returns:
            AgentResponse with the assistant's answer.
        """
        return self._agent.run(message, conversation_history)
