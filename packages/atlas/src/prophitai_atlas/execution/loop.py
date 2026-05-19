"""ChatAgent execution loop - fast ReAct loop for interactive chat."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from openai import OpenAI

from prophitai_atlas.models.new_plan import TaskStatus
from prophitai_shared import Usage, refresh_rolling_cache_breakpoint

if TYPE_CHECKING:
    from prophitai_atlas.agents.base import AgentBase
    from prophitai_atlas.observability import LangfuseObserver


# ================================
# --> Streamed response shape
# ================================


@dataclass
class StreamedResponse:
    """One LLM turn's output, assembled from a streamed chat completion.

    `tool_calls` is the OpenAI wire shape — list of dicts with id/type/function.
    """

    content: str
    tool_calls: List[Dict[str, Any]]
    usage: Usage


# ================================
# --> Helper funcs
# ================================


def _format_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Wrap canonical tool definitions in the OpenAI function-calling envelope."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["parameters"],
            },
        }
        for t in tools
    ]


def _extract_reasoning(obj: Any) -> str:
    """Pull reasoning text from any of the provider shapes OpenRouter forwards."""
    text = getattr(obj, "reasoning_content", None) or getattr(obj, "reason", None)

    if text:
        return text

    details = getattr(obj, "reasoning_details", None) or []
    parts: List[str] = []

    for d in details:
        t = d.get("text") if isinstance(d, dict) else getattr(d, "text", None)

        if t:
            parts.append(t)

    return "".join(parts)


# ================================
# --> Streaming call
# ================================


def call_llm_streaming(
    *,
    client: OpenAI,
    model: str,
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]],
    temperature: Optional[float],
    callback: Any,
    message_id: Optional[str],
) -> StreamedResponse:
    """Stream a chat completion and assemble (content, tool_calls, usage).

    The rolling cache breakpoint is refreshed before each call so the latest
    assistant/tool message carries the marker. Tool calls arrive fragmented
    across chunks — they are reassembled into index-keyed slots.
    """
    refresh_rolling_cache_breakpoint(messages)

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=_format_tools(tools) if tools else None,
        tool_choice="auto" if tools else None,
        temperature=temperature,
        stream=True,
        # Final chunk arrives with empty choices and populated usage.
        stream_options={"include_usage": True},
    )

    content_pieces: List[str] = []
    tool_call_slots: Dict[int, Dict[str, Any]] = {}
    usage: Optional[Usage] = None

    for chunk in response:
        if getattr(chunk, "usage", None):
            usage = Usage.from_response(chunk.usage)

        if not chunk.choices:
            continue

        delta = chunk.choices[0].delta

        reasoning = _extract_reasoning(delta)

        if reasoning and callback is not None:
            # Reason: surface reasoning live but do not append to history.
            on_reasoning = getattr(callback, "on_reasoning_delta", None)

            if on_reasoning is not None:
                on_reasoning(message_id or "", reasoning)

        if delta.content:
            content_pieces.append(delta.content)

            if callback is not None:
                callback.on_text_delta(message_id or "", delta.content)

        if delta.tool_calls:
            for tc in delta.tool_calls:
                slot = tool_call_slots.setdefault(
                    tc.index,
                    {
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    },
                )

                if tc.id:
                    slot["id"] = tc.id

                if tc.function:
                    if tc.function.name:
                        slot["function"]["name"] = tc.function.name

                    if tc.function.arguments:
                        slot["function"]["arguments"] += tc.function.arguments

    content = "".join(content_pieces)
    tool_calls = [tool_call_slots[i] for i in sorted(tool_call_slots)]

    return StreamedResponse(content=content, tool_calls=tool_calls, usage=usage or Usage.zero())


# ================================
# --> Loop
# ================================


class ExecutionLoop:
    """Fast execution loop for chat - no planning, terminates on text-only response."""

    def __init__(self, agent: "AgentBase", *, observer: "LangfuseObserver"):
        self.agent = agent
        self.printer = agent.printer
        self.observer = observer

    def execute(self, message_id: Optional[str] = None) -> Dict[str, Any]:
        """Run ReAct loop until answer ready or max iterations.

        Args:
            message_id: Optional unique identifier for this message. Generated if not provided.

        Returns:
            Dict with answer, tool_calls, total_tokens, cache token stats, iterations, and stop_reason.
        """
        with self.observer.execution_loop(
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

            callback.on_run_started(
                session_id=self.agent.session_id,
                message_id=message_id,
            )

            tool_names = self.agent.get_tool_names()
            print(f"Registered tools ({len(tool_names)}): {sorted(tool_names)}")

            try:
                for i in range(1, self.agent.max_iterations + 1):
                    with self.observer.iteration(
                        number=i,
                        input=self._build_iteration_input(i),
                    ) as iteration_span:

                        callback.on_iteration_start(iteration=i)
                        self.printer.iteration_start(i, self.agent.max_iterations)

                        response = self.call_llm(callback=callback, message_id=message_id)

                        iteration_tokens = self._track_token_usage(response)
                        iteration_usage = self._build_iteration_usage(response)

                        assistant_text = response.content

                        if response.tool_calls:
                            called_tools = self.agent.tool_handler.dispatch(
                                response.tool_calls,
                                assistant_text,
                                iteration=i,
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
                                "content": assistant_text,
                            })

                            iteration_span.update(output={
                                "action": "answer_ready",
                                "answer": assistant_text,
                                "usage": iteration_usage,
                            })

                            callback.on_iteration_end(iteration=i, tokens_used=iteration_tokens)

                            self.printer.iteration_complete(i, "answer_ready")

                            return self._finalize(
                                stop_reason="answer_ready",
                                answer=assistant_text,
                                iterations=i,
                                tool_calls_made=tool_calls_made,
                                loop_span=loop_span,
                            )

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

                return self._finalize(
                    stop_reason="max_iterations",
                    answer=final_answer,
                    iterations=self.agent.max_iterations,
                    tool_calls_made=tool_calls_made,
                    loop_span=loop_span,
                )

            except Exception as e:
                callback.on_run_error(error=str(e))
                raise

    def call_llm(
        self,
        *,
        callback: Any = None,
        message_id: Optional[str] = None,
    ) -> StreamedResponse:
        """Stream one chat completion and return (content, tool_calls, usage)."""
        return call_llm_streaming(
            client=self.agent.client,
            model=self.agent.model,
            messages=self.agent.messages,
            tools=self.agent.tools if self.agent.tools else None,
            temperature=self.agent.temperature,
            callback=callback,
            message_id=message_id,
        )

    def _track_token_usage(self, response: StreamedResponse) -> int:
        iteration_tokens = int(response.usage.total_tokens)

        self.agent.total_tokens += iteration_tokens
        self.agent.cache_write_tokens += int(response.usage.cache_write_tokens)
        self.agent.cached_tokens += int(response.usage.cached_tokens)

        return iteration_tokens

    @staticmethod
    def _build_iteration_usage(response: StreamedResponse) -> Dict[str, int]:
        return {
            "prompt_tokens": int(response.usage.prompt_tokens),
            "completion_tokens": int(response.usage.completion_tokens),
            "total_tokens": int(response.usage.total_tokens),
            "cache_write_tokens": int(response.usage.cache_write_tokens),
            "cached_tokens": int(response.usage.cached_tokens),
        }

    def _build_iteration_input(self, iteration: int) -> Dict[str, Any]:
        messages = self.agent.messages

        if not messages:
            return {"iteration": iteration, "message_count": 0}

        last_msg = messages[-1]
        last_role = last_msg.get("role", "unknown")
        last_content = last_msg.get("content", "") or ""

        if isinstance(last_content, list):
            last_content = "".join(
                part.get("text", "") for part in last_content if isinstance(part, dict)
            )

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
        plan = getattr(self.agent, "plan", None)

        if not plan or not plan.tasks:
            return False

        return any(t.status != TaskStatus.COMPLETE for t in plan.tasks)

    def _get_incomplete_tasks(self) -> list:
        plan = getattr(self.agent, "plan", None)

        if not plan or not plan.tasks:
            return []

        return [t for t in plan.tasks if t.status != TaskStatus.COMPLETE]

    def _finalize(
        self,
        *,
        stop_reason: str,
        answer: str,
        iterations: int,
        tool_calls_made: List[str],
        loop_span: Any,
    ) -> Dict[str, Any]:
        """Emit terminal callbacks/spans and build the loop's return payload."""
        self.agent.chat_callback.on_run_finished(
            answer=answer,
            tool_calls_made=tool_calls_made,
            iterations=iterations,
            tokens_used=self.agent.total_tokens,
            stop_reason=stop_reason,
        )

        loop_span.update(output={
            "stop_reason": stop_reason,
            "iterations": iterations,
            "total_tokens": self.agent.total_tokens,
            "cache_write_tokens": self.agent.cache_write_tokens,
            "cached_tokens": self.agent.cached_tokens,
        })

        return {
            "answer": answer,
            "tool_calls": tool_calls_made,
            "total_tokens": self.agent.total_tokens,
            "cache_write_tokens": self.agent.cache_write_tokens,
            "cached_tokens": self.agent.cached_tokens,
            "iterations": iterations,
            "stop_reason": stop_reason,
        }
