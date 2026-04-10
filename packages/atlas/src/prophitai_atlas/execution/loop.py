"""ChatAgent execution loop - fast ReAct loop for interactive chat."""

from __future__ import annotations

import json
import uuid
from typing import TYPE_CHECKING, Dict, Any, List, Optional

from prophitai_atlas.execution.tool_handler import should_run_parallel
from prophitai_atlas.models.new_plan import TaskStatus
from prophitai_shared import NormalizedLLMResponse, NormalizedToolCall

if TYPE_CHECKING:
    from prophitai_atlas.agents.base import AgentBase

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
            Dict with answer, tool_calls, total_tokens, cache token stats, iterations, and stop_reason.
        """
        with self.agent.langfuse.start_as_current_observation(
            as_type="chain",
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

            tool_names = self.agent.get_tool_names()
            print(f"Registered tools ({len(tool_names)}): {sorted(tool_names)}")

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
                        iteration_usage = self._build_iteration_usage(response)

                        assistant_text = response.assistant_text

                        if response.tool_calls:
                            called_tools = self._handle_tool_calls(
                                response.tool_calls, assistant_text
                            )
                            tool_calls_made.extend(called_tools)

                            iteration_span.update(output={
                                "action": "tool_calls",
                                "tools_called": called_tools,
                                "assistant_text": assistant_text if assistant_text else None,
                                "usage": iteration_usage,
                            })

                            callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                        else:
                            # No tool calls — check for empty answer with incomplete plan
                            if not assistant_text.strip() and self._has_incomplete_tasks():
                                incomplete = self._get_incomplete_tasks()
                                next_task = incomplete[0]

                                self.printer.iteration_complete(i, "empty_answer_retry")

                                self.agent.messages.append({
                                    "role": "assistant",
                                    "content": "I need to continue working on the remaining tasks."
                                })
                                self.agent.messages.append({
                                    "role": "user",
                                    "content": (
                                        f"You returned an empty response but {len(incomplete)} "
                                        f"plan task(s) remain incomplete. Continue with task "
                                        f"{next_task.id}: {next_task.description}"
                                    ),
                                })

                                callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)
                                continue

                            self.agent.messages.append({
                                "role": "assistant",
                                "content": assistant_text
                            })

                            iteration_span.update(output={
                                "action": "answer_ready",
                                "answer": assistant_text,
                                "usage": iteration_usage,
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
                                "cache_creation_input_tokens": self.agent.cache_creation_input_tokens,
                                "cache_read_input_tokens": self.agent.cache_read_input_tokens,
                            })

                            return {
                                "answer": assistant_text,
                                "tool_calls": tool_calls_made,
                                "total_tokens": self.agent.total_tokens,
                                "cache_creation_input_tokens": self.agent.cache_creation_input_tokens,
                                "cache_read_input_tokens": self.agent.cache_read_input_tokens,
                                "iterations": i,
                                "stop_reason": "answer_ready"
                            }

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
                    "cache_creation_input_tokens": self.agent.cache_creation_input_tokens,
                    "cache_read_input_tokens": self.agent.cache_read_input_tokens,
                })

                return {
                    "answer": final_answer,
                    "tool_calls": tool_calls_made,
                    "total_tokens": self.agent.total_tokens,
                    "cache_creation_input_tokens": self.agent.cache_creation_input_tokens,
                    "cache_read_input_tokens": self.agent.cache_read_input_tokens,
                    "iterations": self.agent.max_iterations,
                    "stop_reason": "max_iterations"
                }

            except Exception as e:
                callback.on_run_error(error=str(e))
                raise

    def call_llm(self) -> NormalizedLLMResponse:
        """Make LLM API call."""

        return self.agent.backend.call_llm(
            messages=self.agent.messages,
            tools=self.agent.tools if self.agent.tools else None,
            temperature=self.agent.temperature,
        )

    def _track_token_usage(self, response: NormalizedLLMResponse) -> int:
        iteration_tokens = int(response.usage.total_tokens)
        self.agent.total_tokens += iteration_tokens
        self.agent.cache_creation_input_tokens += int(response.usage.cache_creation_input_tokens)
        self.agent.cache_read_input_tokens += int(response.usage.cache_read_input_tokens)
        return iteration_tokens

    @staticmethod
    def _build_iteration_usage(response: NormalizedLLMResponse) -> Dict[str, int]:
        return {
            "input_tokens": int(response.usage.input_tokens),
            "output_tokens": int(response.usage.output_tokens),
            "total_tokens": int(response.usage.total_tokens),
            "cache_creation_input_tokens": int(response.usage.cache_creation_input_tokens),
            "cache_read_input_tokens": int(response.usage.cache_read_input_tokens),
        }

    def _build_iteration_input(self, iteration: int) -> Dict[str, Any]:
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

    # ================================
    # --> Helper funcs
    # ================================

    def _has_incomplete_tasks(self) -> bool:
        """Check if the agent has a plan with incomplete tasks."""
        plan = getattr(self.agent, "plan", None)

        if not plan or not plan.tasks:
            return False

        return any(t.status != TaskStatus.COMPLETE for t in plan.tasks)

    def _get_incomplete_tasks(self) -> list:
        """Return incomplete tasks from the agent's plan, ordered by step then id."""
        plan = getattr(self.agent, "plan", None)

        if not plan or not plan.tasks:
            return []

        return [t for t in plan.tasks if t.status != TaskStatus.COMPLETE]

    @staticmethod
    def _sanitize_tool_calls(tool_calls: list[NormalizedToolCall]) -> None:
        for tc in tool_calls:
            try:
                json.loads(tc.arguments_json or "{}")
            except (json.JSONDecodeError, TypeError):
                tc.arguments_json = "{}"

    def _handle_tool_calls(self, tool_calls: list[NormalizedToolCall], assistant_text: str) -> List[str]:
        self._sanitize_tool_calls(tool_calls)

        self.agent.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "tool_calls": tool_calls
        })

        if should_run_parallel(tool_calls):
            self.agent.tool_handler.handle_tool_calls_parallel(tool_calls)
        else:
            self.agent.tool_handler.handle_tool_calls(tool_calls)

        return [tc.name for tc in tool_calls]
