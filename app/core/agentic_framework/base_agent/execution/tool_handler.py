"""Tool Handler - Phase 1

Simple tool execution and message management.
Supports parallel execution via asyncio when multiple tools are requested.
"""

import json
from typing import List, Dict, Any, TYPE_CHECKING
from app.core.agentic_framework.base_agent.execution.tool_validation import validate_tool_call
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.logging.message_logger import write_messages_to_yaml
from app.core.agentic_framework.base_agent.logging.tool_trace import log_tool_call
from app.core.agentic_framework.base_agent.context_manager import prune_completed_task_messages, prune_note_content
import yaml
from app.core.agentic_framework.base_agent.utils.models import TaskStatus
from app.core.agentic_framework.tool_lib.common.responses import error_response

if TYPE_CHECKING:
    from ..agent import BaseAgent

# ANSI colors
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RESET = "\033[0m"


class ToolHandler:
    """Handles tool execution and result formatting.

    Responsibilities:
    - Execute tool calls from LLM
    - Parse tool arguments
    - Handle errors gracefully
    - Format results for LLM
    - Update message history
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize with agent reference.

        Args:
            agent: Parent BaseAgent instance
        """
        self.agent = agent
        self.retry = False
        self.tool_call_history = []  # Track all tool calls for this run

    def handle_tool_calls(self, tool_calls: List[Any]) -> None:
        """Execute tool calls and update message history.

        Args:
            tool_calls: List of tool call objects from LLM
        """
        # Add assistant message with tool calls (skip if already added by execution loop)
        last = self.agent.messages[-1] if self.agent.messages else None
        already_added = isinstance(last, dict) and last.get("role") == "assistant" and last.get("tool_calls")
        if not already_added:
            self.agent.messages.append({
                "role": "assistant",
                "content": "",
                "tool_calls": tool_calls
            })

        # Track the index of the current assistant message (needed for pruning exclusion)
        # CRITICAL: When pruning, we must exclude this message to avoid removing it while
        # we're still processing its tool_calls (would orphan tool responses)
        current_assistant_idx = len(self.agent.messages) - 1

        # Execute each tool
        for tool_call in tool_calls:
            name = tool_call.function.name
            args_json = tool_call.function.arguments or "{}"

            # Parse arguments
            args = self._parse_arguments(args_json) # Parse arguments from the tool call output

            # Print tool call with arguments in VERBOSE and DEBUG modes
            if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                print(f"\n[Agent] Calling tool: {_GREEN}{name}{_RESET}")
            elif self.agent.print_mode == PrintMode.SUBAGENT:
                print(f"\n[Sub-agent] Calling tool: {_GREEN}{name}{_RESET}")
            elif self.agent.print_mode == PrintMode.PRODUCTION:
                print(f"  → {name}")

            # NOTE: This is entirely for printing the arguments to the console. It is not used for any functionality
            if args:
                # Filter out internal parameters for display
                display_args = {k: v for k, v in args.items() if k != '_simulation_date'}
                if display_args:
                    if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                        # Print the arguments in a pretty format
                        print(f"   Arguments:")
                        for key, value in display_args.items():
                            print(f"     - {_YELLOW}{key}: {value}{_RESET}")
                    elif self.agent.print_mode == PrintMode.SUBAGENT:
                        print(f"   [Sub-agent] Arguments: {_YELLOW}SUCCESSFULLY PARSED{_RESET}")
                    # PRODUCTION mode: no argument output
                else:
                    if self.agent.print_mode != PrintMode.PRODUCTION:
                        print(f"   Arguments: {_YELLOW}(none){_RESET}")
            else:
                if self.agent.print_mode != PrintMode.PRODUCTION:
                    print(f"   Arguments: {_YELLOW}(none){_RESET}")

            # Execute tool and return the result
            result = self._execute_tool(name, args)

            # Track note titles for display when write_note succeeds
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

            # Context window management: Prune old tool calls at state transitions
            # Key insight: Delete tool calls only AFTER the next state is reached
            # This prevents infinite loops - model needs to see state transitions

            # When marking a task complete, prune old in_progress calls for that task
            if name == "update_tasks" and args.get("status") in ("complete", "completed"):
                try:
                    result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                    if result_dict.get("success"):
                        main_task = args.get("main_task")
                        subtasks = args.get("subtasks")

                        # Prune in_progress tool calls for THIS task (excluding current complete)
                        # Model has seen the in_progress status, now we can clean it up
                        self.agent.messages = prune_completed_task_messages(
                            messages=self.agent.messages,
                            main_task=main_task,
                            subtasks=subtasks,
                            exclude_index=current_assistant_idx,
                            verbose=(self.agent.print_mode != PrintMode.PRODUCTION),
                            prune_status="in_progress"  # Only prune in_progress calls
                        )

                        # Recalculate index after pruning
                        for i in range(len(self.agent.messages) - 1, -1, -1):
                            msg = self.agent.messages[i]
                            if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                                current_assistant_idx = i
                                break

                except Exception as e:
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"⚠️  Warning: Failed to prune in_progress messages: {e}")

            # When starting a new task, prune ALL old completed calls
            elif name == "update_tasks" and args.get("status") == "in_progress":
                try:
                    result_dict = yaml.safe_load(result) if isinstance(result, str) else result
                    if result_dict.get("success"):
                        # Prune ALL completed tool calls from ALL tasks (excluding current in_progress)
                        # Model has seen the completions, now we can clean them up
                        self.agent.messages = prune_completed_task_messages(
                            messages=self.agent.messages,
                            exclude_index=current_assistant_idx,
                            verbose=(self.agent.print_mode != PrintMode.PRODUCTION),
                            prune_all_completed=True  # Prune ALL completed tasks
                        )

                        # Recalculate index after pruning
                        for i in range(len(self.agent.messages) - 1, -1, -1):
                            msg = self.agent.messages[i]
                            if msg.get("role") == "assistant" and msg.get("tool_calls") == tool_calls:
                                current_assistant_idx = i
                                break

                except Exception as e:
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"⚠️  Warning: Failed to prune completed messages: {e}")

            tool_validation = validate_tool_call(name, args, result, self.agent)

            # Parse validation and add to history
            tool_validation_dict = yaml.safe_load(tool_validation)

            success, message = self._check_tool_success(tool_validation_dict)
            
            self.tool_call_history.append(tool_validation_dict)

            # Write entire tool call history to tools.yaml
            log_tool_call(self.tool_call_history, output_dir=getattr(self.agent, "output_dir", None))

            # NOTE: This is entirely for printing the result to the console. It is not used for any functionality
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

        # Write messages to YAML with pruned write_note content (for logging only)
        # CRITICAL: We prune ONLY for YAML writing, NOT for self.agent.messages
        # If we modify self.agent.messages, the LLM will see "[pruned]" in context
        # and copy the pattern in future iterations!
        try:
            import copy
            iteration_indices = getattr(self.agent, "_iteration_message_indices", None)

            # CRITICAL: Deep copy messages before pruning!
            # prune_note_content modifies tool_call objects IN PLACE, so even a shallow
            # copy would still modify the original objects in self.agent.messages
            messages_copy = copy.deepcopy(self.agent.messages)

            # Prune the deep copy (keeps self.agent.messages untouched)
            pruned_messages_for_yaml = prune_note_content(
                messages=messages_copy,
                exclude_index=None,  # Prune all write_note calls for YAML
                verbose=(self.agent.print_mode != PrintMode.PRODUCTION)
            )

            # Write the pruned version to YAML (not self.agent.messages!)
            write_messages_to_yaml(pruned_messages_for_yaml, output_dir=getattr(self.agent, "output_dir", None), iteration_indices=iteration_indices)
        except Exception as e:
            # Don't fail tool execution if logging fails
            print(f"⚠️  Warning: Failed to write messages to YAML: {e}")

    def _parse_arguments(self, args_json: str) -> Dict[str, Any]:
        """Parse tool arguments from JSON string.

        Args:
            args_json: JSON string of arguments

        Returns:
            Parsed arguments dictionary
        """
        try:
            return json.loads(args_json)
        except json.JSONDecodeError:
            print(f"  ⚠️ Could not parse args: {args_json}")
            return {}

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        """Execute a tool with error handling.

        Args:
            name: Tool name
            args: Tool arguments

        Returns:
            Tool result or error message
        """
        func = self.agent.tool_functions.get(name)

        if not func:
            error_msg = f"Tool '{name}' not found. Available: {list(self.agent.tool_functions.keys())}"
            print(f"  ⚠️ {error_msg}")
            return error_response(error_msg)

        try:
            # Auto-inject _simulation_date for simulation agents
            # Make a copy to avoid modifying original args dict (used in validation/logging)
            execution_args = args.copy()
            if self.agent.simulation_date is not None and isinstance(execution_args, dict):
                execution_args['_simulation_date'] = self.agent.simulation_date

            result = func(**execution_args)
            return result
        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            return error_response(error_msg)
    
    def _check_tool_success(self, tool_validation_dict: dict) -> tuple[bool, str]:
        """Check if the tool call was successful.

        A tool is considered successful only if:
        1. success field is True, AND
        2. data field is populated (non-empty)

        Args:
            tool_validation_dict: Dictionary containing tool validation information
                Expected format: {'success': bool, 'data': any, 'error': str (optional)}

        Returns:
            Tuple of (is_successful: bool, error_message: str or None)
            - (True, None) if success=True AND data is non-empty
            - (False, error_msg) if success=False OR data is empty
        """
        # Get success field (default to True for backward compatibility)
        success = tool_validation_dict.get("success", True)

        # If success is explicitly False, tool failed
        if not success:
            error = tool_validation_dict.get("error", "Unknown error")
            return False, error

        # Success is True - now check if data is populated
        data = tool_validation_dict.get("data")

        # Check for None
        if data is None:
            return False, "Tool returned success=True but data is None (no data available)"

        # Check for empty dict
        if isinstance(data, dict) and len(data) == 0:
            return False, "Tool returned success=True but data is empty dict (no data available)"

        # Check for empty list
        if isinstance(data, list) and len(data) == 0:
            return False, "Tool returned success=True but data is empty list (no data available)"

        # Check for empty/whitespace string
        if isinstance(data, str) and data.strip() == "":
            return False, "Tool returned success=True but data is empty string (no data available)"

        # Success is True AND data is populated - tool succeeded!
        return True, None

    def _stringify(self, obj: Any) -> str:
        """Convert any object to string for LLM consumption.

        Args:
            obj: Any Python object

        Returns:
            JSON string or plain string representation
        """
        if isinstance(obj, str):
            return obj

        try:
            # Try JSON serialization with custom handling
            def default_handler(o):
                # Handle Pydantic models
                if hasattr(o, 'model_dump'):
                    return o.model_dump()
                if hasattr(o, 'dict'):
                    return o.dict()
                # Handle dataclasses
                try:
                    import dataclasses
                    if dataclasses.is_dataclass(o):
                        return dataclasses.asdict(o)
                except Exception:
                    pass
                # Fallback to string
                return str(o)

            return json.dumps(obj, default=default_handler, ensure_ascii=False)
        except Exception:
            return str(obj)
