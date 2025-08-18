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
from .tasks.manager import TaskManager
from .core.logger import MessageLogger
from .core.utilities import AgentUtilities, StepTrace
from .core.arg_parser import ToolArgumentParser
from .events.manager import EventManager, AgentEvent
from .tasks.validator import TaskValidator
from .memory.error_memory import ToolErrorMemory
from .memory.semantic_memory import SemanticMemory

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
                use_error_memory: bool = True,
                memory_refresh_interval: int = 6,
            ):
        
        self.model_name = model
        self.llm, self.client = openai_model_and_client()

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.plan_first = plan_first  # always plan first
        self.final_keywords = final_keywords or ["Final Answer:", "FINAL ANSWER:"]
        self.save_messages = save_messages
        self.use_error_memory = use_error_memory
        self.memory_refresh_interval = memory_refresh_interval

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
        self.task_manager = TaskManager(verbose=verbose)
        self.utilities = AgentUtilities(self)
        
        # Initialize event system
        self.event_manager = EventManager(verbose=verbose)
        self.task_validator = TaskValidator(verbose=verbose)
        
        # Initialize error memory system
        if self.use_error_memory:
            self.error_memory = ToolErrorMemory(save_memory=True, verbose=verbose)
            # Pre-populate with common solutions
            if not self.error_memory.error_patterns:
                from .memory.error_memory import initialize_common_solutions
                self.error_memory = initialize_common_solutions()
        else:
            self.error_memory = None
        
        # Track recent tool executions for validation
        self.recent_tool_executions: List[Dict] = []
        self.recent_observations: List[Any] = []
        
        # Track last tool error for retry guidance
        self.last_tool_error: Optional[Dict] = None
        
        # Initialize semantic memory (child classes override this)
        self.semantic_memory: Optional[SemanticMemory] = None
        self._initialize_semantic_memory()
        
        # Register event handlers
        self._register_event_handlers()

    def _initialize_semantic_memory(self):
        """Initialize semantic memory - override in child classes for agent-specific memories."""
        # Base agent doesn't have semantic memory by default
        # Child agents should override this to load their specific memories
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
        
        # Task management tools
        self._register_task_management_tools()

    def _register_task_management_tools(self):
        """Register task management tools for structured updates."""
        
        # Update task status with evidence
        self.add_tool(
            name="update_task_status",
            description="Update the status of a task with evidence of completion or progress",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string", 
                        "description": "Task identifier (e.g., 'task_1' or just '1' for step 1)"
                    },
                    "status": {
                        "type": "string", 
                        "enum": ["started", "in_progress", "completed", "failed", "blocked"],
                        "description": "New task status"
                    },
                    "evidence": {
                        "type": "object",
                        "description": "Evidence supporting the status change",
                        "properties": {
                            "outputs": {"type": "object", "description": "Task outputs/results"},
                            "observations": {"type": "array", "items": {"type": "string"}},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                        }
                    },
                    "reason": {
                        "type": "string", 
                        "description": "Explanation for the status change"
                    }
                },
                "required": ["task_id", "status"]
            },
            function=lambda **kwargs: self.task_manager.update_task_status(**kwargs)
        )
        
        # Mark task complete (simplified version)
        self.add_tool(
            name="mark_task_complete",
            description="Mark a task as complete with optional outputs",
            parameters={
                "type": "object",
                "properties": {
                    "task_id": {
                        "type": "string",
                        "description": "Task identifier (e.g., 'task_1' or just '1' for step 1)"
                    },
                    "outputs": {
                        "type": "object",
                        "description": "Task outputs/results"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Brief summary of what was accomplished"
                    }
                },
                "required": ["task_id"]
            },
            function=lambda task_id, outputs=None, summary=None: self.task_manager.update_task_status(
                task_id=task_id,
                status="completed",
                evidence={"outputs": outputs or {}, "summary": summary} if (outputs or summary) else None,
                reason=summary
            )
        )

    def _register_event_handlers(self):
        """Register event handlers for task management."""
        
        # Handle tool execution events
        def on_tool_executed(data: Dict):
            tool_name = data.get('tool_name')
            result = data.get('result')
            
            # Track for validation
            self.recent_tool_executions.append({'tool_name': tool_name, 'result': result})
            if len(self.recent_tool_executions) > 20:  # Keep last 20
                self.recent_tool_executions.pop(0)
            
            # Check current task progress
            current_task = self.task_manager.get_current_task()
            if current_task:
                # Quick validation based on tool result
                is_complete, confidence, reason = self.task_validator.validate_from_tool_result(
                    current_task, tool_name, result
                )
                
                if is_complete and confidence >= 0.8:
                    # Task appears complete, emit completion event
                    self.event_manager.emit_task_completed(
                        current_task.id,
                        outputs=current_task.outputs,
                        confidence=confidence
                    )
        
        # Handle task completion events
        def on_task_completed(data: Dict):
            task_id = data.get('task_id')
            confidence = data.get('confidence', 1.0)
            
            # Update task status
            self.task_manager.update_task_status(
                task_id,
                'completed',
                evidence={'confidence': confidence, 'auto_detected': True},
                reason='Auto-detected completion from tool execution'
            )
            
            # Start next task if available
            next_tasks = self.task_manager.get_next_tasks()
            if next_tasks and len(next_tasks) > 0:
                next_task = next_tasks[0]
                self.task_manager.update_task_status(
                    next_task.id,
                    'in_progress',
                    reason='Auto-started after previous task completion'
                )
                self.event_manager.emit_task_started(next_task.id, next_task.description)
        
        # Handle task failure events
        def on_task_failed(data: Dict):
            task_id = data.get('task_id')
            error = data.get('error')
            
            # Update task status
            self.task_manager.update_task_status(
                task_id,
                'failed',
                evidence={'error': error},
                reason=f'Task failed: {error}'
            )
        
        # Register the handlers
        self.event_manager.on(AgentEvent.TOOL_EXECUTED, on_tool_executed)
        self.event_manager.on(AgentEvent.TASK_COMPLETED, on_task_completed)
        self.event_manager.on(AgentEvent.TASK_FAILED, on_task_failed)
    
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
        ]
        
        # Inject semantic memories if available
        if self.semantic_memory:
            memory_context = self.semantic_memory.format_memories_for_prompt()
            if memory_context:
                messages.append({"role": "system", "content": memory_context})
        
        messages.extend([
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_prompt},
        ])
        
        # Save initial messages
        self.message_logger.save_messages_to_json(messages, iteration=0)

        if self.plan_first:
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Before you start, produce a JSON plan to follow that will accomplish the user's goal: {\"plan\":[{\"step\":1,\"desc\":\"...\"},...]}\n"
                        "After you produce the json plan, you must come up with an actionable to-do list which must be numbered in the following format: \n\n"
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
            
            # Periodically re-inject semantic memory to keep it fresh in context
            if (self.semantic_memory and 
                self.memory_refresh_interval > 0 and 
                i > 1 and 
                i % self.memory_refresh_interval == 0):
                
                # Use concise format for refresh to avoid context bloat
                memory_refresh = self.semantic_memory.format_memories_for_prompt(concise=False)
                if memory_refresh:
                    if self.verbose:
                        print(f"  🔄 Refreshing semantic memory (every {self.memory_refresh_interval} iterations)")
                    
                    # Inject as a user message to reinforce the concepts
                    messages.append({
                        "role": "user",
                        "content": (
                            f"📌 REMINDER - Key principles to maintain (iteration {i}):\n"
                            f"{memory_refresh}\n"
                            "Continue applying these principles in your analysis."
                        )
                    })

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
                parsed = self.task_manager.parse_plan_to_tasks(assistant_raw, len(self.trace))
                if parsed:
                    # Emit plan created event
                    self.event_manager.emit(AgentEvent.PLAN_CREATED, {
                        'task_count': len(self.task_manager.tasks)
                    })
            
            # Parse any task completion indicators from the response
            if assistant_raw:
                self.task_manager.parse_progress_from_response(assistant_raw, i, len(self.trace))

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
                    
                    # Emit tool executed event
                    self.event_manager.emit_tool_executed(name, args, observation)
                    
                    # Track observation for validation
                    self.recent_observations.append(observation)
                    if len(self.recent_observations) > 20:  # Keep last 20
                        self.recent_observations.pop(0)

                    if self.verbose:
                        print(f"  tool_call -> {name} args={json.dumps(args, sort_keys=True)}")
                        print("  observation:", self.utilities.stringify(observation))

                    # tie tool result back to the tool_call_id
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": self.utilities.stringify(observation),
                    })

                # Update task progress (starts first pending task if needed)
                self.task_manager.update_task_progress(i, len(self.trace))
                
                # Ask the model to analyze the observation and decide next step or finalize the answer
                messages.append(
                    {
                        "role": "user",
                        "content": self.task_manager.get_task_status_prompt(i),
                    }
                )

            else:
                # No tool call. Check for finality
                if self.utilities.looks_final(assistant_raw):
                    # Check if all tasks are complete before accepting Final Answer
                    if self.task_manager.is_checklist_complete():
                        final_text = assistant_raw
                        stop_reason = "final_message"
                        self.trace.append(step)
                        break
                    else:
                        # Reject Final Answer and list incomplete tasks
                        incomplete = self.task_manager.get_incomplete_tasks()
                        messages.append({"role": "assistant", "content": assistant_raw})
                        
                        # Build rejection message
                        reject_msg = (
                            "❌ Cannot accept Final Answer yet - task list is incomplete!\n\n"
                            "You must complete ALL tasks before finalizing.\n"
                            "Incomplete tasks:\n"
                        )
                        for task in incomplete:
                            status_marker = "→" if task["status"] == "in_progress" else " "
                            reject_msg += f"{status_marker} Step {task['step']}: {task['description']} ({task['status'].upper()})\n"
                        reject_msg += "\nPlease continue working through your task list."
                        
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
                            
                            # Emit event for each inner tool
                            self.event_manager.emit_tool_executed(inner_name, inner_args, obs)
                            
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

                        # Update task progress
                        self.task_manager.update_task_progress(i, len(self.trace))
                        messages.append({"role": "user", "content": self.task_manager.get_task_status_prompt(i)})
                    else:
                        # Normal single tool via content JSON
                        step.tool_call = {"name": name, "args": args}
                        self.utilities.update_stagnation(name, args)
                        observation = self.utilities.execute_tool_safe(name, args)
                        step.observation = observation
                        
                        # Emit tool executed event
                        self.event_manager.emit_tool_executed(name, args, observation)
                        
                        # Track observation
                        self.recent_observations.append(observation)
                        if len(self.recent_observations) > 20:
                            self.recent_observations.pop(0)

                        if self.verbose:
                            print(f"  tool_call(content) -> {name} args={json.dumps(args, sort_keys=True)}")
                            print("  observation:", self.utilities.stringify(observation))

                        messages.append({"role": "assistant", "content": assistant_raw})
                        # For content-based tool calls, we can't use "tool" role - use "user" instead
                        messages.append({"role": "user", "content": f"Tool '{name}' returned: {self.utilities.stringify(observation)}"})

                        # Update task progress
                        self.task_manager.update_task_progress(i, len(self.trace))
                        messages.append({"role": "user", "content": self.task_manager.get_task_status_prompt(i)})
                else:
                    # Ask the model to either pick a tool or finalize
                    messages.append({"role": "assistant", "content": assistant_raw})
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                "You provided no tool-call. If additional work is required, either call a tool now or do further analysis. "
                                "Otherwise produce a 'Final Answer:' and stop."
                            ),
                        }
                    )

            self.trace.append(step)
            
            # Save messages after each iteration
            self.message_logger.save_messages_to_json(messages, iteration=i)
            
            # Emit iteration complete event
            self.event_manager.emit(AgentEvent.ITERATION_COMPLETE, {
                'iteration': i,
                'had_tool_call': step.tool_call is not None,
                'current_task': self.task_manager.get_current_task().id if self.task_manager.get_current_task() else None
            })

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
            
            # time.sleep(100)
        
        # THIS IS WHERE THE AGENT LOOP ENDS 
        # THE FOLLOWING CODE IS FOR THE FINAL ANSWER AND SAVING THE MESSAGES
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
