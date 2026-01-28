"""ChatAgent execution loop - fast ReAct loop for interactive chat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, List

from app.core.agentic_framework.base_agent.execution.tool_handler_parallel import (
    should_run_parallel,
    execute_tools_parallel,
)
from app.core.atlas.models import PrintMode

if TYPE_CHECKING:
    from app.core.atlas.agents.chat_agent import ChatAgent

# ANSI colors
_GREEN = "\033[32m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

class ChatExecutionLoop:
    """Fast execution loop for chat - no planning, terminates on text-only response."""

    def __init__(self, agent: 'ChatAgent'):
        self.agent = agent

    def execute(self) -> Dict[str, Any]:
        """Run ReAct loop until answer ready or max iterations."""
        tool_calls_made: List[str] = []
        assistant_text = ""

        for i in range(1, self.agent.max_iterations + 1):
            if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                print(f"\n{_CYAN}[Chat] Iteration {i}/{self.agent.max_iterations}{_RESET}")

            # Call LLM
            response = self.agent.client.chat.completions.create(
                model=self.agent.model,
                messages=self.agent.messages,
                tools=self.agent.tools if self.agent.tools else None,
                tool_choice="auto" if self.agent.tools else None,
                temperature=self.agent.temperature,
            )

            # Track tokens if token usage is in the llm output response
            if hasattr(response, 'usage') and response.usage:
                self.agent.total_tokens = int(response.usage.total_tokens)

            assistant_message = response.choices[0].message # --> this is the assistant message from the llm response
            assistant_text = assistant_message.content or ""

            # Handle tool calls
            if assistant_message.tool_calls: # --> if these tool calls exist in the llm response, execute them using the tool handler method
                tool_calls = assistant_message.tool_calls

                # Add assistant message with tool calls
                self.agent.messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "tool_calls": tool_calls
                })

                # Execute tools (reuse existing handlers)
                if should_run_parallel(tool_calls):
                    execute_tools_parallel(
                        self.agent.tool_handler,
                        tool_calls,
                        len(self.agent.messages) - 1
                    )
                else:
                    self.agent.tool_handler.handle_tool_calls(tool_calls)

                # Track tool calls made
                tool_calls_made.extend([tc.function.name for tc in tool_calls])

            else:
                # No tool calls = LLM has answer ready
                self.agent.messages.append({
                    "role": "assistant",
                    "content": assistant_text
                })

                if self.agent.print_mode == PrintMode.VERBOSE:
                    print(f"\n{_GREEN}[Chat] Answer ready after {i} iteration(s){_RESET}")

                return {
                    "answer": assistant_text,
                    "tool_calls": tool_calls_made,
                    "total_tokens": self.agent.total_tokens,
                    "iterations": i,
                    "stop_reason": "answer_ready"
                }

        # Max iterations reached - return last response
        if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG, PrintMode.PRODUCTION]:
            print(f"\n{_CYAN}[Chat] Max iterations reached{_RESET}")

        return {
            "answer": assistant_text if assistant_text else "Unable to complete request within iteration limit.",
            "tool_calls": tool_calls_made,
            "total_tokens": self.agent.total_tokens,
            "iterations": self.agent.max_iterations,
            "stop_reason": "max_iterations"
        }
