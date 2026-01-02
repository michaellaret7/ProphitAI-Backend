"""Parallel Tool Call Executor

Handles concurrent execution of multiple tool calls using asyncio.
Used when the LLM requests multiple tools that can safely run in parallel.
"""

#TODO: Delete this its no longer needed, tool handler parallel is the new way to handle mutliple tool calls 

import asyncio
from typing import List, Dict, Any, TYPE_CHECKING
import yaml

from app.core.agentic_framework.base_agent.execution.tool_validation import validate_tool_call
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.logging.tool_trace import log_tool_call
from app.core.agentic_framework.base_agent.logging.message_logger import write_messages_to_yaml
from app.core.agentic_framework.base_agent.context_manager import prune_note_content
from app.core.agentic_framework.tool_lib.common.responses import error_response
import copy

if TYPE_CHECKING:
    from app.core.agentic_framework.base_agent.execution.tool_handler import ToolHandler

# ANSI colors
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

# Tools that modify agent state and must run sequentially
SEQUENTIAL_ONLY_TOOLS = {
    # "update_tasks",
    "write_note",
    # "edit_plan",
    "finalize",
    "think"
}

def should_run_parallel(tool_calls: List[Any]) -> bool:
    """Determine if tool calls can be executed in parallel.

    Parallel execution is safe when:
    1. There are multiple tool calls (>1)
    2. None of the tools are in SEQUENTIAL_ONLY_TOOLS

    Args:
        tool_calls: List of tool call objects from LLM

    Returns:
        True if parallel execution is safe, False otherwise
    """
    if len(tool_calls) <= 1:
        return False

    for tool_call in tool_calls:
        if tool_call.function.name in SEQUENTIAL_ONLY_TOOLS:
            return False

    return True


async def _execute_tool_async(
    tool_handler: 'ToolHandler',
    name: str,
    args: Dict[str, Any]
) -> Any:
    """Execute a tool asynchronously.

    Wraps sync functions with asyncio.to_thread for non-blocking execution.

    Args:
        tool_handler: ToolHandler instance with tool functions
        name: Tool name
        args: Tool arguments

    Returns:
        Tool result or error message
    """
    func = tool_handler.agent.tool_functions.get(name)

    if not func:
        error_msg = f"Tool '{name}' not found. Available: {list(tool_handler.agent.tool_functions.keys())}"
        return error_response(error_msg)

    try:
        # Auto-inject _simulation_date for simulation agents
        execution_args = args.copy()
        if tool_handler.agent.simulation_date is not None:
            execution_args['_simulation_date'] = tool_handler.agent.simulation_date

        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            result = await func(**execution_args)
        else:
            # Run sync function in thread pool to avoid blocking
            result = await asyncio.to_thread(func, **execution_args)

        return result
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return error_response(error_msg)


def execute_tools_parallel(
    tool_handler: 'ToolHandler',
    tool_calls: List[Any],
    current_assistant_idx: int  # NOTE: Currently unused - reserved for future pruning support
) -> None:
    """Execute multiple tool calls in parallel using asyncio.

    Args:
        tool_handler: ToolHandler instance
        tool_calls: List of tool call objects from LLM
        current_assistant_idx: Index of current assistant message (reserved for pruning, not yet implemented)

    Note:
        Unlike the sequential tool_handler.handle_tool_calls(), this function does NOT implement
        context pruning for update_tasks calls. This is intentional since parallel execution
        is only used for data-fetching tools (not state-modifying tools like update_tasks).
    """
    agent = tool_handler.agent
    num_tools = len(tool_calls)

    # Print parallel execution header (all modes)
    if agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
        print(f"\n{_CYAN}🔀 Parallel execution: {num_tools} tools{_RESET}")
    elif agent.print_mode == PrintMode.SUBAGENT:
        print(f"\n[Sub-agent] 🔀 Parallel execution: {num_tools} tools")
    elif agent.print_mode == PrintMode.PRODUCTION:
        print(f"  🔀 {num_tools} tools (parallel)")

    # Parse all arguments upfront
    parsed_calls = []
    for tool_call in tool_calls:
        name = tool_call.function.name
        args_json = tool_call.function.arguments or "{}"
        args, parse_error = tool_handler._parse_arguments(args_json)
        parsed_calls.append((tool_call, name, args, parse_error))

        # Print tool names being executed (all modes)
        if agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
            print(f"   → {_GREEN}{name}{_RESET}")
        elif agent.print_mode == PrintMode.SUBAGENT:
            print(f"   → {_GREEN}{name}{_RESET}")
        elif agent.print_mode == PrintMode.PRODUCTION:
            print(f"    → {name}")

    # Helper to create async wrapper for parse errors
    async def _return_parse_error(err: str):
        return error_response(f"Argument parse failed: {err}")

    # Define async runner for all tools (skip tools with parse errors)
    async def run_all():
        tasks = []
        for tool_call, name, args, parse_error in parsed_calls:
            if parse_error:
                # Return parse error as result instead of executing
                tasks.append(_return_parse_error(parse_error))
            else:
                tasks.append(_execute_tool_async(tool_handler, name, args))
        return await asyncio.gather(*tasks, return_exceptions=True)

    # Execute all tools in parallel
    try:
        results = asyncio.run(run_all())
    except Exception as e:
        # If asyncio.run fails, we still need to add tool responses to prevent malformed history
        print(f"⚠️ Parallel execution failed: {e}")
        results = [error_response(f"Parallel execution failed: {e}")] * len(parsed_calls)

    # Process results sequentially (for proper message ordering and validation)
    for (tool_call, name, args, _parse_error), result in zip(parsed_calls, results):
        # Handle exceptions from gather
        if isinstance(result, Exception):
            result = error_response(f"Error executing {name}: {str(result)}")

        # Track note titles (for write_note tool)
        if name == "write_note":
            try:
                result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                if result_dict.get("success") and "title" in args:
                    title = args["title"]
                    if title not in agent.note_titles:
                        agent.note_titles.append(title)
            except Exception:
                pass

        # Validate tool call result
        tool_validation = validate_tool_call(name, args, result, agent)
        tool_validation_dict = yaml.safe_load(tool_validation)
        success, _ = tool_handler._check_tool_success(tool_validation_dict)

        # Add to tool call history
        tool_handler.tool_call_history.append(tool_validation_dict)

        # Print result summary (all modes)
        status = "✓" if success else "✗"
        if agent.print_mode == PrintMode.DEBUG:
            print(f"   {_GREEN}{name}{_RESET} ← {result}")
        elif agent.print_mode == PrintMode.VERBOSE:
            result_str = str(result)
            if len(result_str) > 100:
                print(f"   {status} {_GREEN}{name}{_RESET}: {result_str[:100]}...")
            else:
                print(f"   {status} {_GREEN}{name}{_RESET}: {result_str}")
        elif agent.print_mode == PrintMode.SUBAGENT:
            print(f"   {status} {_GREEN}{name}{_RESET}")
        elif agent.print_mode == PrintMode.PRODUCTION:
            print(f"    {status} {name}")

        # Append tool result message to conversation
        if success:
            agent.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": tool_handler._stringify(result)
            })
        else:
            agent.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": yaml.dump(tool_validation_dict, default_flow_style=False, sort_keys=False)
            })

    # Log tool call history
    log_tool_call(tool_handler.tool_call_history, output_dir=getattr(agent, "output_dir", None))

    # Write messages to YAML with pruned write_note content (for logging only)
    # Mirrors the behavior in tool_handler.handle_tool_calls()
    try:
        iteration_indices = getattr(agent, "_iteration_message_indices", None)
        messages_copy = copy.deepcopy(agent.messages)
        pruned_messages = prune_note_content(
            messages=messages_copy,
            exclude_index=None,
            verbose=(agent.print_mode != PrintMode.PRODUCTION)
        )
        write_messages_to_yaml(
            pruned_messages,
            output_dir=getattr(agent, "output_dir", None),
            iteration_indices=iteration_indices
        )
    except Exception as e:
        print(f"⚠️  Warning: Failed to write messages to YAML: {e}")


