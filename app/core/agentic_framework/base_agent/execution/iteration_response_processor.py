"""Iteration response processor for ReAct loop.

This module processes a single LLM response by coordinating
the FinalityChecker and ToolCallHandler components.
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from ..agent import BaseAgent

from ..core.utilities import StepTrace
from .tool_call_handler import ToolResult, ToolCallHandler
from .finality_checker import FinalityChecker


@dataclass
class IterationResult:
    """Result from executing a single ReAct iteration."""
    iteration: int
    assistant_raw: str
    step_trace: StepTrace
    tool_results: List[ToolResult] = field(default_factory=list)
    is_final: bool = False
    final_text: Optional[str] = None
    stop_reason: Optional[str] = None


class IterationResponseProcessor:
    """Processes a single LLM response in the ReAct loop.

    This class coordinates the FinalityChecker and ToolCallHandler
    to process each LLM response, managing the flow between tool execution
    and finality detection.
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize iteration response processor with component dependencies.

        Args:
            agent: The BaseAgent instance that owns this processor
        """
        self.agent = agent
        self.finality_checker = FinalityChecker(agent)
        self.tool_handler = ToolCallHandler(agent)

    def execute_iteration(
        self,
        iteration: int,
        messages: List[Dict[str, Any]],
        assistant_message: Any,
        assistant_raw: str,
        tools: List[Dict[str, Any]],
        tool_functions: Dict[str, Any]
    ) -> IterationResult:
        """Execute a single ReAct iteration (response processing only).

        NOTE: This method does NOT make the LLM API call - that is done by
        AgentExecutionLoop. This method only processes the LLM response.

        This method:
        1. Receives LLM response from AgentExecutionLoop
        2. Handles tool calls (if any) or checks for finality
        3. Updates conversation state
        4. Returns structured iteration result

        Args:
            iteration: Current iteration number
            messages: Conversation history
            assistant_message: The LLM response message object
            assistant_raw: The raw text content from the assistant
            tools: Available tools (OpenAI format)
            tool_functions: Map of tool names to callable functions

        Returns:
            IterationResult containing execution details
        """
        # Use the provided assistant message (LLM call already made by AgentExecutionLoop)
        msg = assistant_message

        if self.agent.verbose:
            print("  assistant_raw:", assistant_raw)

        # Create step trace
        step = StepTrace(iteration=iteration, assistant_raw=assistant_raw)

        # Initialize result
        result = IterationResult(
            iteration=iteration,
            assistant_raw=assistant_raw,
            step_trace=step
        )

        # Handle native tool calls
        if msg.tool_calls:
            tool_results = self.tool_handler.handle_tool_calls(msg.tool_calls, messages)
            result.tool_results = tool_results

            # Update step trace for agent interface
            if tool_results:
                first_result = tool_results[0]
                step.tool_call = {"name": first_result.tool_name, "args": first_result.args}
                step.observation = first_result.observation

        # Handle content-based tool calls or finality
        else:
            # Check for finality first
            is_final, final_text = self.finality_checker.check_finality(assistant_raw)

            if is_final:
                result.is_final = True
                result.final_text = final_text
                result.stop_reason = "final_message"
            else:
                # Try to parse JSON tool call from content
                content_tool = self.agent.utilities.maybe_parse_json_step(assistant_raw)

                if content_tool:
                    tool_result = self.tool_handler.handle_content_tool_call(content_tool, messages)
                    if tool_result:
                        result.tool_results = [tool_result]
                        step.tool_call = {"name": tool_result.tool_name, "args": tool_result.args}
                        step.observation = tool_result.observation

        return result
