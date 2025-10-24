"""Iteration tracker for Base Agent V2.

Simple tracking of agent iterations without heavy management overhead.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Iteration:
    """Record of a single agent iteration."""

    iteration_num: int
    iteration_type: str  # "thinking", "action", "observation", "reasoning", "general"
    content: str  # What agent said/did
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def has_tool_calls(self) -> bool:
        """Check if this iteration included tool calls."""
        return len(self.tool_calls) > 0

    def is_reasoning_iteration(self) -> bool:
        """Check if this is a reasoning iteration (thinking, observation, or reasoning)."""
        return self.iteration_type in ["thinking", "observation", "reasoning"]


class IterationTracker:
    """
    Simple tracking of agent iterations.

    Tracks iteration count, types, and calculates reasoning density.
    NO heavy management - just lightweight metrics.
    """

    def __init__(self, max_iterations: int = 100):
        """
        Initialize iteration tracker.

        Args:
            max_iterations: Maximum iterations before stopping
        """
        self.max_iterations = max_iterations
        self.iterations: List[Iteration] = []
        self.current_iteration = 0

    def record_iteration(
        self,
        iteration_type: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None
    ) -> None:
        """
        Record an iteration.

        Args:
            iteration_type: Type of iteration (thinking/action/observation/reasoning/general)
            content: Agent's response content
            tool_calls: Tool calls made (if any)
        """
        self.current_iteration += 1

        iteration = Iteration(
            iteration_num=self.current_iteration,
            iteration_type=iteration_type,
            content=content,
            tool_calls=tool_calls or []
        )

        self.iterations.append(iteration)

    def get_reasoning_density(self) -> float:
        """
        Calculate percentage of iterations that were reasoning (no tools).

        Reasoning iterations = thinking + observation + reasoning (no tool calls)
        Total iterations = all iterations

        Target: 30-40%

        Returns:
            Reasoning density as float (0.0 to 1.0)
        """
        if not self.iterations:
            return 0.0

        reasoning_iterations = sum(
            1 for it in self.iterations
            if it.is_reasoning_iteration()
        )

        return reasoning_iterations / len(self.iterations)

    def should_continue(self) -> bool:
        """
        Check if execution should continue.

        Returns:
            True if under max iterations, False otherwise
        """
        return self.current_iteration < self.max_iterations

    def get_summary(self) -> Dict[str, Any]:
        """
        Get summary of iteration tracking for final analytics.

        Returns:
            Dict with iteration stats and reasoning density
        """
        # Calculate breakdown inline (no separate method needed)
        breakdown = {
            "thinking": 0,
            "action": 0,
            "observation": 0,
            "reasoning": 0,
            "general": 0
        }

        for iteration in self.iterations:
            iteration_type = iteration.iteration_type
            if iteration_type in breakdown:
                breakdown[iteration_type] += 1

        reasoning_density = self.get_reasoning_density()

        return {
            "total_iterations": self.current_iteration,
            "max_iterations": self.max_iterations,
            "remaining": self.max_iterations - self.current_iteration,
            "reasoning_density": round(reasoning_density, 3),
            "reasoning_density_percentage": round(reasoning_density * 100, 1),
            "breakdown": breakdown,
            "reasoning_iterations": breakdown["thinking"] + breakdown["observation"] + breakdown["reasoning"],
            "action_iterations": breakdown["action"]
        }