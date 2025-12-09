"""Execution Loop - Phase 1

Simple ReAct iteration loop.
"""

from typing import Dict, Any, TYPE_CHECKING
import json
from app.core.agentic_framework.base_agent.utils.models import PrintMode
from app.core.agentic_framework.base_agent.planning.plan_prompt import plan_prompt
from app.core.agentic_framework.base_agent.planning.plan_parser import parse_plan_with_gpt
from app.core.agentic_framework.base_agent.utils.models import *
from app.core.agentic_framework.base_agent.execution.utils import (
    extract_final_answer,
    build_plan_context
)
from app.core.agentic_framework.base_agent.utils.messages.message_utils import remove_system_messages
from app.core.agentic_framework.base_agent.utils.messages.execution_loop_msg import (
    THINK_DEEPLY_MESSAGE,
    get_finalize_rejected_message
)
from app.core.agentic_framework.base_agent.execution.tool_handler_async import (
    should_run_parallel,
    execute_tools_parallel
)
from app.core.agentic_framework.base_agent.logging.message_logger import write_messages_to_yaml
from app.core.agentic_framework.tool_lib.base_tools.edit_plan import edit_plan
from app.core.agentic_framework.base_agent.planning.plan_progress import get_plan_progress
import traceback

if TYPE_CHECKING:
    from ..agent import BaseAgent


class ExecutionLoop:
    """Manages the main ReAct iteration loop.

    Responsibilities:
    - Run iteration loop (1 to max_iterations)
    - Call LLM API each iteration
    - Delegate tool execution to ToolHandler
    - Detect finality
    - Track tokens
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize with agent reference.

        Args:
            agent: Parent BaseAgent instance
        """
        self.agent = agent

    def execute(self) -> Dict[str, Any]:
        """Execute main ReAct loop.

        Returns:
            Dictionary with final_answer, iterations, total_tokens, stop_reason
        """
        final_answer = None
        stop_reason = "max_iterations"

        # Main loop
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
            # If we dont remove the planning prompt, the agent will keep planning and executing the same tasks over and over again
            if i > 1 and self.agent.plan and self.agent.plan.tasks:
                messages_before = len(self.agent.messages)
                self.agent.messages = [msg for msg in self.agent.messages if not (msg.get("role") == "system" and "🚨 CRITICAL INSTRUCTION" in msg.get("content", ""))]
                messages_after = len(self.agent.messages)

                if messages_before != messages_after:
                    if self.agent.print_mode in [PrintMode.VERBOSE, PrintMode.DEBUG]:
                        print(f"🗑️  Removed planning prompt from message history (planning phase complete)")

                # First execution iteration (i==2) gets detailed workflow, later iterations get reminders
                is_first_execution = (i == 2)
                plan_context = build_plan_context(self.agent, is_first_execution=is_first_execution)

                # Find existing plan status message and update it, or append if not found
                plan_status_updated = False
                for msg in self.agent.messages:
                    if msg.get("role") == "system" and "## Current Plan Status" in msg.get("content", ""):
                        # Update existing plan status message
                        msg["content"] = plan_context
                        plan_status_updated = True
                        break

                # If no existing plan status found, append new one (first time only)
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
                patterns=["AVAILABLE NOTES IN NOTEBOOK", "## THINK DEEPLY THIS ITERATION"]
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

            # Inject per-turn THINK reminder
            self.agent.messages.append({
                "role": "system",
                "content": THINK_DEEPLY_MESSAGE
            })

            # Record message index for iteration banner (after all system message injection)
            self.agent._iteration_message_indices[i] = len(self.agent.messages) - 1

            try:
                # NOTE: This code block is what calls the LLM and gets the response (this is the main LLM call and the engine of the agent)
                #TODO: Have this output a specific format to a pydantic dataclass for the response every time and it should always have a reasoning field 
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

                # Track tokens
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

                        # Invoke callback for plan streaming
                        # This is new for the purposes of showing the agent stream on the frontend
                        if hasattr(self.agent, "state_callback") and self.agent.state_callback is not None:
                            self.agent.state_callback.on_plan_created(plan)

                        continue

                if assistant_text:
                    print(f"Assistant: {assistant_text}")

                # Handle tool calls
                if assistant_message.tool_calls: #if tool calls are in the assistant message, we need to execute the underlying function and return the output

                    tool_calls = assistant_message.tool_calls # --> create the tool calls variable out of assistant_message.tool calls just for simplicity sake

                    # Preserve the model's visible reasoning even when it choses to use tools
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text,
                        "tool_calls": tool_calls
                    })

                    # NOTE: This conditional statement says if there are multiple tool calls returned for this iteration from the LLM, run the tools in parallel (using async) else run the regular sequential tool calls
                    # NOTE: This is where the tool calls are handled and called 
                    # NOTE: This code resides in tool_handler.py and tool_handler_async.py
                    if should_run_parallel(tool_calls):
                        execute_tools_parallel(self.agent.tool_handler, tool_calls, len(self.agent.messages) - 1)
                    else:
                        self.agent.tool_handler.handle_tool_calls(tool_calls)

                    # Detect finalize tool and terminate with provided answer
                    # This looks for the function name "finalize" in the tool calls
                    try:
                        for tc in tool_calls:
                            name = getattr(tc.function, "name", "")

                            # Only check plan progress when finalize is called
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

                # LLM returned text without tools
                else:
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

            except Exception as e:
                # Always print errors (not just in DEBUG mode)
                print(f"⚠️ Error in iteration {i}: {e}") # NOTE: This is the error that is printed to the console
                traceback.print_exc()
                continue

        return {
            "final_answer": final_answer or "No final answer reached",
            "iterations": i if 'i' in locals() else 0,
            "total_tokens": self.agent.total_tokens,
            "stop_reason": stop_reason
        }
