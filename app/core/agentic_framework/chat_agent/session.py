"""ChatAgent session management."""

from dataclasses import dataclass, field
from typing import List, Dict, Any

@dataclass
class ChatSession:
    """Manages conversation state across multiple turns."""

    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation history."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation history."""
        self.messages.append({"role": "assistant", "content": content})

    def get_history(self, max_messages: int = 20) -> List[Dict[str, Any]]:
        """Get recent conversation history."""
        filtered = [m for m in self.messages if m.get("role") in ("user", "assistant")]
        return filtered[-max_messages:]

    def clear(self) -> None:
        """Clear the conversation history."""
        self.messages = []
