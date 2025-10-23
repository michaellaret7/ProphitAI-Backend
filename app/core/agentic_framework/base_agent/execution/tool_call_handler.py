"""Tool call handling for agent iterations.

This module handles the execution of tool calls, both native (OpenAI format)
and content-based (JSON format), including plan loading and parallel execution.
"""

import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..agent import BaseAgent

from ..core.result_parser import parse_tool_result


@dataclass
class ToolResult:
    """Result from executing a single tool."""
    tool_name: str
    args: Dict[str, Any]
    observation: Any
    tool_call_id: Optional[str] = None


class ToolCallHandler:
    """Handles tool call execution for agent iterations.

    This class manages the execution of tools, tracks failures,
    handles plan loading, and manages parallel tool execution.
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize tool call handler.

        Args:
            agent: The BaseAgent instance that owns this handler
        """
        self.agent = agent

    def handle_tool_calls(
        self,
        tool_calls: List[Any],
        messages: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """Handle native tool calls from the LLM.

        Args:
            tool_calls: List of tool call objects from LLM response
            messages: Conversation history (modified in place)

        Returns:
            List of ToolResult objects
        """
        results: List[ToolResult] = []

        # Append assistant message with all tool calls
        assistant_message = {
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_message)

        # Execute each tool call
        for tc in tool_calls:
            name = tc.function.name
            args_json = tc.function.arguments or "{}"

            # Parse arguments using robust parser
            args = self._parse_tool_arguments(name, args_json)

            # Check for stagnation
            self.agent.utilities.update_stagnation(name, args)

            # Execute tool or skip if failed too many times
            observation = self._execute_tool_with_failure_tracking(name, args)

            # Handle structured planning tool
            if name == "create_structured_plan":
                self._handle_plan_loading(observation)

            # Update execution engine with tool result
            self.agent.execution_engine.update_task_from_tool_result(name, observation)

            # Check for task failure indicators
            self.agent._check_for_task_failure(name, observation)

            # Check if current task should be completed and advance automatically
            if self.agent.execution_engine.plan_loaded:
                should_complete, reason = self.agent.execution_engine.check_task_completion_conditions()
                if should_complete:
                    self.agent.execution_engine.advancement.advance_task_progression()

            # Track observation for validation
            self._track_observation(observation)

            if self.agent.verbose:
                log_args = {k: v for k, v in args.items() if k != '_simulation_date'}
                print(f"  tool_call -> {name} args={json.dumps(log_args, sort_keys=True)}")
                print("  observation:", self.agent.utilities.stringify(observation))

            # Add tool result to messages
            observation_content = self.agent.utilities.stringify(observation)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": observation_content,
            })

            # Create tool result
            tool_result = ToolResult(
                tool_name=name,
                args=args,
                observation=observation,
                tool_call_id=tc.id
            )
            results.append(tool_result)

        # Update task progress
        current_iteration = self.agent.trace[-1].iteration if self.agent.trace else 0
        self.agent.task_manager.progress.update_progress(current_iteration)

        return results

    def handle_content_tool_call(
        self,
        content_tool: Dict[str, Any],
        messages: List[Dict[str, Any]]
    ) -> Optional[ToolResult]:
        """Handle JSON-based tool call from content.

        Args:
            content_tool: Parsed tool call from content
            messages: Conversation history (modified in place)

        Returns:
            ToolResult if successful, None otherwise
        """
        name = content_tool.get("tool")
        args = content_tool.get("args", {})

        # Skip if no valid tool name
        if not name:
            if self.agent.verbose:
                print(f"⚠️ Skipping tool call - no valid tool name found")
            return None

        # Special handling for parallel wrapper
        if name == "multi_tool_use.parallel" and isinstance(args, dict) and isinstance(args.get("tool_uses"), list):
            return self._handle_parallel_tool_calls(args, messages)

        # Normal single tool execution
        self.agent.utilities.update_stagnation(name, args)
        observation = self.agent.utilities.execute_tool_safe(name, args)

        # Update execution engine
        self.agent.execution_engine.update_task_from_tool_result(name, observation)
        self.agent._check_for_task_failure(name, observation)

        # Check if current task should be completed and advance automatically
        if self.agent.execution_engine.plan_loaded:
            should_complete, reason = self.agent.execution_engine.check_task_completion_conditions()
            if should_complete:
                self.agent.execution_engine.advancement.advance_task_progression()

        # Track observation
        self._track_observation(observation)

        if self.agent.verbose:
            log_args = {k: v for k, v in args.items() if k != '_simulation_date'}
            print(f"  tool_call(content) -> {name} args={json.dumps(log_args, sort_keys=True)}")
            print("  observation:", self.agent.utilities.stringify(observation))

        # Add to messages
        messages.append({"role": "assistant", "content": ""})
        messages.append({
            "role": "user",
            "content": f"Tool '{name}' returned: {self.agent.utilities.stringify(observation)}"
        })

        # Update task progress
        current_iteration = self.agent.trace[-1].iteration if self.agent.trace else 0
        self.agent.task_manager.progress.update_progress(current_iteration)

        return ToolResult(
            tool_name=name,
            args=args,
            observation=observation
        )

    def _parse_tool_arguments(self, tool_name: str, args_json: str) -> Dict[str, Any]:
        """Parse tool arguments using robust parser.

        Args:
            tool_name: Name of the tool
            args_json: JSON string of arguments

        Returns:
            Parsed arguments dictionary
        """
        if self.agent._arg_parser:
            return self.agent._arg_parser.parse_arguments(
                tool_name=tool_name,
                args_json=args_json,
                tool_function=self.agent.tool_functions.get(tool_name)
            )
        else:
            # Fallback if parser not initialized
            try:
                return json.loads(args_json)
            except json.JSONDecodeError:
                return {"_raw": args_json}

    def _execute_tool_with_failure_tracking(
        self,
        tool_name: str,
        args: Dict[str, Any]
    ) -> Any:
        """Execute tool with consecutive failure tracking.

        Args:
            tool_name: Name of the tool to execute
            args: Tool arguments

        Returns:
            Tool execution result or skip message
        """
        # Check for consecutive failures
        error_key_args = {k: v for k, v in args.items() if k != '_simulation_date'}
        error_key = f"{tool_name}:{json.dumps(error_key_args, sort_keys=True)}"

        if error_key in self.agent.consecutive_failures and self.agent.consecutive_failures[error_key] >= 3:
            if self.agent.verbose:
                print(f"⚠️ Skipping {tool_name} - failed 3 times with same args")
            return f"Skipped after 3 consecutive failures with same arguments"

        # Execute tool
        observation = self.agent.utilities.execute_tool_safe(tool_name, args)

        # Track failures/successes
        parsed_obs = parse_tool_result(observation, verbose=self.agent.verbose)

        if parsed_obs.get('success') is False:
            self.agent.consecutive_failures[error_key] = self.agent.consecutive_failures.get(error_key, 0) + 1
            if self.agent.verbose:
                error_msg = parsed_obs.get('error', 'Unknown error')
                print(f"⚠️ Tool failed: {error_msg}")
        else:
            # Reset on success
            if error_key in self.agent.consecutive_failures:
                del self.agent.consecutive_failures[error_key]

        return observation

    def _handle_plan_loading(self, observation: Any) -> bool:
        """Handle loading of structured plan into execution engine.

        Args:
            observation: Result from create_structured_plan tool

        Returns:
            True if plan was loaded successfully
        """
        if not isinstance(observation, dict) or not observation.get('success'):
            return False

        plan_data = observation.get('plan', {})
        from ..tasks.models import TodoList

        try:
            todo_list = TodoList.model_validate(plan_data)

            if self.agent.execution_engine.load_plan(todo_list):
                if self.agent.verbose:
                    print("✅ Plan loaded into execution engine")
                    plan_summary = self.agent.task_manager.progress.get_summary()
                    print(f"📊 Plan Overview: {plan_summary['total_main_tasks']} main tasks, {plan_summary['total_subtasks']} subtasks")
                return True
        except Exception as e:
            if self.agent.verbose:
                print(f"⚠️ Failed to load plan into execution engine: {e}")

        return False

    def _handle_parallel_tool_calls(
        self,
        args: Dict[str, Any],
        messages: List[Dict[str, Any]]
    ) -> ToolResult:
        """Handle parallel tool wrapper by executing sequentially.

        Args:
            args: Arguments containing tool_uses list
            messages: Conversation history (modified in place)

        Returns:
            ToolResult with aggregated results
        """
        aggregated_results: List[Dict[str, Any]] = []

        for entry in args.get("tool_uses", []):
            if not isinstance(entry, dict):
                continue

            inner_name = entry.get("recipient_name") or entry.get("tool")
            inner_args = entry.get("parameters") or entry.get("args") or {}

            if isinstance(inner_name, str) and inner_name.startswith("functions."):
                inner_name = inner_name[10:]

            # Parse/validate inner args
            if self.agent._arg_parser and isinstance(inner_name, str):
                inner_args = self.agent._arg_parser.parse_arguments(
                    tool_name=inner_name,
                    args_json=json.dumps(inner_args),
                    tool_function=self.agent.tool_functions.get(inner_name)
                )

            # Execute tool
            obs = self.agent.utilities.execute_tool_safe(inner_name, inner_args)

            # Update execution engine
            self.agent.execution_engine.update_task_from_tool_result(inner_name, obs)
            self.agent._check_for_task_failure(inner_name, obs)

            # Check if current task should be completed and advance automatically
            if self.agent.execution_engine.plan_loaded:
                should_complete, reason = self.agent.execution_engine.check_task_completion_conditions()
                if should_complete:
                    self.agent.execution_engine.advancement.advance_task_progression()

            aggregated_results.append({
                "tool": inner_name,
                "args": inner_args,
                "observation": obs,
            })

        parallel_result = {"parallel_results": aggregated_results}

        if self.agent.verbose:
            print(f"  tool_call(content) -> multi_tool_use.parallel (unwrapped {len(aggregated_results)} calls)")
            print("  observation:", self.agent.utilities.stringify(parallel_result))

        # Add to messages
        messages.append({"role": "assistant", "content": ""})
        messages.append({
            "role": "user",
            "content": f"Unwrapped 'multi_tool_use.parallel' and executed sequentially: {self.agent.utilities.stringify(parallel_result)}"
        })

        # Update task progress
        current_iteration = self.agent.trace[-1].iteration if self.agent.trace else 0
        self.agent.task_manager.progress.update_progress(current_iteration)

        return ToolResult(
            tool_name="multi_tool_use.parallel",
            args=args,
            observation=parallel_result
        )

    def _track_observation(self, observation: Any) -> None:
        """Track observation for validation.

        Args:
            observation: Tool execution result
        """
        self.agent.recent_observations.append(observation)
        if len(self.agent.recent_observations) > 20:
            self.agent.recent_observations.pop(0)