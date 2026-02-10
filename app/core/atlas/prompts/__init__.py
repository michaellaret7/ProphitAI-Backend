"""Prompt templates for agents."""

from .universal import UNIVERSAL_AGENT_MESSAGE
from .chat import CHAT_SYSTEM_PROMPT
from .reminders import THINK_DEEPLY_MESSAGE, get_finalize_rejected_message
from .utils import remove_system_messages
from .worker import WORKER_SYSTEM_PROMPT

__all__ = [
    "UNIVERSAL_AGENT_MESSAGE",
    "CHAT_SYSTEM_PROMPT",
    "THINK_DEEPLY_MESSAGE",
    "get_finalize_rejected_message",
    "remove_system_messages",
    "WORKER_SYSTEM_PROMPT",
]
