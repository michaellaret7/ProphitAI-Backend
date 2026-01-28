"""Parallel Tool Call Executor - concurrent execution using ThreadPoolExecutor."""

from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, TYPE_CHECKING
import yaml
import copy

from app.core.agentic_framework.base_agent.execution.tool_validation import validate_tool_call
from app.core.atlas.models import PrintMode
from app.core.agentic_framework.base_agent.logging.tool_trace import log_tool_call
from app.core.agentic_framework.base_agent.logging.message_logger import write_messages_to_yaml
from app.core.atlas.context import prune_note_content
from app.core.agentic_framework.tool_lib.common.responses import error_response

if TYPE_CHECKING:
    from app.core.atlas.execution.tool_handler import ToolHandler

# ANSI colors
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

# Tools that modify agent state and must run sequentially
SEQUENTIAL_ONLY_TOOLS = {
    "write_note",
    "finalize",
    "think"
}

def should_run_parallel(tool_calls: List[Any]) -> bool:
    """Determine if tool calls can be executed in parallel."""
    if len(tool_calls) <= 1:
        return False

    for tool_call in tool_calls:
        if tool_call.function.name in SEQUENTIAL_ONLY_TOOLS:
            return False

    return True

def _execute_tool(
    tool_handler: 'ToolHandler',
    name: str,
    args: Dict[str, Any]
) -> Any:
    """Execute a tool synchronously (called from ThreadPoolExecutor)."""
    func = tool_handler.agent.tool_functions.get(name)

    if not func:
        error_msg = f"Tool '{name}' not found. Available: {list(tool_handler.agent.tool_functions.keys())}"
        return error_response(error_msg)

    try:
        execution_args = args.copy()
        if getattr(tool_handler.agent, 'simulation_date', None) is not None:
            execution_args['_simulation_date'] = tool_handler.agent.simulation_date

        return func(**execution_args)

    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return error_response(error_msg)


def execute_tools_parallel(
    tool_handler: 'ToolHandler',
    tool_calls: List[Any],
    current_assistant_idx: int
) -> None:
    """Execute multiple tool calls in parallel using ThreadPoolExecutor."""
    agent = tool_handler.agent
    num_tools = len(tool_calls)

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

        if agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
            print(f"   → {_GREEN}{name}{_RESET}")
        elif agent.print_mode == PrintMode.SUBAGENT:
            print(f"   → {_GREEN}{name}{_RESET}")
        elif agent.print_mode == PrintMode.PRODUCTION:
            print(f"    → {name}")

    # Execute all tools in parallel
    results = []
    try:
        with ThreadPoolExecutor(max_workers=len(parsed_calls)) as executor:
            futures = []
            for tool_call, name, args, parse_error in parsed_calls:
                if parse_error:
                    futures.append(None)
                else:
                    futures.append(executor.submit(_execute_tool, tool_handler, name, args))

            for i, (tool_call, name, args, parse_error) in enumerate(parsed_calls):
                if parse_error:
                    results.append(error_response(f"Argument parse failed: {parse_error}"))
                else:
                    try:
                        results.append(futures[i].result())
                    except Exception as e:
                        results.append(error_response(f"Error executing {name}: {str(e)}"))
    except Exception as e:
        print(f"⚠️ Parallel execution failed: {e}")
        results = [error_response(f"Parallel execution failed: {e}")] * len(parsed_calls)

    # Process results sequentially
    for (tool_call, name, args, _parse_error), result in zip(parsed_calls, results):

        if name == "write_note":
            try:
                result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                if result_dict.get("success") and "title" in args:
                    title = args["title"]
                    if title not in agent.note_titles:
                        agent.note_titles.append(title)
            except Exception:
                pass

        tool_validation = validate_tool_call(name, args, result, agent)
        tool_validation_dict = yaml.safe_load(tool_validation)
        success, _ = tool_handler._check_tool_success(tool_validation_dict)

        tool_handler.tool_call_history.append(tool_validation_dict)

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

    log_tool_call(tool_handler.tool_call_history, output_dir=getattr(agent, "output_dir", None))

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
