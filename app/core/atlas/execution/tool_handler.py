"""Tool Handler - executes tools and manages message history."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional, TYPE_CHECKING, Union

import yaml

from app.core.atlas.execution.validation import validate_tool_call
from app.core.atlas.logging import AgentPrinter
from app.core.atlas.tools.responses import error_response
from app.core.atlas.execution.utils import stringify_for_llm, check_tool_success

if TYPE_CHECKING:
    from app.core.atlas.agents import AgentBase
    from app.core.atlas.models.callbacks import ChatCallback, NoOpChatCallback

from opentelemetry import context as otel_context


# Tools that modify agent state and must run sequentially
SEQUENTIAL_ONLY_TOOLS = {"think"}

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
        self.current_iteration: int = 0  # Set by execution loop for callback events
        self.retry = False

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
            self._sanitize_tool_call_args(tool_calls)
            self.agent.messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            })

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

    def _execute_tools_parallel(
        self,
        parsed_calls: List[tuple]
    ) -> List[Any]:
        """Execute parsed tool calls in parallel. Returns list of results.

        Captures the OTel context from the calling thread and re-attaches it
        in each worker thread so tool spans nest under the iteration span.
        """
        parent_ctx = otel_context.get_current()
        results = []
        try:
            with ThreadPoolExecutor(max_workers=len(parsed_calls)) as executor:
                futures = []
                for tool_call, name, args, parse_error in parsed_calls:
                    if parse_error:
                        futures.append(None) # If error parsing the arguments, we don't execute the tool.
                    else:
                        futures.append(
                            executor.submit(
                                self._execute_tool_with_context,
                                parent_ctx,
                                name,
                                args
                            )
                        )

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

    def _execute_tool_with_context(self, ctx, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool in a worker thread with parent OTel context attached."""
        otel_token = otel_context.attach(ctx)
        try:
            return self._execute_tool(name, args)
        finally:
            otel_context.detach(otel_token)

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

    @staticmethod
    def _sanitize_tool_call_args(tool_calls: List[Any]) -> None:
        """Replace invalid JSON in tool call arguments with '{}' to prevent API 400 errors."""
        for tc in tool_calls:
            try:
                json.loads(tc.function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                tc.function.arguments = "{}"

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

        # This execute tool method is the heart/base of the tool handler.
        # We want to track the tool executions and results in Langfuse.
        with self.agent.langfuse.start_as_current_observation(
            as_type="span",
            name=f"tool: {name}",
        ) as tool_span:

            tool_span.update(input=args, metadata={"tool_name": name})

            try:
                execution_args = args.copy()

                result = func(**execution_args)
                result_str = str(result)

                if len(result_str) > 2000:
                    result_str = result_str[:2000] + "... (truncated)"

                # Reason: Tools that handle errors internally return error_response()
                # without raising. Detect these so the span is flagged ERROR in Langfuse.
                is_tool_error = False
                try:
                    parsed = yaml.safe_load(result) if isinstance(result, str) else result
                    if isinstance(parsed, dict) and parsed.get("success") is False:
                        is_tool_error = True
                except Exception:
                    pass

                if is_tool_error:
                    tool_span.update(level="ERROR", output=result_str)
                else:
                    tool_span.update(output=result_str)

                return result

            except Exception as e:
                error_msg = f"Error executing {name}: {str(e)}"

                tool_span.update(
                    level="ERROR",
                    error=str(e),
                    output={"error": error_msg}
                )

                self.printer.tool_error(error_msg)

                return error_response(error_msg)

    def _add_tool_result(
        self,
        tool_call: Any,
        result: Any,
        name: str,
        args: Dict[str, Any],
    ) -> bool:
        """Add a tool result to messages."""
        tool_validation = validate_tool_call(name, args, result, self.agent)
        tool_validation_dict = yaml.safe_load(tool_validation)
        success, _ = check_tool_success(tool_validation_dict)

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
