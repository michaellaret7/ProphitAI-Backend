"""DeepAgent execution loop - full ReAct loop with planning capabilities."""

import json
import traceback
from typing import Dict, Any, TYPE_CHECKING

from app.core.atlas.planning import plan_prompt, parse_plan_with_gpt, get_plan_progress
from app.core.atlas.execution.utils import extract_final_answer, build_plan_context
from app.core.atlas.prompts import (
    remove_system_messages,
    THINK_DEEPLY_MESSAGE,
    get_finalize_rejected_message
)
from app.core.atlas.execution.tool_handler import should_run_parallel

if TYPE_CHECKING:
    from app.core.atlas.agents.deep_agent import DeepAgent


class DeepExecutionLoop:
    """Full-featured execution loop with planning, notes, and finalize detection."""

    def __init__(self, agent: 'DeepAgent'):
        self.agent = agent
        self.printer = agent.printer

    def execute(self) -> Dict[str, Any]:
        """Execute main ReAct loop with planning support."""
        final_answer = None
        stop_reason = "max_iterations"

        for i in range(1, self.agent.max_iterations + 1):
            self.printer.iteration_start(i)
            self.agent.current_iteration = i

            if not hasattr(self.agent, '_iteration_message_indices'):
                self.agent._iteration_message_indices = {}

            # Planning phase (iteration 1 only)
            if i == 1 and self.agent.plan_first:
                self._inject_planning_prompt() # Maybe investigate if we can get rid of this functionality and run a quick planning subagent 

            # Execution phase (iteration 2+)
            if i > 1 and self.agent.plan and self.agent.plan.tasks:
                self._transition_to_execution(i)

            # Inject dynamic system messages
            self._inject_system_messages()
            self.agent._iteration_message_indices[i] = len(self.agent.messages) - 1

            try:
                response = self._call_llm()
                self._track_token_usage(response)
                self.printer.debug_response(response)

                assistant_message = response.choices[0].message
                assistant_text = assistant_message.content or ""

                # Parse plan on first iteration
                if i == 1 and self.agent.plan_first and assistant_text:
                    if self._handle_plan_parsing(assistant_text):
                        continue

                self.printer.assistant_response(assistant_text)

                # Handle tool calls or text response
                if assistant_message.tool_calls:
                    should_break = self._handle_tool_calls(
                        assistant_message.tool_calls,
                        assistant_text
                    )
                    if should_break:
                        final_answer, stop_reason = self._extract_final_answer(
                            assistant_message.tool_calls,
                            assistant_text
                        )
                        break
                else:
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

            except Exception as e:
                self.printer.error(f"Error in iteration {i}: {e}")
                traceback.print_exc()
                continue

        return {
            "final_answer": final_answer or "No final answer reached",
            "iterations": i if 'i' in locals() else 0,
            "total_tokens": self.agent.total_tokens,
            "stop_reason": stop_reason
        }

    def _inject_planning_prompt(self) -> None:
        """Inject planning prompt for iteration 1."""
        self.agent.messages.append({
            "role": "system",
            "content": plan_prompt
        })

    def _transition_to_execution(self, iteration: int) -> None:
        """Remove planning prompt and inject plan status."""
        # Remove planning prompt
        messages_before = len(self.agent.messages)
        self.agent.messages = [
            msg for msg in self.agent.messages
            if not (msg.get("role") == "system" and "🚨 CRITICAL INSTRUCTION" in msg.get("content", ""))
        ]

        if len(self.agent.messages) != messages_before:
            self.printer.planning_prompt_removed()

        # Inject or update plan status
        is_first_execution = (iteration == 2)
        plan_context = build_plan_context(self.agent, is_first_execution=is_first_execution)

        for msg in self.agent.messages:
            if msg.get("role") == "system" and "## Current Plan Status" in msg.get("content", ""):
                msg["content"] = plan_context
                return

        self.printer.plan_status_injected()
        self.agent.messages.append({"role": "system", "content": plan_context})

    def _inject_system_messages(self) -> None:
        """Inject notes reminder and think deeply prompt."""
        self.agent.messages = remove_system_messages(
            self.agent.messages,
            patterns=["AVAILABLE NOTES IN NOTEBOOK", "## THINK DEEPLY AND REFLECT THIS ITERATION"]
        )

        # Notes reminder
        if self.agent.note_titles:
            notes_list = "\n".join(f"  - {title}" for title in self.agent.note_titles)
            self.agent.messages.append({
                "role": "system",
                "content": (
                    f"📓 AVAILABLE NOTES IN NOTEBOOK (use retrieve_notes tool):\n"
                    f"{notes_list}\n\n"
                    f"Remember: Use retrieve_notes with the EXACT title to recall your previous analysis."
                )
            })

        # Think deeply every 5 iterations
        if self.agent.current_iteration % 5 == 0:
            self.agent.messages.append({
                "role": "system",
                "content": THINK_DEEPLY_MESSAGE
            })

    def _call_llm(self):
        """Make LLM API call."""
        kwargs = {}
        if getattr(self.agent, "reasoning_effort", None) is not None:
            kwargs["reasoning_effort"] = self.agent.reasoning_effort
        if getattr(self.agent, "temperature", None) is not None:
            kwargs["temperature"] = self.agent.temperature

        return self.agent.client.chat.completions.create(
            model=self.agent.model,
            messages=self.agent.messages,
            tools=self.agent.tools if self.agent.tools else None,
            tool_choice="auto",
            **kwargs
        )

    def _track_token_usage(self, response) -> None:
        """Track and print token usage."""
        if hasattr(response, 'usage') and response.usage:
            self.agent.total_tokens = int(response.usage.total_tokens)
            self.printer.token_usage(self.agent.total_tokens)

    def _handle_plan_parsing(self, assistant_text: str) -> bool:
        """Parse plan from assistant response. Returns True if should continue loop."""
        plan, error = parse_plan_with_gpt(assistant_text)

        if error:
            self.printer.plan_error(error)
            self.agent.messages.append({
                "role": "user",
                "content": f"Your plan could not be parsed. Error: {error}. Please provide a valid plan."
            })
            return True

        self.agent.plan = plan
        self.printer.plan_parsed(len(plan.tasks))

        if hasattr(self.agent, "state_callback") and self.agent.state_callback is not None:
            self.agent.state_callback.on_plan_created(plan)

        return True

    def _handle_tool_calls(self, tool_calls, assistant_text: str) -> bool:
        """Execute tool calls. Returns True if should break loop (finalize detected)."""
        self.agent.messages.append({
            "role": "assistant",
            "content": assistant_text,
            "tool_calls": tool_calls
        })

        if should_run_parallel(tool_calls):
            self.agent.tool_handler.handle_tool_calls_parallel(tool_calls)
        else:
            self.agent.tool_handler.handle_tool_calls(tool_calls)

        # Check for finalize tool
        for tc in tool_calls:
            name = getattr(tc.function, "name", "")
            if name in ("finalize", "final_answer", "final_answer_tool"):
                progress, completion = get_plan_progress(self.agent.plan)

                if completion:
                    return True

                self.agent.messages.append({
                    "role": "system",
                    "content": get_finalize_rejected_message(progress)
                })

        return False

    def _extract_final_answer(self, tool_calls, assistant_text: str) -> tuple[str, str]:
        """Extract final answer from finalize tool call."""
        for tc in tool_calls:
            name = getattr(tc.function, "name", "")
            if name in ("finalize", "final_answer", "final_answer_tool"):
                try:
                    args = json.loads(getattr(tc.function, "arguments", "") or "{}")
                except Exception:
                    args = {}

                answer = args.get("answer") or extract_final_answer(assistant_text or "")
                return answer, "finalize_tool"

        return "No final answer reached", "max_iterations"
