import json
import os
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

# Domain tools
from backend.src.prophit_alts.core.tools.calculator import calculator
from backend.src.prophit_alts.core.tools.data_wrapper_tool import ProphitAltsDataWrapper
from backend.src.prophit_alts.core.tools.search_engine_tool import AgentSearchEngine
from backend.src.utils.choose_model_and_client import openai_model_and_client

load_dotenv()

@dataclass
class StepTrace:
    iteration: int
    assistant_raw: str = ""
    tool_call: Optional[Dict[str, Any]] = None
    observation: Optional[Any] = None
    analysis: Optional[str] = None

#TODO: add a tool to check an item off the to do list every time the model runs
class BaseAgent:
    """
    Refactored BaseAgent with:
      (a) Native tool-calls + JSON ReAct
      (b) No eval() anywhere (safe JSON parsing only)
      (c) Loop/stop/summary management
      (d) Returns a clean structured trace
    """

    def __init__(self, system_prompt: str, user_prompt: str, *, model: str = "gpt-5", max_iterations: int = 50, verbose: bool = True, plan_first: bool = True, final_keywords: Optional[List[str]] = None):
        self.model_name = model
        self.llm, self.client = openai_model_and_client(model=self.model_name)

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.plan_first = True  # always plan first
        self.final_keywords = final_keywords or ["Final Answer:", "FINAL ANSWER:"]

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

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self._system_rules()},
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]

        if self.plan_first:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Before you start, produce a short JSON plan: {\"plan\":[{\"step\":1,\"desc\":\"...\"},...]}\n"
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
                    except json.JSONDecodeError:
                        # If arguments are not valid JSON, pass raw string under a key
                        args = {"_raw": args_json}

                    step.tool_call = {"name": name, "args": args}

                    # Stagnation detection
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

                # Ask the model to analyze the observation and decide next step or finalize
                messages.append(
                    {
                        "role": "user",
                            "content": (
                                "Analyze the latest tool observations. Based on your analysis, either: "
                                "(a) call another tool to continue iterating, or "
                                "(b) if you've tested multiple portfolio variations and achieved your targets, "
                                "produce a FINAL ANSWER preceded by 'Final Answer:'."
                            ),
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
                    messages.append({"role": "tool", "content": self._stringify(observation)})

                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "Analyze the latest tool observations. Based on your analysis, either: "
                                "(a) call another tool to continue iterating, or "
                                "(b) if you've tested multiple portfolio variations and achieved your targets, "
                                "produce a FINAL ANSWER preceded by 'Final Answer:'."
                            ),
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

    # --- Helpers -----------------------------------------------------------
    def _system_rules(self) -> str:
        return (
            "You are a JSON ReAct agent. Prefer native tool-calls. When you can finalize, "
            "output a concise answer beginning with 'Final Answer:'. If you must emit a JSON step, use:\n"
            '{"thought":"...","action":{"tool":"name","args":{}}}'
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
                return obj["action"]
        except json.JSONDecodeError:
            pass
        # Try to find JSON object inside text
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict) and "action" in obj:
                    return obj["action"]
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

