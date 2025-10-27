"""Execution Loop - Phase 1

Simple ReAct iteration loop.
"""

from typing import Dict, Any, TYPE_CHECKING
import json
from pathlib import Path
from app.core.agentic_framework.base_agent_v2.utils.models import PrintMode
from app.core.agentic_framework.base_agent_v2.planning.plan_prompt import plan_prompt
from app.core.agentic_framework.base_agent_v2.planning.plan_parser import parse_plan_with_gpt

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

            if i == 1 and self.agent.plan_first:
                self.agent.messages.append({
                    "role": "system",
                    "content": plan_prompt
                })

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
                    if self.agent.print_mode == PrintMode.DEBUG:
                        print(f"Usage: {response.usage}")
                    self.agent.total_tokens = int(response.usage.total_tokens)

                assistant_message = response.choices[0].message
                assistant_text = assistant_message.content or ""

                # Parse plan on first iteration if plan_first is enabled
                if i == 1 and self.agent.plan_first and assistant_text:
                    plan, error = parse_plan_with_gpt(assistant_text)
                    print(f"Plan: {plan}")

                    if error:
                        print(f"❌ Plan parsing failed: {error}")
                        self.agent.messages.append({
                            "role": "user",
                            "content": f"Your plan could not be parsed. Error: {error}. Please provide a valid plan."
                        })
                        continue
                    else:
                        print(f" Plan parsed successfully!")
                        print(f"   Tasks: {len(plan.tasks)}")

                        if self.agent.print_mode == PrintMode.DEBUG:
                            print(f"   Plan: {plan.model_dump_json(indent=2)}")

                        # Add assistant response to history
                        self.agent.messages.append({
                            "role": "assistant",
                            "content": assistant_text
                        })

                        continue

                if assistant_text:
                    print(f"Assistant: {assistant_text}")

                # Handle tool calls
                if assistant_message.tool_calls: #if tool calls are in the assistant message, we need to execute the underlying function and return the output
                    self.agent.tool_handler.handle_tool_calls(assistant_message.tool_calls)
                
                # Check for finality
                elif self._is_final(assistant_text):
                    final_answer = self._extract_final_answer(assistant_text)
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
        self._write_messages_to_file()

        return {
            "final_answer": final_answer or "No final answer reached",
            "iterations": i if 'i' in locals() else 0,
            "total_tokens": self.agent.total_tokens,
            "stop_reason": stop_reason
        }

    def _is_final(self, text: str) -> bool:
        """Check if text contains finality marker.

        Args:
            text: Assistant response text

        Returns:
            True if text indicates final answer
        """
        if not text:
            return False
        text_lower = text.strip().lower()
        return text_lower.startswith("final answer:") or "final answer:" in text_lower

    def _extract_final_answer(self, text: str) -> str:
        """Extract final answer text after marker.

        Args:
            text: Full assistant response

        Returns:
            Text after "Final Answer:" marker
        """
        text = text.strip()
        lower_text = text.lower()
        final_idx = lower_text.find("final answer:")

        if final_idx >= 0:
            return text[final_idx + 13:].strip()

        return text

    def _write_messages_to_file(self) -> None:
        """Write complete message history to markdown file after execution."""
        try:
            # Get path to base_agent_v2 directory
            base_agent_v2_dir = Path(__file__).parent.parent
            output_file = base_agent_v2_dir / "l.md"

            # Build markdown content
            content = "# Agent Message History\n\n"
            content += f"Total Messages: {len(self.agent.messages)}\n\n"
            content += "---\n\n"

            for idx, message in enumerate(self.agent.messages, 1):
                role = message.get("role", "unknown")
                content += f"## Message {idx} - Role: {role}\n\n"

                # Handle content
                if message.get("content"):
                    content += f"**Content:**\n```\n{message['content']}\n```\n\n"

                # Handle tool calls
                if message.get("tool_calls"):
                    content += "**Tool Calls:**\n"
                    for tool_call in message["tool_calls"]:
                        tool_name = tool_call.function.name
                        tool_args = tool_call.function.arguments
                        content += f"- Tool: `{tool_name}`\n"
                        content += f"  - ID: `{tool_call.id}`\n"
                        content += f"  - Arguments:\n```json\n{tool_args}\n```\n\n"

                # Handle tool call ID (for tool response messages)
                if message.get("tool_call_id"):
                    content += f"**Tool Call ID:** `{message['tool_call_id']}`\n\n"

                content += "---\n\n"

            # Write to file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"\n📝 Message history written to: {output_file}")

        except Exception as e:
            print(f"\n⚠️ Failed to write message history: {e}")
