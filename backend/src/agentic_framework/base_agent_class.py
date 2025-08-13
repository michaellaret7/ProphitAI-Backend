import json
import os
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# Domain tools
from backend.src.agentic_framework.base_tools.calculator import calculator
from backend.src.agentic_framework.base_tools.data_wrapper_tool import ProphitAltsDataWrapper
from backend.src.agentic_framework.base_tools.search_engine_tool import AgentSearchEngine
from backend.src.utils.choose_model_and_client import openai_model_and_client
from backend.src.utils.choose_model_and_client import *

load_dotenv()

@dataclass
class StepTrace:
    iteration: int
    assistant_raw: str = ""
    tool_call: Optional[Dict[str, Any]] = None
    observation: Optional[Any] = None
    analysis: Optional[str] = None

class BaseAgent:
    """
    Refactored BaseAgent with:
      (a) Native tool-calls + JSON ReAct
      (b) No eval() anywhere (safe JSON parsing only)
      (c) Loop/stop/summary management
      (d) Returns a clean structured trace
    """

    def __init__(self, system_prompt: str, user_prompt: str, *, model: str = "gpt-5", max_iterations: int = 50, verbose: bool = True, plan_first: bool = True, final_keywords: Optional[List[str]] = None, save_messages: bool = True):
        self.model_name = model
        self.llm, self.client = openai_model_and_client(model=self.model_name)

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.plan_first = True  # always plan first
        self.final_keywords = final_keywords or ["Final Answer:", "FINAL ANSWER:"]
        self.save_messages = save_messages

        # OpenAI tools and local dispatch map
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable[..., Any]] = {}

        # Register built-ins
        self._register_base_tools()

        # Trace and accounting
        self.trace: List[StepTrace] = []
        self.total_tokens: int = 0

        # Stagnation detection
        self._recent_actions: List[str] = []  # serialized (tool_name + sorted args)
        self._stuck_count: int = 0
        self._stuck_threshold: int = 4  # Increased to allow more iterations for portfolio testing
        
        # Message logging
        if self.save_messages:
            self.messages_log_path = Path(__file__).parent / "agent_output" / "agent_messages.json"
            # Clear the messages file at start
            try:
                with open(self.messages_log_path, "w", encoding="utf-8") as f:
                    json.dump({}, f)
            except Exception:
                pass
        
        # Checklist tracking
        self.checklist_path = Path(__file__).parent / "agent_output" / "agent_checklist.json"
        self.checklist_items: List[Dict[str, Any]] = []
        self.checklist_enabled = False  # Will be enabled when plan is detected
        # Clear the checklist file at start
        try:
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception:
            pass

    # --- Tool registry -----------------------------------------------------
    def _register_base_tools(self):
        ticker_data_description = (
            "The get_ticker_data tool returns a comprehensive dictionary of financial "
            "data for a given stock ticker, including performance metrics, style factors, "
            "fundamental data, recent news, earnings transcript summaries, and grades."
        )
        search_description = (
            "The free_search tool searches the web. Provide a detailed query that will be "
            "sent to an external search engine."
        )

        # get_ticker_data
        self.add_tool(
            name="get_ticker_data",
            description=ticker_data_description,
            parameters={
                "type": "object",
                "properties": {
                    "ticker": {"type": "string", "description": "Stock ticker symbol."},
                },
                "required": ["ticker"],
            },
            function=lambda ticker: ProphitAltsDataWrapper(ticker).run_all(),
        )

        # free_search
        self.add_tool(
            name="free_search",
            description=search_description,
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Detailed query for the search engine.",
                    }
                },
                "required": ["query"],
            },
            function=lambda query: AgentSearchEngine().perplexity_free_search(query),
        )

        # calculator
        self.add_tool(
            name="calculator",
            description=(
                "Perform mathematical calculations. Provide the expression string and the tool returns the result."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Expression to evaluate."}
                },
                "required": ["expression"],
            },
            function=lambda expression: calculator(expression),
        )

    def add_tool(self, name: str, description: str, parameters: Dict, function: Callable):
        tool_def = {
            "type": "function",
            "function": {"name": name, "description": description, "parameters": parameters},
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function

    # --- Core run loop -----------------------------------------------------
    def run(self) -> Dict[str, Any]:
        if self.verbose:
            print("🚀 Starting JSON ReAct run")
            print(f"Query: {self.user_prompt}")
            print("=" * 60)
            if self.save_messages:
                print(f"📝 Saving messages to: {self.messages_log_path}")

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._system_rules()},
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]
        
        # Save initial messages
        self._save_messages_to_json(messages, iteration=0)

        if self.plan_first:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Before you start, produce a short JSON plan: {\"plan\":[{\"step\":1,\"desc\":\"...\"},...]}\n"
                        "After you produce the short json plan, you must come up with an actionable to-do list which must be numbered in the following format: \n\n"
                        "1. [actionable item 1]\n"
                            "a. [actionable item 1a]\n"
                            "b. [actionable item 1b]\n"
                            "and so on..."
                        "2. [actionable item 2]\n"
                            "a. [actionable item 2a]\n"
                            "b. [actionable item 2b]\n"
                            "and so on..."
                        "and so on..."
                        "Then begin executing with tool-calls."
                    ),
                }
            )

        final_text: Optional[str] = None
        stop_reason: str = ""

        for i in range(1, self.max_iterations + 1):
            if self.verbose:
                print(f"\n⚜️  Iteration {i}")

            response = self.client.chat.completions.create(
                model=self.llm,
                messages=messages,
                tools=self.tools if self.tools else None,
                tool_choice="auto" if self.tools else None,            
            )

            choice = response.choices[0]
            msg = choice.message
            self._accumulate_usage(response)

            # Record assistant content (may be None when tool_calls are used)
            assistant_raw = msg.content or ""

            if self.verbose:
                print("  assistant_raw:", assistant_raw)

            step = StepTrace(iteration=i, assistant_raw=assistant_raw)
            
            # Try to parse plan from first response if plan_first is enabled
            if i == 1 and self.plan_first and assistant_raw:
                self._parse_plan_to_checklist(assistant_raw)

            if msg.tool_calls:
                # Append the assistant message that contains all tool calls
                messages.append({
                    "role": "assistant",
                    "content": assistant_raw if assistant_raw else "",
                    "tool_calls": msg.tool_calls,
                })
                # Execute tool-calls sequentially (usually one at a time)
                for tc in msg.tool_calls:
                    name = tc.function.name
                    args_json = tc.function.arguments or "{}"

                    try:
                        args = json.loads(args_json)
                        print(tc.function.name)
                    except json.JSONDecodeError:
                        # If arguments are not valid JSON, pass raw string under a key
                        args = {"_raw": args_json}

                    step.tool_call = {"name": name, "args": args}

                    # Stagnation detection to detect if the agent is stuck in a loop
                    self._update_stagnation(name, args)

                    observation = self._execute_tool_safe(name, args)
                    step.observation = observation

                    if self.verbose:
                        print(f"  tool_call -> {name} args={json.dumps(args, sort_keys=True)}")
                        print("  observation:", self._stringify(observation))

                    # tie tool result back to the tool_call_id
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": self._stringify(observation),
                    })

                # Update checklist progress and ask the model to analyze the observation
                self._update_checklist_progress(i)
                
                # Ask the model to analyze the observation and decide next step or finalize the answer
                messages.append(
                    {
                        "role": "user",
                        "content": self._get_checklist_prompt(i),
                    }
                )

            else:
                # No tool call. Check for finality
                if self._looks_final(assistant_raw):
                    final_text = assistant_raw
                    stop_reason = "final_message"
                    self.trace.append(step)
                    break

                # If it's JSON step format, allow model to request tools via content
                content_tool = self._maybe_parse_json_step(assistant_raw)
                if content_tool:
                    name = content_tool["tool"]
                    args = content_tool.get("args", {})
                    step.tool_call = {"name": name, "args": args}
                    self._update_stagnation(name, args)
                    observation = self._execute_tool_safe(name, args)
                    step.observation = observation

                    if self.verbose:
                        print(f"  tool_call(content) -> {name} args={json.dumps(args, sort_keys=True)}")
                        print("  observation:", self._stringify(observation))

                    messages.append({"role": "assistant", "content": assistant_raw})
                    # For content-based tool calls, we can't use "tool" role - use "user" instead
                    messages.append({"role": "user", "content": f"Tool '{name}' returned: {self._stringify(observation)}"})

                    # Update checklist progress
                    self._update_checklist_progress(i)
                    
                    messages.append(
                        {
                            "role": "user",
                            "content": self._get_checklist_prompt(i),
                        }
                    )
                else:
                    # Ask the model to either pick a tool or finalize
                    messages.append({"role": "assistant", "content": assistant_raw})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You provided no tool-call. If additional information is required, call a tool now. "
                                "Otherwise produce a 'Final Answer:' and stop."
                            ),
                        }
                    )

            self.trace.append(step)
            
            # Save messages after each iteration
            self._save_messages_to_json(messages, iteration=i)

            if self.verbose:
                print("" + "-"*80)

            # Stagnation guard – request a different approach
            if self._stuck_count >= self._stuck_threshold:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "You are repeating the same action with similar arguments and no new information. "
                            "Propose a different approach or finalize with a 'Final Answer:'."
                        ),
                    }
                )
                self._stuck_count = 0  # reset after nudging

        else:
            stop_reason = "max_iterations"

        # If no explicit final_text was emitted, try to extract the last assistant content
        if final_text is None:
            final_text = self._extract_last_final(messages) or "Reached maximum iterations without a final answer."

        if self.verbose and final_text:
            print("✅ Final Answer:", final_text)

        return {
            "final_text": final_text,
            "iterations": len(self.trace),
            "stopped_reason": stop_reason,
            "total_tokens": self.total_tokens,
            "trace": [self._trace_to_dict(s) for s in self.trace],
        }
        
        # Final save with complete trace
        if self.save_messages:
            self._save_final_json(messages, result)
        
        return result

    # --- Helpers -----------------------------------------------------------
    def _system_rules(self) -> str:
        return (
            "You are a JSON ReAct agent. Prefer native tool-calls. When you can finalize, "
            "output a concise answer beginning with 'Final Answer:'. If you must emit a JSON step, use:\n"
            '{"thought":"...","action":{"tool":"name","args":{}}}\n'
            'IMPORTANT: Use exact tool names without any prefix (e.g., "get_ticker_data" not "functions.get_ticker_data")'
        )

    def _accumulate_usage(self, response) -> None:
        try:
            if hasattr(response, "usage") and response.usage and response.usage.total_tokens:
                self.total_tokens += int(response.usage.total_tokens)
        except Exception:
            pass

    def _execute_tool_safe(self, name: str, args: Dict[str, Any]):
        func = self.tool_functions.get(name)
        if not func:
            return f"Error: tool '{name}' not found"
        try:
            return func(**args) if isinstance(args, dict) else func(args)
        except TypeError as e:
            return f"Error calling tool '{name}': {e} (args={args})"
        except Exception as e:
            return f"Unhandled error in tool '{name}': {e}"

    def _maybe_parse_json_step(self, content: str) -> Optional[Dict[str, Any]]:
        content = (content or "").strip()
        if not content:
            return None
        # Try single JSON object in content
        try:
            obj = json.loads(content)
            if isinstance(obj, dict) and "action" in obj and isinstance(obj["action"], dict):
                action = obj["action"]
                # Strip "functions." prefix if present
                if "tool" in action and isinstance(action["tool"], str):
                    if action["tool"].startswith("functions."):
                        action["tool"] = action["tool"][10:]  # Remove "functions." prefix
                return action
        except json.JSONDecodeError:
            pass
        # Try to find JSON object inside text
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict) and "action" in obj:
                    action = obj["action"]
                    # Strip "functions." prefix if present
                    if isinstance(action, dict) and "tool" in action and isinstance(action["tool"], str):
                        if action["tool"].startswith("functions."):
                            action["tool"] = action["tool"][10:]  # Remove "functions." prefix
                    return action
            except json.JSONDecodeError:
                return None
        return None

    def _looks_final(self, text: str) -> bool:
        if not text:
            return False
        if text.strip().startswith("Final Answer:"):
            return True
        # If the model returned a JSON with final true (rare when using content), accept
        try:
            j = json.loads(text)
            if isinstance(j, dict) and j.get("final") is True:
                return True
        except Exception:
            pass
        return False

    def _extract_last_final(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        for m in reversed(messages):
            if m["role"] == "assistant" and isinstance(m.get("content"), str):
                c = m["content"]
                if c and c.strip():
                    return c
        return None

    def _stringify(self, observation: Any) -> str:
        try:
            if isinstance(observation, (dict, list)):
                return json.dumps(observation, ensure_ascii=False)
            return str(observation)
        except Exception:
            return "<unserializable observation>"

    def _update_stagnation(self, name: str, args: Dict[str, Any]):
        key = f"{name}:{json.dumps(args, sort_keys=True)}"
        if key in self._recent_actions:
            self._stuck_count += 1
        else:
            self._stuck_count = 0
        self._recent_actions.append(key)
        if len(self._recent_actions) > 16:
            self._recent_actions.pop(0)

    def _trace_to_dict(self, s: StepTrace) -> Dict[str, Any]:
        return {
            "iteration": s.iteration,
            "assistant_raw": s.assistant_raw,
            "tool_call": s.tool_call,
            "observation": s.observation,
            "analysis": s.analysis,
        }
    
    def _save_messages_to_json(self, messages: List[Dict[str, Any]], iteration: int) -> None:
        """Save messages to JSON file during execution."""
        if not self.save_messages:
            return
        
        try:
            # Create a serializable version of messages
            serializable_messages = []
            for msg in messages:
                serializable_msg = {"role": msg["role"], "content": msg.get("content", "")}
                
                # Handle tool calls if present
                if "tool_calls" in msg and msg["tool_calls"]:
                    serializable_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in msg["tool_calls"]
                    ]
                
                # Handle tool_call_id if present
                if "tool_call_id" in msg:
                    serializable_msg["tool_call_id"] = msg["tool_call_id"]
                
                serializable_messages.append(serializable_msg)
            
            data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "messages": serializable_messages,
                "message_count": len(serializable_messages)
            }
            
            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save messages: {e}")
    
    def _save_final_json(self, messages: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
        """Save final messages and results to JSON file."""
        if not self.save_messages:
            return
        
        try:
            # Create serializable messages
            serializable_messages = []
            for msg in messages:
                serializable_msg = {"role": msg["role"], "content": msg.get("content", "")}
                
                if "tool_calls" in msg and msg["tool_calls"]:
                    serializable_msg["tool_calls"] = [
                        {
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in msg["tool_calls"]
                    ]
                
                if "tool_call_id" in msg:
                    serializable_msg["tool_call_id"] = msg["tool_call_id"]
                
                serializable_messages.append(serializable_msg)
            
            final_data = {
                "timestamp": datetime.now().isoformat(),
                "model": self.model_name,
                "final_result": {
                    "final_text": result["final_text"],
                    "iterations": result["iterations"],
                    "stopped_reason": result["stopped_reason"],
                    "total_tokens": result["total_tokens"]
                },
                "messages": serializable_messages,
                "trace_summary": [
                    {
                        "iteration": t["iteration"],
                        "tool_call": t["tool_call"]["name"] if t["tool_call"] else None,
                        "has_observation": t["observation"] is not None
                    } for t in result["trace"]
                ]
            }
            
            # Save to the same messages file (not a separate final file)
            with open(self.messages_log_path, "w", encoding="utf-8") as f:
                json.dump(final_data, f, indent=2, ensure_ascii=False)
            
            if self.verbose:
                print(f"\n✅ Final messages saved to: {self.messages_log_path}")
        
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save final messages: {e}")
    
    # --- Checklist management methods --------------------------------------
    def _parse_plan_to_checklist(self, content: str) -> bool:
        """Parse the agent's JSON plan into checklist items."""
        try:
            # Look for JSON object in the content
            import re
            json_match = re.search(r'\{.*"plan".*\}', content, re.DOTALL)
            if not json_match:
                return False
            
            plan_data = json.loads(json_match.group(0))
            if "plan" not in plan_data:
                return False
            
            # Convert plan to checklist items
            self.checklist_items = []
            for item in plan_data["plan"]:
                self.checklist_items.append({
                    "step": item.get("step", len(self.checklist_items) + 1),
                    "description": item.get("desc", ""),
                    "status": "pending",
                    "started_at_iteration": None,
                    "completed_at_iteration": None
                })
            
            self.checklist_enabled = True
            self._save_checklist()
            
            if self.verbose:
                print(f"📋 Checklist created with {len(self.checklist_items)} items")
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to parse plan: {e}")
            return False
    
    def _save_checklist(self) -> None:
        """Save current checklist to JSON file."""
        if not self.checklist_enabled:
            return
        
        try:
            checklist_data = {
                "created_at": datetime.now().isoformat(),
                "current_iteration": len(self.trace),
                "items": self.checklist_items
            }
            
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump(checklist_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save checklist: {e}")
    
    def _load_checklist(self) -> None:
        """Load checklist from JSON file if it exists."""
        try:
            if self.checklist_path.exists():
                with open(self.checklist_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.checklist_items = data.get("items", [])
                    self.checklist_enabled = len(self.checklist_items) > 0
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load checklist: {e}")
    
    def _update_checklist_progress(self, iteration: int) -> None:
        """Update checklist based on recent tool calls."""
        if not self.checklist_enabled or not self.checklist_items:
            return
        
        # Simple heuristic: mark first pending item as in-progress
        # and mark in-progress items as completed after 2-3 iterations
        for item in self.checklist_items:
            if item["status"] == "pending":
                item["status"] = "in_progress"
                item["started_at_iteration"] = iteration
                break
            elif item["status"] == "in_progress" and item.get("started_at_iteration"):
                # Mark as complete if we've moved past this step
                if iteration - item["started_at_iteration"] >= 2:
                    item["status"] = "completed"
                    item["completed_at_iteration"] = iteration
        
        self._save_checklist()
    
    def _get_checklist_prompt(self, iteration: int) -> str:
        """Generate combined analysis direction + checklist status prompt."""
        # Base analysis direction (always include this)
        base_prompt = (
            "Analyze the latest tool observations. Based on your analysis, either: "
            "(a) call another tool to continue iterating, or "
            "(b) if you've tested multiple portfolio variations and achieved your targets, "
            "produce a FINAL ANSWER preceded by 'Final Answer:'."
        )
        
        # If no checklist, return just the base prompt
        if not self.checklist_enabled or not self.checklist_items:
            return base_prompt
        
        # Build checklist status display
        status_lines = ["\n\n📋 Checklist Progress (Iteration {}):".format(iteration)]
        for item in self.checklist_items:
            step_num = item.get("step", "?")
            desc = item.get("description", "")
            status = item.get("status", "pending")
            
            if status == "completed":
                status_lines.append(f"[✓ DONE] Step {step_num}: {desc}")
            elif status == "in_progress":
                status_lines.append(f"→ Step {step_num}: {desc} (IN PROGRESS)")
            else:
                status_lines.append(f"  Step {step_num}: {desc}")
        
        # Count progress
        completed = sum(1 for item in self.checklist_items if item["status"] == "completed")
        total = len(self.checklist_items)
        status_lines.append(f"\nProgress: {completed}/{total} steps completed")
        
        # Add reminder to stay on track
        status_lines.append("\nRemember to follow your plan while analyzing the results.")
        
        # Combine base prompt with checklist status
        return base_prompt + "\n".join(status_lines)

