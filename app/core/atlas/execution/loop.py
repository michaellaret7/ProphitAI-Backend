"""ChatAgent execution loop - fast ReAct loop for interactive chat."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from app.core.atlas.execution.tool_handler import should_run_parallel

if TYPE_CHECKING:
    from app.core.atlas.agents.base import AgentBase

class ExecutionLoop:
    """Fast execution loop for chat - no planning, terminates on text-only response."""

    def __init__(self, agent: 'AgentBase'):
        self.agent = agent
        self.printer = agent.printer

    def execute(self, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Run ReAct loop until answer ready or max iterations.

        Args:
            message_id: Optional unique identifier for this message. Generated if not provided.

        Returns:
            Dict with answer, tool_calls, total_tokens, iterations, and stop_reason.
        """
        with self.agent.langfuse.start_as_current_observation(
            as_type="span",
            name="execution_loop",
            input={
                "agent": self.agent.__class__.__name__,
                "model": self.agent.model,
                "max_iterations": self.agent.max_iterations,
                "message_count": len(self.agent.messages),
                "tools": self.agent.get_tool_names(),
            },
        ) as loop_span:

            message_id = message_id or str(uuid.uuid4())
            callback = self.agent.chat_callback

            tool_calls_made: List[str] = []
            assistant_text = ""
            iteration_tokens = 0

            # Emit run started
            callback.on_run_started(
                session_id=self.agent.session_id,
                message_id=message_id,
            )

            try:
                for i in range(1, self.agent.max_iterations + 1):

                    with self.agent.langfuse.start_as_current_observation(
                        as_type="span",
                        name=f"iteration_{i}"
                    ) as iteration_span:
                        iteration_span.update(
                            input=self._build_iteration_input(i),
                            metadata={"iteration": str(i)},
                        )

                        # Set current iteration for tool handler callback events
                        self.agent.tool_handler.current_iteration = i

                        callback.on_iteration_start(iteration=i)
                        self.printer.iteration_start(i, self.agent.max_iterations)

                        response = self.call_llm()
                        iteration_tokens = self._track_token_usage(response)

                        assistant_message = response.choices[0].message
                        assistant_text = assistant_message.content or ""

                        if assistant_message.tool_calls:
                            called_tools = self._handle_tool_calls(
                                assistant_message.tool_calls, assistant_text
                            )
                            tool_calls_made.extend(called_tools)

                            iteration_span.update(output={
                                "action": "tool_calls",
                                "tools_called": called_tools,
                                "assistant_text": assistant_text if assistant_text else None,
                            })

                            callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                        else:
                            # No tool calls = LLM has answer ready
                            self.agent.messages.append({
                                "role": "assistant",
                                "content": assistant_text
                            })

                            iteration_span.update(output={
                                "action": "answer_ready",
                                "answer": assistant_text,
                            })

                            callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                            self.printer.iteration_complete(i, "answer_ready")

                            callback.on_run_finished(
                                answer=assistant_text,
                                tool_calls_made=tool_calls_made,
                                iterations=i,
                                tokens_used=self.agent.total_tokens,
                                stop_reason="answer_ready",
                            )

                            loop_span.update(output={
                                "stop_reason": "answer_ready",
                                "iterations": i,
                                "total_tokens": self.agent.total_tokens,
                            })

                            return {
                                "answer": assistant_text,
                                "tool_calls": tool_calls_made,
                                "total_tokens": self.agent.total_tokens,
                                "iterations": i,
                                "stop_reason": "answer_ready"
                            }

                    # Flush after each iteration so spans appear in Langfuse in real time
                    self.agent.langfuse.flush()

                # Max iterations reached
                callback.on_iteration_end(
                    iteration=self.agent.max_iterations,
                    tokens_used=iteration_tokens,
                )
                self.printer.iteration_complete(self.agent.max_iterations, "max_iterations")

                final_answer = (
                    assistant_text
                    if assistant_text
                    else "Unable to complete request within iteration limit."
                )

                callback.on_run_finished(
                    answer=final_answer,
                    tool_calls_made=tool_calls_made,
                    iterations=self.agent.max_iterations,
                    tokens_used=self.agent.total_tokens,
                    stop_reason="max_iterations",
                )

                loop_span.update(output={
                    "stop_reason": "max_iterations",
                    "iterations": self.agent.max_iterations,
                    "total_tokens": self.agent.total_tokens,
                })

                return {
                    "answer": final_answer,
                    "tool_calls": tool_calls_made,
                    "total_tokens": self.agent.total_tokens,
                    "iterations": self.agent.max_iterations,
                    "stop_reason": "max_iterations"
                }

            except Exception as e:
                callback.on_run_error(error=str(e))
                raise

    def call_llm(self):
        """Make LLM API call."""
        
        return self.agent.client.chat.completions.create(
            model=self.agent.model,
            messages=self.agent.messages,
            tools=self.agent.tools if self.agent.tools else None,
            tool_choice="auto" if self.agent.tools else None,
            temperature=self.agent.temperature,
        )

    def _track_token_usage(self, response) -> int:
        """Track token usage from response.

        Returns:
            Number of tokens used in this call (for iteration_end event).
        """
        if hasattr(response, 'usage') and response.usage:
            iteration_tokens = int(response.usage.total_tokens)
            self.agent.total_tokens = iteration_tokens
            return iteration_tokens
        return 0

    def _build_iteration_input(self, iteration: int) -> Dict[str, Any]:
        """Build a summary of the messages entering this iteration for Langfuse tracing."""
        messages = self.agent.messages
        
        if not messages:
            return {"iteration": iteration, "message_count": 0}

        last_msg = messages[-1]
        last_role = last_msg.get("role", "unknown")
        last_content = last_msg.get("content", "") or ""

        return {
            "iteration": iteration,
            "message_count": len(messages),
            "last_message_role": last_role,
            "last_message_preview": last_content[:500],
        }

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
