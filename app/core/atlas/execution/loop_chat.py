"""ChatAgent execution loop - fast ReAct loop for interactive chat."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any, List

from app.core.atlas.execution.tool_handler import should_run_parallel

if TYPE_CHECKING:
    from app.core.atlas.agents.chat_agent import ChatAgent


class ChatExecutionLoop:
    """Fast execution loop for chat - no planning, terminates on text-only response."""

    def __init__(self, agent: 'ChatAgent'):
        self.agent = agent
        self.printer = agent.printer

    def execute(self) -> Dict[str, Any]:
        """Run ReAct loop until answer ready or max iterations."""
        tool_calls_made: List[str] = []
        assistant_text = ""

        for i in range(1, self.agent.max_iterations + 1):
            self.printer.iteration_start(i, self.agent.max_iterations)

            response = self._call_llm()
            self._track_token_usage(response)

            assistant_message = response.choices[0].message
            assistant_text = assistant_message.content or ""

            if assistant_message.tool_calls:
                tool_calls_made.extend(
                    self._handle_tool_calls(assistant_message.tool_calls, assistant_text)
                )
            else:
                # No tool calls = LLM has answer ready
                self.agent.messages.append({
                    "role": "assistant",
                    "content": assistant_text
                })
                
                self.printer.iteration_complete(i, "answer_ready")

                return {
                    "answer": assistant_text,
                    "tool_calls": tool_calls_made,
                    "total_tokens": self.agent.total_tokens,
                    "iterations": i,
                    "stop_reason": "answer_ready"
                }

        # Max iterations reached
        self.printer.iteration_complete(self.agent.max_iterations, "max_iterations")

        return {
            "answer": assistant_text if assistant_text else "Unable to complete request within iteration limit.",
            "tool_calls": tool_calls_made,
            "total_tokens": self.agent.total_tokens,
            "iterations": self.agent.max_iterations,
            "stop_reason": "max_iterations"
        }

    def _call_llm(self):
        """Make LLM API call."""
        return self.agent.client.chat.completions.create(
            model=self.agent.model,
            messages=self.agent.messages,
            tools=self.agent.tools if self.agent.tools else None,
            tool_choice="auto" if self.agent.tools else None,
            temperature=self.agent.temperature,
        )

    def _track_token_usage(self, response) -> None:
        """Track token usage from response."""
        if hasattr(response, 'usage') and response.usage:
            self.agent.total_tokens = int(response.usage.total_tokens)

    def _handle_tool_calls(self, tool_calls, assistant_text: str) -> List[str]:
        """Execute tool calls and return list of tool names called."""
        self.agent.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "tool_calls": tool_calls
        })

        if should_run_parallel(tool_calls):
            self.agent.tool_handler.handle_tool_calls_parallel(tool_calls)
        else:
            self.agent.tool_handler.handle_tool_calls(tool_calls)

        return [tc.function.name for tc in tool_calls]
