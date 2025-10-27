"""Execution Loop - Phase 1

Simple ReAct iteration loop.
"""

from typing import Dict, Any, TYPE_CHECKING
import json
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode
from app.core.agentic_framework.base_agent_v2.planning.plan_prompt import plan_prompt
from app.core.agentic_framework.base_agent_v2.planning.plan_parser import parse_plan_with_gpt
from app.core.agentic_framework.base_agent_v2.utils.models import *
from app.core.agentic_framework.base_agent_v2.execution.utils import (
    is_final,
    extract_final_answer,
    build_plan_context,
    write_messages_to_file
)

if TYPE_CHECKING:
    from ..agent import SimpleAgent


class ExecutionLoop:
    """Manages the main ReAct iteration loop.

    Responsibilities:
    - Run iteration loop (1 to max_iterations)
    - Call LLM API each iteration
    - Delegate tool execution to ToolHandler
    - Detect finality
    - Track tokens
    """

    def __init__(self, agent: 'SimpleAgent'):
        """Initialize with agent reference.

        Args:
            agent: Parent SimpleAgent instance
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
            print(f"\n--- Iteration {i} ---")

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
                    print(f"🗑️  Removed planning prompt from message history (planning phase complete)")

                plan_context = build_plan_context(self.agent)
                print(f"📊 Injecting plan status into context...")
                self.agent.messages.append({
                    "role": "system",
                    "content": plan_context
                })

                if self.agent.print_mode == PrintMode.DEBUG or self.agent.print_mode == PrintMode.VERBOSE:
                    print(f"Plan context: {plan_context}")

            try:
                # Call LLM
                response = self.agent.client.chat.completions.create(
                    model=self.agent.model,
                    messages=self.agent.messages,
                    tools=self.agent.tools if self.agent.tools else None,
                    tool_choice="auto",
                    **({"reasoning_effort": self.agent.reasoning_effort} if getattr(self.agent, "reasoning_effort", None) is not None else {}),
                    **({"temperature": self.agent.temperature} if getattr(self.agent, "temperature", None) is not None else {})
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
                    print(f"Usage: {response.usage.total_tokens}")
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

                        # if self.agent.print_mode == PrintMode.DEBUG or self.agent.print_mode == PrintMode.VERBOSE:
                        #     print(f"   Plan details: {plan.model_dump_json(indent=2)}")

                        # Add assistant response to history
                        self.agent.messages.append({
                            "role": "assistant",
                            "content": assistant_text
                        })

                        print(f"📋 Plan created. Moving to execution phase...")

                        continue

                if assistant_text:
                    print(f"Assistant: {assistant_text}")

                # Handle tool calls
                if assistant_message.tool_calls: #if tool calls are in the assistant message, we need to execute the underlying function and return the output
                    self.agent.tool_handler.handle_tool_calls(assistant_message.tool_calls)
                
                # Check for finality
                elif is_final(assistant_text):
                    final_answer = extract_final_answer(assistant_text)
                    stop_reason = "final_answer"
                    break

                # LLM returned text without tools or finality
                else:
                    self.agent.messages.append({
                        "role": "assistant",
                        "content": assistant_text
                    })

            except Exception as e:
                if self.agent.print_mode == PrintMode.DEBUG:
                    print(f"⚠️ Error in iteration {i}: {e}")
                continue

        # Write complete message history to file
        write_messages_to_file(self.agent)

        return {
            "final_answer": final_answer or "No final answer reached",
            "iterations": i if 'i' in locals() else 0,
            "total_tokens": self.agent.total_tokens,
            "stop_reason": stop_reason
        }
