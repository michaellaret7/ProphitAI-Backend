"""ToolIntegrationManager - Tool result processing and evidence collection.

Responsibilities:
- Process tool execution results
- Extract evidence from tool outputs
- Determine tool relevance to current task/subtask
- Trigger auto-advancement based on validation
- Pattern matching for success indicators
"""

from typing import List, Optional, Any, TYPE_CHECKING
import re
from ...core.result_parser import parse_tool_result
from ..models import MainTask, SubTask, TaskStatus

if TYPE_CHECKING:
    from .executor_core import ExecutorCore
    from .advancement import AdvancementManager


# ============================================================================
# Evidence Logging Configuration
# ============================================================================
# Philosophy: Only log evidence for significant events and insights,
# not routine status updates or simple successes.

# Tools that should ALWAYS log evidence (important events)
ALWAYS_LOG_EVIDENCE = {
    'create_structured_plan',
    'mark_task_complete',
    'episodic_remember',
}

# Tools that should NEVER log evidence (routine task management)
NEVER_LOG_EVIDENCE = {
    'update_task_status',
    'get_current_task_info',
    'get_completion_analysis',
}


def should_log_evidence(tool_name: str, result: Any) -> bool:
    """Determine if tool result warrants evidence logging.

    Only logs evidence for significant events to reduce overhead.

    Args:
        tool_name: Name of executed tool
        result: Tool result

    Returns:
        True if evidence should be logged
    """
    # Always log these important events
    if tool_name in ALWAYS_LOG_EVIDENCE:
        return True

    # Never log routine task management
    if tool_name in NEVER_LOG_EVIDENCE:
        return False

    # For analytical tools, only log if result has substance or errors
    parsed = parse_tool_result(result, verbose=False)

    # Always log failures prominently
    if parsed.get('success') is False:
        return True

    # Log if there's actual data (not just success=True)
    if 'data' in parsed and parsed['data']:
        return True

    # Log if there are warnings or errors
    if 'error' in parsed or 'warning' in parsed:
        return True

    # Default: don't log routine successes
    return False


class ToolIntegrationManager:
    """Manages tool result processing and evidence collection."""

    def __init__(self, core: 'ExecutorCore', advancement: 'AdvancementManager'):
        """Initialize the tool integration manager.

        Args:
            core: ExecutorCore instance for state access
            advancement: AdvancementManager for auto-advancement
        """
        self.core = core
        self.advancement = advancement

    def _get_current_task_from_state(self):
        """Get the ACTUAL current task from stored plan state, not cached reference.

        This ensures we always route to the correct task even after advancements.

        Returns:
            Tuple of (current_main_task, current_subtask) from actual plan state
        """
        plan = self.core.task_store.get_current_structured_plan()
        if not plan:
            return None, None

        # Find the task with status=in_progress
        current_task = None
        for task in plan.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                current_task = task
                break

        # If no task is in_progress, find the first pending task
        if not current_task:
            for task in plan.tasks:
                if task.status == TaskStatus.PENDING:
                    current_task = task
                    break

        if not current_task:
            return None, None

        # Find the first incomplete subtask
        current_subtask = None
        if current_task.subtasks:
            for subtask in current_task.subtasks:
                if not subtask.completed:
                    current_subtask = subtask
                    break

        return current_task, current_subtask

    def update_task_from_tool_result(self, tool_name: str, result: Any) -> bool:
        """Update task progress based on tool execution result.

        Args:
            tool_name: Name of the tool that was executed
            result: Result from the tool execution

        Returns:
            True if task was updated based on the result
        """
        # Early return if no current task (plan already completed)
        if self.core.current_main_task is None:
            if self.core.verbose:
                print("Tool result received after plan completion - ignoring")
            return False

        # BUG FIX: Get ACTUAL current task from state, not cached reference
        # This ensures evidence routes to the correct task after advancements
        active_task, active_subtask = self._get_current_task_from_state()

        # Fallback to core reference if state query fails
        if active_task is None:
            active_task = self.core.current_main_task
            active_subtask = self.core.current_subtask

        active_task_id = active_task.id if active_task else None
        active_subtask_id = active_subtask.id if active_subtask else None
        predicted_tools = list(active_task.predicted_tool_use or []) if active_task else []

        # Add tool result to observations using TaskManager
        observation = f"Tool '{tool_name}' returned: {str(result)[:200]}"

        # Always add observation to main task
        self.core.task_store.add_task_observation(
            active_task_id,
            observation
        )

        # Determine relevance and success (always strict)
        is_relevant = self._is_tool_relevant(tool_name, active_task, active_subtask)
        is_error = self._is_error_result(result)

        if active_subtask_id and is_relevant:
            # Add observation to subtask only when relevant
            self.core.task_store.add_task_observation(
                active_task_id,
                observation,
                active_subtask_id
            )

            # Collect evidence respecting error-awareness
            evidence_items = self.collect_evidence_from_tool_result(tool_name, result)
            for evidence in evidence_items:
                self.core.task_store.add_task_evidence(
                    active_task_id,
                    evidence,
                    active_subtask_id
                )

        # Check if this tool was predicted for this task and assess completion
        should_auto_advance = False
        if tool_name in predicted_tools:
            if self.core.verbose:
                print(f"  🔧 Tool '{tool_name}' execution recorded for predicted task tool")

            # Check if this completes the current subtask
            if active_subtask is not None:
                # Simple heuristic: if tool was predicted and executed successfully, subtask may be complete
                if not isinstance(result, Exception) and result is not None:
                    # Check if we should auto-advance subtask
                    if self._should_auto_advance_subtask(tool_name, result):
                        should_auto_advance = True

        # Add completion evidence to appropriate level (avoid duplicating on main if attached to subtask)
        evidence_items = self.collect_evidence_from_tool_result(tool_name, result)
        if active_subtask_id and is_relevant:
            # Evidence already attached to subtask above; skip duplicating on main task
            pass
        else:
            for evidence in evidence_items:
                # Avoid adding misleading success evidence at main-task level when error occurred
                if self._looks_like_success_evidence(evidence) and is_error:
                    continue
                self.core.task_store.add_task_evidence(
                    active_task_id,
                    evidence
                )

        # Advance only after all routing/evidence writes are done
        if should_auto_advance:
            success, message = self.advancement.advance_task_progression()
            if success and self.core.verbose:
                print(f"  🚀 Auto-advanced: {message}")

        # State is already saved by TaskManager methods

        return True

    def _should_auto_advance_subtask(self, tool_name: str, result: Any) -> bool:
        """Determine if subtask should be auto-advanced based on intelligent validation.

        Args:
            tool_name: Name of the executed tool
            result: Result from tool execution

        Returns:
            True if subtask should be advanced
        """
        if not self.core.current_subtask:
            return False

        # Check the subtask for completion using TaskValidator
        subtask_complete = self.core.task_validator.is_subtask_complete(
            self.core.current_subtask
        )

        if self.core.verbose and subtask_complete:
            print(f"  🔍 Subtask completion detected")

        # Require relevance, success, and explicit tool-named evidence (always strict)
        is_relevant = self._is_tool_relevant(tool_name, self.core.current_main_task, self.core.current_subtask)
        is_error = self._is_error_result(result)
        has_tool_named_evidence = self._subtask_has_tool_named_evidence(self.core.current_subtask, tool_name)
        if not (is_relevant and not is_error and has_tool_named_evidence):
            return False

        # Auto-advance if validator confirms completion
        return subtask_complete

    def collect_evidence_from_tool_result(self, tool_name: str, result: Any) -> List[str]:
        """Automatically collect evidence from tool results.

        Only collects evidence for significant events to reduce overhead.

        Args:
            tool_name: Name of the executed tool
            result: Result from tool execution

        Returns:
            List of evidence strings extracted from the result
        """
        # Check if we should log evidence for this tool
        if not should_log_evidence(tool_name, result):
            return []  # Return empty list, no evidence

        evidence_items = []

        is_error = self._is_error_result(result)

        if is_error:
            # Record explicit failure evidence without implying success
            message = self._summarize_error(result)
            evidence_items.append(f"⚠️ Tool {tool_name} FAILED{': ' + message if message else ''}")
            return evidence_items

        # Basic evidence: tool execution (success path only)
        # Use more concise format
        evidence_items.append(f"Executed '{tool_name}'")

        # Parse result to check for success and extract data
        parsed_result = parse_tool_result(result, verbose=False)

        # For successful analytical tools, log key insights only
        if parsed_result.get('success') is True and 'data' in parsed_result:
            data = parsed_result['data']

            # Add concise data summary
            if isinstance(data, dict) and data:
                evidence_items.append(f"Retrieved data with {len(data)} fields")
            elif isinstance(data, list) and len(data) > 0:
                evidence_items.append(f"Retrieved {len(data)} items")

        return evidence_items

    # --- Helper methods for strict validation ---

    def _is_error_result(self, result: Any) -> bool:
        """Check if result is an error using standardized parsing."""
        parsed = parse_tool_result(result, verbose=False)
        return parsed.get('success') is False

    def _summarize_error(self, result: Any) -> str:
        """Summarize error message from result."""
        try:
            if isinstance(result, Exception):
                return str(result)
            if isinstance(result, dict):
                if result.get('error'):
                    return str(result.get('error'))
                # Common error shapes
                for key in ['message', 'detail', 'details']:
                    if key in result:
                        return str(result[key])
            if isinstance(result, str):
                return result[:160]
        except Exception:
            return ""
        return ""

    def _is_tool_relevant(self, tool_name: str, main_task: MainTask, subtask: Optional[SubTask]) -> bool:
        """Check if tool is relevant to current task/subtask."""
        if not main_task or not subtask:
            return False
        try:
            tool = str(tool_name).strip().lower()
            # 1) Prefer explicit subtask expected_tools if provided
            expected = [str(t).strip().lower() for t in getattr(subtask, 'expected_tools', [])]
            if expected:
                return tool in expected

            # 2) Otherwise require whole-word match of tool name in subtask description
            desc = str(subtask.description or "").lower()
            pattern = r"\b" + re.escape(tool) + r"\b"
            if re.search(pattern, desc):
                return True

            # 3) Fallback: allow relevance when the subtask description clearly starts with 'Call <tool>'
            # This guards against minor punctuation/formatting variations
            simple_call_pattern = r"\bcall\s+" + re.escape(tool) + r"\b"
            return re.search(simple_call_pattern, desc) is not None
        except Exception:
            return False

    def _subtask_has_tool_named_evidence(self, subtask: SubTask, tool_name: str) -> bool:
        """Check if subtask has evidence mentioning the tool name."""
        if not subtask:
            return False
        t = str(tool_name).strip().lower()
        for ev in subtask.completion_evidence:
            try:
                if t in str(ev).lower():
                    return True
            except Exception:
                continue
        return False

    def _looks_like_success_evidence(self, evidence_text: str) -> bool:
        """Check if evidence text contains success indicators."""
        text = (evidence_text or "").lower()
        success_markers = [
            'successfully executed tool', 'returned success=true', 'completed',
            'retrieval completed', 'analysis completed', 'calculation completed',
            'processing completed', 'creation completed', 'generation completed'
        ]
        return any(marker in text for marker in success_markers)
