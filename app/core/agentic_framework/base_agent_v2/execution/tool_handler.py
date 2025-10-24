"""Tool execution handler for Base Agent V2.

Simple tool execution without automatic advancement or heavy management.
"""

import json
import yaml
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass

if TYPE_CHECKING:
    from ..agent_v2 import AgentV2

from ..core.result_parser import parse_tool_result


@dataclass
class ToolResult:
    """Result from executing a single tool."""
    tool_name: str
    args: Dict[str, Any]
    output: Any  # Raw tool output
    success: bool
    error: Optional[str] = None
    tool_call_id: Optional[str] = None


class ToolHandler:
    """
    Handles tool call execution for V2 agent.

    Simplified from V1:
    - NO automatic task advancement
    - NO automatic tracking/validation
    - Just executes tools and returns results
    - Agent/execution loop handle everything else
    """

    def __init__(self, agent: 'AgentV2'):
        """
        Initialize tool handler.

        Args:
            agent: The AgentV2 instance that owns this handler
        """
        self.agent = agent

    def execute_tool_calls(
        self,
        tool_calls: List[Any],
        conversation_history: List[Dict[str, Any]]
    ) -> List[ToolResult]:
        """
        Execute native tool calls from LLM response.

        Args:
            tool_calls: List of tool call objects from LLM
            conversation_history: Conversation history (will append results)

        Returns:
            List of ToolResult objects
        """
        results: List[ToolResult] = []

        # Print tool execution header
        if self.agent.verbose:
            print(f"\n🔧 TOOL EXECUTION ({len(tool_calls)} tool{'s' if len(tool_calls) > 1 else ''})")
            print(f"{'─' * 80}")

        # Append assistant message with tool calls
        assistant_message = {
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls
        }
        conversation_history.append(assistant_message)

        # Execute each tool call
        for tc in tool_calls:
            tool_name = tc.function.name
            args_json = tc.function.arguments or "{}"

            # Parse arguments
            try:
                args = json.loads(args_json)
            except json.JSONDecodeError as e:
                # Argument parsing failed
                result = ToolResult(
                    tool_name=tool_name,
                    args={},
                    output=None,
                    success=False,
                    error=f"Failed to parse arguments: {e}",
                    tool_call_id=tc.id
                )
                results.append(result)

                # Add error to conversation
                self._add_tool_result_to_conversation(
                    conversation_history,
                    tool_call_id=tc.id,
                    tool_name=tool_name,
                    output=yaml.dump({"success": False, "error": str(e)})
                )
                continue

            # Execute the tool
            try:
                output = self._execute_tool(tool_name, args)
                parsed = parse_tool_result(output)

                result = ToolResult(
                    tool_name=tool_name,
                    args=args,
                    output=output,
                    success=parsed.get('success', False),
                    error=parsed.get('error'),
                    tool_call_id=tc.id
                )
                results.append(result)

                # Add to conversation
                self._add_tool_result_to_conversation(
                    conversation_history,
                    tool_call_id=tc.id,
                    tool_name=tool_name,
                    output=output
                )

            except Exception as e:
                # Tool execution failed
                error_output = yaml.dump({
                    "success": False,
                    "error": f"Tool execution failed: {str(e)}"
                })

                result = ToolResult(
                    tool_name=tool_name,
                    args=args,
                    output=error_output,
                    success=False,
                    error=str(e),
                    tool_call_id=tc.id
                )
                results.append(result)

                # Add error to conversation
                self._add_tool_result_to_conversation(
                    conversation_history,
                    tool_call_id=tc.id,
                    tool_name=tool_name,
                    output=error_output
                )

        # Print completion
        if self.agent.verbose:
            print(f"{'─' * 80}")

        return results

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """
        Execute a registered tool.

        Args:
            tool_name: Name of tool to execute
            args: Arguments for the tool

        Returns:
            Tool output (usually YAML string)

        Raises:
            ValueError: If tool not found
            Exception: If tool execution fails
        """
        # Get tool from registry
        if not hasattr(self.agent, 'tools') or tool_name not in self.agent.tools:
            raise ValueError(f"Tool '{tool_name}' not found in registry")

        tool_func = self.agent.tools[tool_name]

        # Print tool execution details
        if self.agent.verbose:
            print(f"\n  Tool: {tool_name}")
            if args:
                # Format args nicely - show full args, no truncation
                args_str = json.dumps(args, indent=4)
                print(f"  Args: {args_str}")
            else:
                print(f"  Args: None")

        # Execute tool
        try:
            result = tool_func(**args)

            # Print full tool output
            if self.agent.verbose:
                print(f"\n  Output:")
                # Show full result, no truncation
                result_str = str(result)
                # Indent each line for readability
                for line in result_str.split('\n'):
                    print(f"    {line}")

                # Print success indicator at the end
                try:
                    if isinstance(result, str) and ('success:' in result.lower() or 'error:' in result.lower()):
                        if 'success: true' in result.lower():
                            print(f"\n  Status: ✓ Success")
                        elif 'success: false' in result.lower():
                            print(f"  Status: ✗ Failed")
                        else:
                            print(f"\n  Status: Completed")
                    else:
                        print(f"\n  Status: Completed")
                except:
                    print(f"\n  Status: Completed")

            return result
        except Exception as e:
            if self.agent.verbose:
                print(f"\n  Status: ✗ Error - {str(e)}")
            # Re-raise with context
            raise Exception(f"Tool '{tool_name}' execution failed: {e}") from e

    def _add_tool_result_to_conversation(
        self,
        conversation_history: List[Dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        output: Any
    ) -> None:
        """
        Add tool result to conversation history.

        Args:
            conversation_history: Conversation history (modified in place)
            tool_call_id: ID of the tool call
            tool_name: Name of tool
            output: Tool output
        """
        # Convert output to string if needed
        output_str = str(output) if not isinstance(output, str) else output

        # Add tool result message
        tool_message = {
            "role": "tool",
            "content": output_str,
            "tool_call_id": tool_call_id,
            "name": tool_name
        }
        conversation_history.append(tool_message)