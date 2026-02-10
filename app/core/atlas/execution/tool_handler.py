"""Tool Handler - executes tools and manages message history."""

import copy
import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Union

import yaml

from app.core.atlas.execution.validation import validate_tool_call
from app.core.atlas.logging import AgentPrinter, write_messages_to_yaml, log_tool_call
from app.core.atlas.context import prune_completed_task_messages, prune_note_content
from app.core.atlas.tools.responses import error_response
from app.core.atlas.execution.utils import stringify_for_llm, check_tool_success

if TYPE_CHECKING:
    from app.core.atlas.agents import AgentBase
    from app.core.atlas.models.callbacks import ChatCallback, NoOpChatCallback

# Tools that modify agent state and must run sequentially
SEQUENTIAL_ONLY_TOOLS = {"write_note", "finalize", "think", "update_plan"}

def should_run_parallel(tool_calls: List[Any]) -> bool:
    """Determine if tool calls can be executed in parallel.

    Returns False if:
    - Only one tool call (no benefit from parallelization)
    - Any tool is in SEQUENTIAL_ONLY_TOOLS (state-modifying tools)
    """
    if len(tool_calls) <= 1:
        return False

    for tool_call in tool_calls:
        if tool_call.function.name in SEQUENTIAL_ONLY_TOOLS:
            return False

    return True

class ToolHandler:
    """Handles tool execution and result formatting."""

    def __init__(
        self,
        agent: 'AgentBase',
        printer: AgentPrinter,
        chat_callback: Optional[Union["ChatCallback", "NoOpChatCallback"]] = None,
    ):
        self.agent = agent
        self.printer = printer
        # Note: chat_callback param kept for backwards compatibility but not used
        # We always read from agent.chat_callback to get the current callback
        self.current_iteration: int = 0  # Set by execution loop for callback events
        self.retry = False
        self.tool_call_history = []

    @property
    def chat_callback(self) -> Optional[Union["ChatCallback", "NoOpChatCallback"]]:
        """Get the current chat callback from the agent.

        This property ensures we always use the agent's current callback,
        which may be updated after ToolHandler initialization (e.g., when
        WebSocketChatCallback is set per-message in chat_router).
        """
        return getattr(self.agent, 'chat_callback', None)

    def handle_tool_calls(self, tool_calls: List[Any]) -> None:
        """Execute tool calls and update message history."""
        last = self.agent.messages[-1] if self.agent.messages else None

        already_added = isinstance(last, dict) and last.get("role") == "assistant" and last.get("tool_calls")

        if not already_added:
            self.agent.messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            })

        current_assistant_idx = len(self.agent.messages) - 1

        for tool_call in tool_calls:
            name = tool_call.function.name
            tool_call_id = tool_call.id

            args_json = tool_call.function.arguments or "{}"

            args, parse_error = self._parse_arguments(args_json)

            self.printer.tool_call_start(name)

            # Emit tool call start event
            if self.chat_callback:
                self.chat_callback.on_tool_call_start(
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    arguments=args,
                    iteration=self.current_iteration,
                )

            if parse_error:
                self.printer.parse_error(args_json)

                result = error_response(
                    f"Tool '{name}' was not executed because arguments could not be parsed. "
                    f"{parse_error}. Please retry the tool call with valid JSON arguments."
                )

                self._add_tool_result(tool_call, result, name, args)

                # Emit tool result event for parse error
                if self.chat_callback:
                    self.chat_callback.on_tool_call_result(
                        tool_call_id=tool_call_id,
                        tool_name=name,
                        result=str(result),
                        success=False,
                        duration_ms=0,
                    )

                continue

            self.printer.tool_arguments(args)

            # Execute with timing
            start_time = time.perf_counter()
            result = self._execute_tool(name, args)
            duration_ms = int((time.perf_counter() - start_time) * 1000)

            # Track note titles
            if name == "write_note":
                self._handle_note_tracking(result, args)

            # Handle task completion pruning
            if name == "update_tasks":
                current_assistant_idx = self._handle_task_update(
                    result, args, tool_calls, current_assistant_idx
                )

            # Add result to messages (returns success after validation)
            success = self._add_tool_result(tool_call, result, name, args)

            # Emit tool result event AFTER _add_tool_result (reuses success, no duplicate validation)
            if self.chat_callback:
                result_str = str(result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "... (truncated)"
                self.chat_callback.on_tool_call_result(
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    result=result_str,
                    success=success,
                    duration_ms=duration_ms,
                )

        self._write_messages_to_yaml()

    def handle_tool_calls_parallel(self, tool_calls: List[Any]) -> None:
        """Execute multiple tool calls in parallel using ThreadPoolExecutor."""
        num_tools = len(tool_calls)
        self.printer.parallel_start(num_tools)

        # Parse all arguments upfront and emit start events
        parsed_calls = []
        for tool_call in tool_calls:
            name = tool_call.function.name
            tool_call_id = tool_call.id

            args_json = tool_call.function.arguments or "{}"
            args, parse_error = self._parse_arguments(args_json)

            parsed_calls.append((tool_call, name, args, parse_error))
            
            self.printer.parallel_tool_queued(name)

            # Emit tool call start event
            if self.chat_callback:
                self.chat_callback.on_tool_call_start(
                    tool_call_id=tool_call_id,
                    tool_name=name,
                    arguments=args,
                    iteration=self.current_iteration,
                )

        # Execute all tools in parallel (with timing)
        start_times = {tc.id: time.perf_counter() for tc in tool_calls}
        results = self._execute_tools_parallel(parsed_calls)
        end_time = time.perf_counter()

        # Process results sequentially
        for (tool_call, name, args, _parse_error), result in zip(parsed_calls, results):
            if name == "write_note":
                self._handle_note_tracking(result, args)

            success = self._add_tool_result_parallel(tool_call, result, name, args)

            # Emit tool result event
            if self.chat_callback:
                duration_ms = int((end_time - start_times[tool_call.id]) * 1000)
                result_str = str(result)
                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "... (truncated)"
                self.chat_callback.on_tool_call_result(
                    tool_call_id=tool_call.id,
                    tool_name=name,
                    result=result_str,
                    success=success,
                    duration_ms=duration_ms,
                )

        # Log all tool calls once after parallel execution completes
        log_tool_call(self.tool_call_history, output_dir=getattr(self.agent, "output_dir", None))
        self._write_messages_to_yaml()

    def _execute_tools_parallel(
        self,
        parsed_calls: List[tuple]
    ) -> List[Any]:
        """Execute parsed tool calls in parallel. Returns list of results."""
        results = []
        try:
            with ThreadPoolExecutor(max_workers=len(parsed_calls)) as executor:
                futures = []
                for tool_call, name, args, parse_error in parsed_calls:
                    if parse_error:
                        futures.append(None)
                    else:
                        futures.append(executor.submit(self._execute_tool, name, args))

                for i, (tool_call, name, args, parse_error) in enumerate(parsed_calls):
                    if parse_error:
                        results.append(error_response(f"Argument parse failed: {parse_error}"))
                    else:
                        try:
                            results.append(futures[i].result())
                        except Exception as e:
                            results.append(error_response(f"Error executing {name}: {str(e)}"))
        except Exception as e:
            self.printer.error(f"Parallel execution failed: {e}")
            results = [error_response(f"Parallel execution failed: {e}")] * len(parsed_calls)

        return results

    def _add_tool_result_parallel(
        self,
        tool_call: Any,
        result: Any,
        name: str,
        args: Dict[str, Any],
    ) -> bool:
        """Add a tool result to messages for parallel execution (uses parallel printer)."""
        tool_validation = validate_tool_call(name, args, result, self.agent)
        tool_validation_dict = yaml.safe_load(tool_validation)
        success, _ = check_tool_success(tool_validation_dict)

        self.tool_call_history.append(tool_validation_dict)

        self.printer.parallel_tool_result(name, result, success)

        content = stringify_for_llm(result) if success else yaml.dump(
            tool_validation_dict, default_flow_style=False, sort_keys=False
        )
        self.agent.messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": content
        })

        return success

    def _parse_arguments(self, args_json: str) -> tuple[Dict[str, Any], str | None]:
        """Parse tool arguments from JSON string."""
        try:
            return json.loads(args_json), None
        except json.JSONDecodeError as e:
            self.printer.parse_error(args_json)
            error_msg = f"Failed to parse tool arguments (invalid JSON): {str(e)}"
            return {}, error_msg

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with error handling."""
        func = self.agent.tool_functions.get(name)

        if not func:
            error_msg = f"Tool '{name}' not found. Available: {list(self.agent.tool_functions.keys())}"
            self.printer.tool_error(error_msg)
            return error_response(error_msg)

        try:
            execution_args = args.copy()
            if getattr(self.agent, 'simulation_date', None) is not None and isinstance(execution_args, dict):
                execution_args['_simulation_date'] = self.agent.simulation_date
            return func(**execution_args)
        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            self.printer.tool_error(error_msg)
            return error_response(error_msg)

    def _handle_note_tracking(self, result: Any, args: Dict[str, Any]) -> None:
        """Track note titles when write_note succeeds."""
        try:
            result_dict = yaml.safe_load(result) if isinstance(result, str) else result
            if result_dict.get("success") and "title" in args:
                title = args["title"]
                if title not in self.agent.note_titles:
                    self.agent.note_titles.append(title)
                    self.printer.note_added(title)
        except Exception as e:
            self.printer.warning(f"Failed to track note title: {e}")

    def _handle_task_update(
        self,
        result: Any,
        args: Dict[str, Any],
        tool_calls: List[Any],
        current_assistant_idx: int
    ) -> int:
        """Handle message pruning when tasks are updated. Returns updated assistant index."""
        status = args.get("status")
        if status not in ("complete", "completed", "in_progress"):
            return current_assistant_idx

        try:
            result_dict = yaml.safe_load(result) if isinstance(result, str) else result
            if not result_dict.get("success"):
                return current_assistant_idx

            if status in ("complete", "completed"):
                self.agent.messages = prune_completed_task_messages(
                    messages=self.agent.messages,
                    main_task=args.get("main_task"),
                    subtasks=args.get("subtasks"),
                    exclude_index=current_assistant_idx,
                    verbose=self.printer.is_verbose,
                    prune_status="in_progress"
                )
            else:  # in_progress
                self.agent.messages = prune_completed_task_messages(
                    messages=self.agent.messages,
                    exclude_index=current_assistant_idx,
                    verbose=self.printer.is_verbose,
                    prune_all_completed=True
                )

            # Recalculate assistant index after pruning
            for i in range(len(self.agent.messages) - 1, -1, -1):
                msg = self.agent.messages[i]
                if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                    return i

        except Exception as e:
            self.printer.warning(f"Failed to prune messages: {e}")

        return current_assistant_idx

    def _write_messages_to_yaml(self) -> None:
        """Write pruned messages to YAML for logging."""
        try:
            iteration_indices = getattr(self.agent, "_iteration_message_indices", None)
            messages_copy = copy.deepcopy(self.agent.messages)
            pruned_messages = prune_note_content(
                messages=messages_copy,
                exclude_index=None,
                verbose=self.printer.is_verbose
            )
            write_messages_to_yaml(
                pruned_messages,
                output_dir=getattr(self.agent, "output_dir", None),
                iteration_indices=iteration_indices
            )
        except Exception as e:
            self.printer.warning(f"Failed to write messages to YAML: {e}")

    def _add_tool_result(
        self,
        tool_call: Any,
        result: Any,
        name: str,
        args: Dict[str, Any],
    ) -> bool:
        """Add a tool result to messages and log it."""
        tool_validation = validate_tool_call(name, args, result, self.agent)
        tool_validation_dict = yaml.safe_load(tool_validation)
        success, _ = check_tool_success(tool_validation_dict)

        self.tool_call_history.append(tool_validation_dict)
        log_tool_call(self.tool_call_history, output_dir=getattr(self.agent, "output_dir", None))

        self.printer.tool_result(name, result, success)

        content = stringify_for_llm(result) if success else yaml.dump(
            tool_validation_dict, default_flow_style=False, sort_keys=False
        )
        self.agent.messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": content
        })

        return success
