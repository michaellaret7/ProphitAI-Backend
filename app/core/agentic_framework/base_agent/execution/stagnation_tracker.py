"""Stagnation detection and recovery for agent iterations.

This module tracks repeated actions and detects when an agent is stuck,
providing intelligent recovery messages based on execution context.
"""

import json
from typing import List, Dict, Any, Tuple, Optional


class StagnationTracker:
    """Tracks and detects stagnation in agent execution.

    Stagnation occurs when an agent repeatedly executes the same tool
    with similar arguments without making progress. This tracker monitors
    recent actions and provides recovery guidance when stagnation is detected.
    """

    def __init__(self, threshold: int = 4, history_size: int = 16):
        """Initialize stagnation tracker.

        Args:
            threshold: Number of repeated actions before stagnation is triggered
            history_size: Maximum number of recent actions to track
        """
        self.threshold = threshold
        self.history_size = history_size
        self._recent_actions: List[str] = []  # Serialized (tool_name + sorted args)
        self._stuck_count: int = 0

    def update(self, tool_name: str, args: Dict[str, Any]) -> None:
        """Update stagnation tracking with a new tool execution.

        Args:
            tool_name: Name of the executed tool
            args: Arguments passed to the tool

        Note:
            Automatically filters out '_simulation_date' from args for
            stagnation comparison (not JSON serializable).
        """
        # Strip 'functions.' prefix if present
        if tool_name.startswith("functions."):
            tool_name = tool_name[10:]

        # Filter out _simulation_date for stagnation key (not JSON serializable)
        stag_args = {k: v for k, v in args.items() if k != '_simulation_date'}

        # Create unique key for this action
        key = f"{tool_name}:{json.dumps(stag_args, sort_keys=True)}"

        # Check if this action was recently executed
        if key in self._recent_actions:
            self._stuck_count += 1
        else:
            self._stuck_count = 0

        # Add to history and maintain size limit
        self._recent_actions.append(key)
        if len(self._recent_actions) > self.history_size:
            self._recent_actions.pop(0)

    def is_stagnating(self) -> bool:
        """Check if agent is currently stagnating.

        Returns:
            True if stuck_count >= threshold, False otherwise
        """
        return self._stuck_count >= self.threshold

    def get_stagnation_count(self) -> int:
        """Get current stagnation count.

        Returns:
            Number of consecutive repeated actions
        """
        return self._stuck_count

    def reset(self) -> None:
        """Reset stagnation state after recovery intervention."""
        self._stuck_count = 0

    def clear_history(self) -> None:
        """Clear all tracking history (useful for testing or fresh starts)."""
        self._recent_actions.clear()
        self._stuck_count = 0

    def get_recovery_message(
        self,
        execution_engine: Optional[Any] = None,
        recent_observations: Optional[List[Any]] = None,
        verbose: bool = False
    ) -> str:
        """Generate intelligent recovery message based on execution context.

        Args:
            execution_engine: Optional execution engine for plan-driven context
            recent_observations: Optional list of recent tool observations
            verbose: Whether to print debug information

        Returns:
            Formatted recovery message string
        """
        # Check if we have plan execution context
        if execution_engine and execution_engine.plan_loaded:
            # Check for intelligent stagnation detection
            is_stagnating, stagnation_reason = execution_engine.check_for_stagnation(
                recent_observations or [],
                threshold=3
            )

            if is_stagnating:
                if verbose:
                    print(f"🔄 Stagnation detected: {stagnation_reason}")

                return (
                    f"🚨 STAGNATION DETECTED: {stagnation_reason}\n\n"
                    "Your current task appears to be stagnating. Consider these options:\n"
                    "1. Use 'handle_task_failure' tool with recovery strategy\n"
                    "2. Use 'advance_to_next_task' to move forward\n"
                    "3. Try alternative tools or approaches\n"
                    "4. Use 'get_completion_analysis' to assess current state\n\n"
                    "Choose an appropriate action to break out of the stagnation."
                )
            else:
                # Regular stagnation with plan context
                task_context = execution_engine.get_current_task_context()
                current_task_info = ""

                if task_context.get("status") == "executing":
                    current_task_info = f"\nCurrent Task: {task_context['main_task']['description']}"
                    if 'subtask' in task_context:
                        current_task_info += f"\nCurrent SubTask: {task_context['subtask']['description']}"

                return (
                    "🔄 You are repeating similar actions without new progress. "
                    f"{current_task_info}\n\n"
                    "Consider: different tools, alternative approach, or use 'handle_task_failure' if stuck."
                )
        else:
            # Original stagnation message when no plan loaded
            return (
                "You are repeating the same action with similar arguments and no new information. "
                "Propose a different approach or finalize with a 'Final Answer:'."
            )

    def get_state(self) -> Dict[str, Any]:
        """Get current stagnation state for debugging/monitoring.

        Returns:
            Dictionary containing current state information
        """
        return {
            "stuck_count": self._stuck_count,
            "threshold": self.threshold,
            "is_stagnating": self.is_stagnating(),
            "recent_actions_count": len(self._recent_actions),
            "history_size": self.history_size
        }

    def __repr__(self) -> str:
        """String representation of tracker state."""
        return (
            f"StagnationTracker(stuck_count={self._stuck_count}, "
            f"threshold={self.threshold}, "
            f"is_stagnating={self.is_stagnating()})"
        )
