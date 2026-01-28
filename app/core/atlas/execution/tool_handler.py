"""Tool Handler - executes tools and manages message history."""

import json
from typing import List, Dict, Any, TYPE_CHECKING
from app.core.agentic_framework.base_agent.execution.tool_validation import validate_tool_call
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.logging.message_logger import write_messages_to_yaml
from app.core.agentic_framework.base_agent.logging.tool_trace import log_tool_call
from app.core.agentic_framework.base_agent.context_manager import prune_completed_task_messages, prune_note_content, prune_think_content
import yaml
from app.core.agentic_framework.base_agent.utils.models import TaskStatus
from app.core.agentic_framework.tool_lib.common.responses import error_response

if TYPE_CHECKING:
    from app.core.atlas.agents import AgentBase

# ANSI colors
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


class ToolHandler:
    """Handles tool execution and result formatting."""

    def __init__(self, agent: 'AgentBase'):
        self.agent = agent
        self.retry = False
        self.tool_call_history = []

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
            args_json = tool_call.function.arguments or "{}"

            args, parse_error = self._parse_arguments(args_json)

            if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                print(f"\n[Agent] Calling tool: {_GREEN}{name}{_RESET}")
            elif self.agent.print_mode == PrintMode.SUBAGENT:
                print(f"\n[Sub-agent] Calling tool: {_GREEN}{name}{_RESET}")
            elif self.agent.print_mode == PrintMode.PRODUCTION:
                print(f"  → {name}")

            if parse_error:
                if self.agent.print_mode != PrintMode.PRODUCTION:
                    print(f"   ⚠️ Argument parse failed - skipping tool execution")
                result = error_response(
                    f"Tool '{name}' was not executed because arguments could not be parsed. "
                    f"{parse_error}. Please retry the tool call with valid JSON arguments."
                )
                self._add_tool_result(tool_call, result, name, args)
                continue

            if args:
                display_args = {k: v for k, v in args.items() if k != '_simulation_date'}
                if display_args:
                    if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                        print(f"   Arguments:")
                        for key, value in display_args.items():
                            print(f"     - {_YELLOW}{key}: {value}{_RESET}")
                    elif self.agent.print_mode == PrintMode.SUBAGENT:
                        print(f"   [Sub-agent] Arguments: {_YELLOW}SUCCESSFULLY PARSED{_RESET}")
                else:
                    if self.agent.print_mode != PrintMode.PRODUCTION:
                        print(f"   Arguments: {_YELLOW}(none){_RESET}")
            else:
                if self.agent.print_mode != PrintMode.PRODUCTION:
                    print(f"   Arguments: {_YELLOW}(none){_RESET}")

            result = self._execute_tool(name, args)

            if name == "write_note":
                try:
                    result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                    if result_dict.get("success") and "title" in args:
                        title = args["title"]
                        if title not in self.agent.note_titles:
                            self.agent.note_titles.append(title)
                            if self.agent.print_mode != PrintMode.PRODUCTION:
                                print(f"📝 Added note title to notebook: '{title}'")
                except Exception as e:
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"⚠️  Warning: Failed to track note title: {e}")

            if name == "update_tasks" and args.get("status") in ("complete", "completed"):
                try:
                    result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                    if result_dict.get("success"):
                        main_task = args.get("main_task")
                        subtasks = args.get("subtasks")

                        self.agent.messages = prune_completed_task_messages(
                            messages=self.agent.messages,
                            main_task=main_task,
                            subtasks=subtasks,
                            exclude_index=current_assistant_idx,
                            verbose=(self.agent.print_mode != PrintMode.PRODUCTION),
                            prune_status="in_progress"
                        )

                        for i in range(len(self.agent.messages) - 1, -1, -1):
                            msg = self.agent.messages[i]
                            if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                                current_assistant_idx = i
                                break

                except Exception as e:
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"⚠️  Warning: Failed to prune in_progress messages: {e}")

            elif name == "update_tasks" and args.get("status") == "in_progress":
                try:
                    result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                    if result_dict.get("success"):
                        self.agent.messages = prune_completed_task_messages(
                            messages=self.agent.messages,
                            exclude_index=current_assistant_idx,
                            verbose=(self.agent.print_mode != PrintMode.PRODUCTION),
                            prune_all_completed=True
                        )

                        for i in range(len(self.agent.messages) - 1, -1, -1):
                            msg = self.agent.messages[i]
                            if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                                current_assistant_idx = i
                                break

                except Exception as e:
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"⚠️  Warning: Failed to prune completed messages: {e}")

            self._add_tool_result(tool_call, result, name, args)

        try:
            import copy
            iteration_indices = getattr(self.agent, "_iteration_message_indices", None)
            messages_copy = copy.deepcopy(self.agent.messages)
            pruned_messages_for_yaml = prune_note_content(
                messages=messages_copy,
                exclude_index=None,
                verbose=(self.agent.print_mode != PrintMode.PRODUCTION)
            )
            write_messages_to_yaml(pruned_messages_for_yaml, output_dir=getattr(self.agent, "output_dir", None), iteration_indices=iteration_indices)
        except Exception as e:
            print(f"⚠️  Warning: Failed to write messages to YAML: {e}")

    def _parse_arguments(self, args_json: str) -> tuple[Dict[str, Any], str | None]:
        """Parse tool arguments from JSON string."""
        try:
            return json.loads(args_json), None
        except json.JSONDecodeError as e:
            display_json = args_json[:200] + "..." if len(args_json) > 200 else args_json
            print(f" Could not parse args: {display_json}")
            error_msg = f"Failed to parse tool arguments (invalid JSON): {str(e)}"
            return {}, error_msg

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with error handling."""
        func = self.agent.tool_functions.get(name)

        if not func:
            error_msg = f"Tool '{name}' not found. Available: {list(self.agent.tool_functions.keys())}"
            print(f"  ⚠️ {error_msg}")
            return error_response(error_msg)

        try:
            execution_args = args.copy()
            if getattr(self.agent, 'simulation_date', None) is not None and isinstance(execution_args, dict):
                execution_args['_simulation_date'] = self.agent.simulation_date

            result = func(**execution_args)
            return result
        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            return error_response(error_msg)

    def _check_tool_success(self, tool_validation_dict: dict) -> tuple[bool, str]:
        """Check if the tool call was successful."""
        success = tool_validation_dict.get("success", True)

        if not success:
            error = tool_validation_dict.get("error", "Unknown error")
            return False, error

        data = tool_validation_dict.get("data")

        if data is None:
            return False, "Tool returned success=True but data is None (no data available)"

        if isinstance(data, dict) and len(data) == 0:
            return False, "Tool returned success=True but data is empty dict (no data available)"

        if isinstance(data, list) and len(data) == 0:
            return False, "Tool returned success=True but data is empty list (no data available)"

        if isinstance(data, str) and data.strip() == "":
            return False, "Tool returned success=True but data is empty string (no data available)"

        return True, None

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
        success, _ = self._check_tool_success(tool_validation_dict)

        self.tool_call_history.append(tool_validation_dict)
        log_tool_call(self.tool_call_history, output_dir=getattr(self.agent, "output_dir", None))

        if self.agent.print_mode == PrintMode.DEBUG:
            print(f"  ← Result: {result}")
        elif self.agent.print_mode == PrintMode.VERBOSE:
            result_str = str(result)
            if len(result_str) > 200:
                print(f"   ✓ Result: {result_str[:200]}... (truncated)")
            else:
                print(f"   ✓ Result: {result_str}")
        elif self.agent.print_mode == PrintMode.SUBAGENT:
            print(f"[Sub-agent] {name} tool call successful: {success}")

        if success:
            self.agent.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": self._stringify(result)
            })
        else:
            self.agent.messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": yaml.dump(tool_validation_dict, default_flow_style=False, sort_keys=False)
            })

        return success

    def _stringify(self, obj: Any) -> str:
        """Convert any object to string for LLM consumption."""
        if isinstance(obj, str):
            return obj

        try:
            def default_handler(o):
                if hasattr(o, 'model_dump'):
                    return o.model_dump()
                if hasattr(o, 'dict'):
                    return o.dict()
                try:
                    import dataclasses
                    if dataclasses.is_dataclass(o):
                        return dataclasses.asdict(o)
                except Exception:
                    pass
                return str(o)

            return json.dumps(obj, default=default_handler, ensure_ascii=False)
        except Exception:
            return str(obj)
