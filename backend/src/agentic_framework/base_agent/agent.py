import json
import os
import re
from typing import List, Dict, Any, Callable, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import time

from dotenv import load_dotenv
from openai import OpenAI

# Domain tools
from backend.src.agentic_framework.base_tools.calculator import calculator
from backend.src.agentic_framework.base_tools.data_wrapper_tool import ProphitAltsDataWrapper
from backend.src.agentic_framework.base_tools.search_engine_tool import AgentSearchEngine
from backend.src.utils.choose_model_and_client import *

# Import helper classes
from .checklist_manager import ChecklistManager
from .manage_logger import MessageLogger
from .agent_utilities import AgentUtilities, StepTrace
from .args_parse import ToolArgumentParser

load_dotenv()

class BaseAgent:
    """
    Refactored BaseAgent with:
      (a) Native tool-calls + JSON ReAct
      (b) No eval() anywhere (safe JSON parsing only)
      (c) Loop/stop/summary management
      (d) Returns a clean structured trace
    """

    def __init__(self, 
                system_prompt: str, 
                user_prompt: str, 
                *, 
                model: str = None, 
                max_iterations: int = 50, 
                verbose: bool = True, 
                plan_first: bool = True, 
                final_keywords: Optional[List[str]] = None, 
                save_messages: bool = True,
            ):
        
        # self.model_name = model
        # self.llm, self.client = openai_model_and_client(model=self.model_name)

        self.llm, self.client = gemini_model_and_client()
        self.model_name = self.llm

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.plan_first = plan_first  # always plan first
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
        
        # Initialize argument parser (will be set after tools are registered)
        self._arg_parser: Optional[ToolArgumentParser] = None
        
        # Initialize helper classes
        self.message_logger = MessageLogger(save_messages=save_messages, verbose=verbose, model_name=self.model_name)
        self.checklist_manager = ChecklistManager(verbose=verbose)
        self.utilities = AgentUtilities(self)

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
            "function": {
                "name": name, 
                "description": description, 
                "parameters": parameters
            }
        }
        self.tools.append(tool_def)
        self.tool_functions[name] = function
    
    def _create_arg_parser(self):
        """Create argument parser with current tool definitions."""
        tool_registry = {}
        for tool in self.tools:
            func_def = tool.get('function', {})
            tool_registry[func_def.get('name')] = func_def
        self._arg_parser = ToolArgumentParser(tool_registry)

    # --- Core run loop -----------------------------------------------------
    def run(self) -> Dict[str, Any]:
        # Create argument parser now that all tools (base + child class) are registered
        if not self._arg_parser:
            self._create_arg_parser()
        
        if self.verbose:
            print("🚀 Starting JSON ReAct run")
            print(f"Query: {self.user_prompt}")
            print("=" * 60)
            if self.save_messages:
                print(f"📝 Saving messages to: {self.message_logger.messages_log_path}")

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.utilities.system_rules()},
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ]
        
        # Save initial messages
        self.message_logger.save_messages_to_json(messages, iteration=0)

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
            self.utilities.accumulate_usage(response)

            # Record assistant content (may be None when tool_calls are used)
            assistant_raw = msg.content or ""

            if self.verbose:
                print("  assistant_raw:", assistant_raw)

            step = StepTrace(iteration=i, assistant_raw=assistant_raw)
            
            # Try to parse plan from first response if plan_first is enabled
            if i == 1 and self.plan_first and assistant_raw:
                self.checklist_manager.parse_plan_to_checklist(assistant_raw, len(self.trace))
            
            # Parse any task completion indicators from the response
            if assistant_raw:
                self.checklist_manager.parse_progress_from_response(assistant_raw, i, len(self.trace))

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

                    # Use robust argument parser
                    if self._arg_parser:
                        args = self._arg_parser.parse_arguments(
                            tool_name=name,
                            args_json=args_json,
                            tool_function=self.tool_functions.get(name)
                        )
                    else:
                        # Fallback if parser not initialized
                        try:
                            args = json.loads(args_json)
                        except json.JSONDecodeError:
                            args = {"_raw": args_json}
                    
                    # if self.verbose:
                    #     print(f"  Parsed args for {name}: {json.dumps(args, sort_keys=True)}")

                    step.tool_call = {"name": name, "args": args}

                    # Stagnation detection to detect if the agent is stuck in a loop
                    self.utilities.update_stagnation(name, args)

                    observation = self.utilities.execute_tool_safe(name, args)
                    step.observation = observation

                    if self.verbose:
                        print(f"  tool_call -> {name} args={json.dumps(args, sort_keys=True)}")
                        print("  observation:", self.utilities.stringify(observation))

                    # tie tool result back to the tool_call_id
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": self.utilities.stringify(observation),
                    })

                # Update checklist progress (starts first pending task if needed)
                self.checklist_manager.update_checklist_progress(i, len(self.trace))
                
                # Ask the model to analyze the observation and decide next step or finalize the answer
                messages.append(
                    {
                        "role": "user",
                        "content": self.checklist_manager.get_checklist_prompt(i),
                    }
                )

            else:
                # No tool call. Check for finality
                if self.utilities.looks_final(assistant_raw):
                    # Check if checklist is complete before accepting Final Answer
                    if self.checklist_manager.is_checklist_complete():
                        final_text = assistant_raw
                        stop_reason = "final_message"
                        self.trace.append(step)
                        break
                    else:
                        # Reject Final Answer and list incomplete tasks
                        incomplete = self.checklist_manager.get_incomplete_tasks()
                        messages.append({"role": "assistant", "content": assistant_raw})
                        
                        # Build rejection message
                        reject_msg = (
                            "❌ Cannot accept Final Answer yet - checklist is incomplete!\n\n"
                            "You must complete ALL checklist items before finalizing.\n"
                            "Incomplete tasks:\n"
                        )
                        for task in incomplete:
                            status_marker = "→" if task["status"] == "in_progress" else " "
                            reject_msg += f"{status_marker} Step {task['step']}: {task['description']} ({task['status'].upper()})\n"
                        reject_msg += "\nPlease continue working through your checklist."
                        
                        messages.append({"role": "user", "content": reject_msg})
                        continue  # Don't break, continue the loop

                # If it's JSON step format, allow model to request tools via content
                content_tool = self.utilities.maybe_parse_json_step(assistant_raw)
                if content_tool:
                    name = content_tool.get("tool")
                    args = content_tool.get("args", {})

                    # Special handling: unwrap invented parallel wrapper
                    if name == "multi_tool_use.parallel" and isinstance(args, dict) and isinstance(args.get("tool_uses"), list):
                        aggregated_results: List[Dict[str, Any]] = []
                        for entry in args.get("tool_uses", []):
                            if not isinstance(entry, dict):
                                continue
                            inner_name = entry.get("recipient_name") or entry.get("tool")
                            inner_args = entry.get("parameters") or entry.get("args") or {}
                            if isinstance(inner_name, str) and inner_name.startswith("functions."):
                                inner_name = inner_name[10:]
                            # Parse/validate inner args against schema if possible
                            if self._arg_parser and isinstance(inner_name, str):
                                inner_args = self._arg_parser.parse_arguments(
                                    tool_name=inner_name,
                                    args_json=json.dumps(inner_args),
                                    tool_function=self.tool_functions.get(inner_name)
                                )
                            # Execute sequentially
                            obs = self.utilities.execute_tool_safe(inner_name, inner_args)
                            aggregated_results.append({
                                "tool": inner_name,
                                "args": inner_args,
                                "observation": obs,
                            })

                        step.tool_call = {"name": name, "args": args}
                        step.observation = {"parallel_results": aggregated_results}

                        if self.verbose:
                            print(f"  tool_call(content) -> {name} (unwrapped {len(aggregated_results)} calls)")
                            print("  observation:", self.utilities.stringify(step.observation))

                        messages.append({"role": "assistant", "content": assistant_raw})
                        messages.append({"role": "user", "content": f"Unwrapped 'multi_tool_use.parallel' and executed sequentially: {self.utilities.stringify(step.observation)}"})

                        # Update checklist progress
                        self.checklist_manager.update_checklist_progress(i, len(self.trace))
                        messages.append({"role": "user", "content": self.checklist_manager.get_checklist_prompt(i)})
                    else:
                        # Normal single tool via content JSON
                        step.tool_call = {"name": name, "args": args}
                        self.utilities.update_stagnation(name, args)
                        observation = self.utilities.execute_tool_safe(name, args)
                        step.observation = observation

                        if self.verbose:
                            print(f"  tool_call(content) -> {name} args={json.dumps(args, sort_keys=True)}")
                            print("  observation:", self.utilities.stringify(observation))

                        messages.append({"role": "assistant", "content": assistant_raw})
                        # For content-based tool calls, we can't use "tool" role - use "user" instead
                        messages.append({"role": "user", "content": f"Tool '{name}' returned: {self.utilities.stringify(observation)}"})

                        # Update checklist progress
                        self.checklist_manager.update_checklist_progress(i, len(self.trace))
                        messages.append({"role": "user", "content": self.checklist_manager.get_checklist_prompt(i)})
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
                
                time.sleep(60)

            self.trace.append(step)
            
            # Save messages after each iteration
            self.message_logger.save_messages_to_json(messages, iteration=i)

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
            final_text = self.utilities.extract_last_final(messages) or "Reached maximum iterations without a final answer."

        if self.verbose and final_text:
            print("✅ Final Answer:", final_text)

        result = {
            "final_text": final_text,
            "iterations": len(self.trace),
            "stopped_reason": stop_reason,
            "total_tokens": self.total_tokens,
            "trace": [self.utilities.trace_to_dict(s) for s in self.trace],
        }
        
        # Final save with complete trace
        if self.save_messages:
            self.message_logger.save_final_json(messages, result)
        
        return result
