"""DeepAgent execution loop - full ReAct loop with planning capabilities."""

from typing import Dict, Any, TYPE_CHECKING
import json
import traceback

from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.planning.plan_prompt import plan_prompt
from app.core.agentic_framework.base_agent.planning.plan_parser import parse_plan_with_gpt
from app.core.atlas.execution.utils import (
    extract_final_answer,
    build_plan_context
)
from app.core.agentic_framework.base_agent.utils.messages.message_utils import remove_system_messages
from app.core.agentic_framework.base_agent.utils.messages.execution_loop_msg import (
    THINK_DEEPLY_MESSAGE,
    get_finalize_rejected_message
)
from app.core.agentic_framework.base_agent.execution.tool_handler_parallel import (
    should_run_parallel,
    execute_tools_parallel
)
from app.core.agentic_framework.base_agent.planning.plan_progress import get_plan_progress

if TYPE_CHECKING:
    from app.core.atlas.agents.deep_agent import DeepAgent


class DeepExecutionLoop:
    """Full-featured execution loop with planning, notes, and finalize detection."""

    def __init__(self, agent: 'DeepAgent'):
        self.agent = agent

    def execute(self) -> Dict[str, Any]:
        """Execute main ReAct loop with planning support."""
        final_answer = None
        stop_reason = "max_iterations"

        for i in range(1, self.agent.max_iterations + 1):
            if self.agent.print_mode == PrintMode.PRODUCTION:
                print(f"\n[{i}]", end=" ", flush=True)
            else:
                print(f"\n--- Iteration {i} ---")

            # Track current iteration for logging purposes
            self.agent.current_iteration = i
            if not hasattr(self.agent, '_iteration_message_indices'):
                self.agent._iteration_message_indices = {}

            # Planning phase: inject planning prompt (iteration 1 only)
            if i == 1 and self.agent.plan_first:
                self.agent.messages.append({
                    "role": "system",
                    "content": plan_prompt
                })

            # Execution phase: inject plan status and remove old planning prompt (iteration 2+)
            if i > 1 and self.agent.plan and self.agent.plan.tasks:
                messages_before = len(self.agent.messages)
                self.agent.messages = [msg for msg in self.agent.messages if not (msg.get("role") == "system" and "🚨 CRITICAL INSTRUCTION" in msg.get("content", ""))]
                messages_after = len(self.agent.messages)

                if messages_before != messages_after:
                    if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                        print(f"🗑️  Removed planning prompt from message history (planning phase complete)")

                is_first_execution = (i == 2)
                plan_context = build_plan_context(self.agent, is_first_execution=is_first_execution)

                plan_status_updated = False
                for msg in self.agent.messages:
                    if msg.get("role") == "system" and "## Current Plan Status" in msg.get("content", ""):
                        msg["content"] = plan_context
                        plan_status_updated = True
                        break

                if not plan_status_updated:
                    if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                        print(f"📊 Injecting plan status into context...")
                    self.agent.messages.append({
                        "role": "system",
                        "content": plan_context
                    })

            # Remove old system messages before re-injecting fresh versions
            self.agent.messages = remove_system_messages(
                self.agent.messages,
                patterns=[
                    "AVAILABLE NOTES IN NOTEBOOK",
                    "## THINK DEEPLY AND REFLECT THIS ITERATION"
                ]
            )

            # Inject available notes reminder if notes exist
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

            # Think deeply reminder every 5 iterations
            if self.agent.current_iteration % 5 == 0:
                self.agent.messages.append({
                    "role": "system",
                    "content": THINK_DEEPLY_MESSAGE
                })

            self.agent._iteration_message_indices[i] = len(self.agent.messages) - 1

            try:
                response = self.agent.client.chat.completions.create(
                    model=self.agent.model,
                    messages=self.agent.messages,
                    tools=self.agent.tools if self.agent.tools else None,
                    tool_choice="auto",
                    **({"reasoning_effort": self.agent.reasoning_effort} if getattr(self.agent, "reasoning_effort", None) is not None else {}),
                    **({"temperature": self.agent.temperature} if getattr(self.agent, "temperature", None) is not None else {}),
                )

                if self.agent.print_mode == PrintMode.DEBUG:
                    try:
                        print("\nLLM raw response JSON:")
                        print(response.model_dump_json(indent=2))
                    except Exception:
                        try:
                            print("\nLLM raw response dict:")
                            print(json.dumps(response.model_dump(), indent=2, default=str))
                        except Exception:
                            print(f"\nLLM raw response (repr): {response!r}")

                if hasattr(response, 'usage') and response.usage:
                    print(f"Token Usage: {response.usage.total_tokens}")
                    self.agent.total_tokens = int(response.usage.total_tokens)

                assistant_message = response.choices[0].message
                assistant_text = assistant_message.content or ""

                # Parse plan on first iteration if plan_first is enabled
                if i == 1 and self.agent.plan_first and assistant_text:
                    plan, error = parse_plan_with_gpt(assistant_text)

                    if error:
                        print(f"❌ Plan parsing failed: {error}")
                        self.agent.messages.append({
                            "role": "user",
                            "content": f"Your plan could not be parsed. Error: {error}. Please provide a valid plan."
                        })
                        continue
                    else:
                        self.agent.plan = plan
                        print(f"✅ Plan parsed successfully!")
                        print(f"   Tasks: {len(plan.tasks)}")

                        if hasattr(self.agent, "state_callback") and self.agent.state_callback is not None:
                            self.agent.state_callback.on_plan_created(plan)

                        continue

                if assistant_text:
                    print(f"Assistant: {assistant_text}")

                # Handle tool calls
                if assistant_message.tool_calls:
                    tool_calls = assistant_message.tool_calls

                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text,
                        "tool_calls": tool_calls
                    })

                    if should_run_parallel(tool_calls):
                        execute_tools_parallel(self.agent.tool_handler, tool_calls, len(self.agent.messages) - 1)
                    else:
                        self.agent.tool_handler.handle_tool_calls(tool_calls)

                    # Detect finalize tool
                    try:
                        for tc in tool_calls:
                            name = getattr(tc.function, "name", "")

                            if name in ("finalize", "final_answer", "final_answer_tool"):
                                progress, completion = get_plan_progress(self.agent.plan)

                                if completion:
                                    args = {}
                                    try:
                                        args = json.loads(getattr(tc.function, "arguments", "") or "{}")
                                    except Exception:
                                        args = {}

                                    final_answer = args.get("answer") or extract_final_answer(assistant_text or "")
                                    stop_reason = "finalize_tool"

                                    raise StopIteration
                                else:
                                    self.agent.messages.append({
                                        "role": "system",
                                        "content": get_finalize_rejected_message(progress)
                                    })

                    except StopIteration:
                        break

                else:
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

            except Exception as e:
                print(f"⚠️ Error in iteration {i}: {e}")
                traceback.print_exc()
                continue

        return {
            "final_answer": final_answer or "No final answer reached",
            "iterations": i if 'i' in locals() else 0,
            "total_tokens": self.agent.total_tokens,
            "stop_reason": stop_reason
        }
