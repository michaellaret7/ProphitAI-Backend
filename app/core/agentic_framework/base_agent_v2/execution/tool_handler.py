"""Tool Handler - Phase 1

Simple tool execution and message management.
"""

import json
from typing import List, Dict, Any, TYPE_CHECKING
from app.core.agentic_framework.base_agent_v2.execution.tool_validation import check_tool_success
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode
from app.core.agentic_framework.base_agent_v2.logging.message_logger import write_messages_to_yaml
from app.core.agentic_framework.base_agent_v2.logging.tool_trace import log_tool_call
import yaml
from app.core.agentic_framework.base_agent_v2.utils.models import TaskStatus

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
        # Add assistant message with tool calls
        self.agent.messages.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls
        })

        # Execute each tool
        for tool_call in tool_calls:
            name = tool_call.function.name
            args_json = tool_call.function.arguments or "{}"

            # Parse arguments
            args = self._parse_arguments(args_json) # Parse arguments from the tool call output

            # Print tool call with arguments in VERBOSE and DEBUG modes
            print(f"\nCalling tool: {_GREEN}{name}{_RESET}")
            if args:
                print(f"   Arguments:")
                for key, value in args.items():
                    print(f"     - {_YELLOW}{key}: {value}{_RESET}")
            else:
                print(f"   Arguments: {_YELLOW}(none){_RESET}")

            # Execute tool and return the result
            result = self._execute_tool(name, args)

            # NOTE: We need to check if the tool was successful and if not, we need to add the tool to the tool trace file
            tool_validation = check_tool_success(name, args, result, self.agent)

            # Parse validation and add to history
            tool_validation_dict = yaml.safe_load(tool_validation)
            self.tool_call_history.append(tool_validation_dict)

            # Write entire tool call history to tools.yaml
            log_tool_call(self.tool_call_history)

            success = tool_validation_dict["success"]
            
            if self.agent.print_mode == PrintMode.DEBUG:
                print(f"  ← Result: {result}")
            elif self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.PRODUCTION]:
                result_str = str(result)
                if len(result_str) > 200:
                    print(f"   ✓ Result: {result_str[:200]}... (truncated)")
                else:
                    print(f"   ✓ Result: {result_str}")

            if success:
                # if tool call was successful, append the tool result to the messages
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

        try:
            write_messages_to_yaml(self.agent.messages)
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
            return {"error": error_msg}

        try:
            result = func(**args)
            return result
        except Exception as e:
            error_msg = f"Error executing {name}: {str(e)}"
            print(f"  ⚠️ {error_msg}")
            return {"error": error_msg}

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
