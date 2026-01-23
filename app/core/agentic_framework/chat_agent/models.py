"""ChatAgent response models."""

from dataclasses import dataclass, field
from typing import List

@dataclass
class ChatResponse:
    """Response from ChatAgent.run()"""

    answer: str
    tool_calls_made: List[str] = field(default_factory=list)
    tokens_used: int = 0
    iterations: int = 0
    stop_reason: str = "answer_ready"
