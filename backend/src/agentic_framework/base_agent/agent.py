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
from backend.src.agentic_framework.base_agent.base_tools.calculator import calculator
from backend.src.agentic_framework.base_agent.base_tools.planning_tool import PlanningTool
from backend.src.utils.choose_model_and_client import *

# Import helper classes
from .tasks.manager import TaskManager
from .tasks.execution_engine import PlanExecutionEngine
from .core.logger import MessageLogger
from .core.utilities import AgentUtilities, StepTrace
from .core.arg_parser import ToolArgumentParser
from .events.manager import EventManager, AgentEvent
from .tasks.validator import TaskValidator
from .memory.error_memory import ToolErrorMemory
from .memory.semantic_memory import SemanticMemory
from .memory.episodic_memory import EpisodicMemory
from .tool_registry import register_base_tools, register_task_management_tools

load_dotenv()

#TODO: get rid of old/dead code that does not help the main agent work flow

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
                max_iterations: int = 75, 
                verbose: bool = True, 
                plan_first: bool = True, 
                final_keywords: Optional[List[str]] = None, 
                save_messages: bool = True,
                use_error_memory: bool = True,
                use_episodic_memory: bool = True,
                memory_refresh_interval: int = 6,
                strict_validation: bool = True,
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
        self.use_episodic_memory = use_episodic_memory
        self.memory_refresh_interval = memory_refresh_interval
        
        # Validation behavior toggle (strict by default)
        self.strict_validation = strict_validation

        # OpenAI tools and local dispatch map
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable[..., Any]] = {}

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

        # Register task management tools after task manager is initialized
        register_task_management_tools(self)
        
        # Initialize event system
        self.event_manager = EventManager(verbose=verbose)
        self.task_validator = TaskValidator(verbose=verbose, strict_validation=self.strict_validation)
        
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

        # Initialize episodic memory (blank each session if enabled)
        self.episodic = EpisodicMemory(reset_on_init=True) if self.use_episodic_memory else None

        # Register built-ins (after episodic is initialized so episodic tools are available)
        register_base_tools(self)
        
        # Initialize planning tool with agent context
        self.planning_tool = PlanningTool(agent=self)
        
        # Initialize execution engine for structured plan execution
        self.execution_engine = PlanExecutionEngine(
            task_manager=self.task_manager, 
            event_manager=self.event_manager,
            verbose=self.verbose,
            strict_validation=self.strict_validation
        )
        
        # Register event handlers
        self._register_event_handlers()

    def _initialize_semantic_memory(self):
        """Initialize semantic memory - override in child classes for agent-specific memories."""
        # Base agent doesn't have semantic memory by default
        # Child agents should override this to load their specific memories
        pass
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Return all available tools and their information."""
        tools_info = {}
        for tool in self.tools:
            func_def = tool.get('function', {})
            name = func_def.get('name', 'Unknown')
            tools_info[name] = {
                'description': func_def.get('description', ''),
                'parameters': func_def.get('parameters', {}),
                'required': func_def.get('parameters', {}).get('required', [])
            }
        return tools_info

    def _register_event_handlers(self):
        """Register event handlers for monitoring (progression handled by PlanExecutionEngine)."""
        
        # Simple tool execution tracking for monitoring only
        def on_tool_executed(data: Dict):
            tool_name = data.get('tool_name')
            result = data.get('result')
            
            # Track for validation
            self.recent_tool_executions.append({'tool_name': tool_name, 'result': result})
            if len(self.recent_tool_executions) > 20:  # Keep last 20
                self.recent_tool_executions.pop(0)
            
            # Note: Task progression is now handled automatically by PlanExecutionEngine
            # No manual task management needed in event handlers
        
        # Register only the monitoring handler
        self.event_manager.on(AgentEvent.TOOL_EXECUTED, on_tool_executed)
        
        # Note: Task completion and failure events are handled automatically by PlanExecutionEngine
        # Old manual progression handlers removed to prevent conflicts
    
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
    
    def _get_enhanced_task_prompt(self, iteration: int) -> str:
        """Generate enhanced plan-driven task awareness prompt.
        
        Args:
            iteration: Current iteration number
            
        Returns:
            Enhanced task prompt with comprehensive context
        """
        if not self.execution_engine.plan_loaded:
            return ""
        
        task_context = self.execution_engine.get_current_task_context()
        if task_context.get("status") != "executing":
            return ""
        
        # Get intelligent completion analysis
        completion_analysis = self.execution_engine.get_intelligent_completion_analysis()
        
        # Build comprehensive task awareness prompt
        task_prompt = (
            f"\n🎯 PLAN-DRIVEN EXECUTION STATUS (Iteration {iteration}):\n"
            f"📋 Main Task {task_context['main_task']['id']}: {task_context['main_task']['description']}"
        )
        
        if 'subtask' in task_context:
            subtask = task_context['subtask']
            task_prompt += f"\n  → Current SubTask: {subtask['description']}"
            
            # Add intelligent validation feedback
            if completion_analysis.get('current_subtask'):
                validation = completion_analysis['current_subtask']['validation']
                confidence = validation['confidence']
                if confidence >= 0.7:
                    task_prompt += f"\n    ✅ High completion confidence: {confidence:.1%} - {validation['explanation'][:50]}..."
                elif confidence >= 0.4:
                    task_prompt += f"\n    🔄 Moderate progress: {confidence:.1%} - {validation['explanation'][:50]}..."
                else:
                    task_prompt += f"\n    ⏳ Getting started: {confidence:.1%} - {validation['explanation'][:50]}..."
        
        # Add main task completion confidence
        if completion_analysis.get('main_task_analysis'):
            main_confidence = completion_analysis['main_task_analysis']['confidence']
            task_prompt += f"\n  📊 Main Task Confidence: {main_confidence:.1%}"
        
        # Add predicted tools guidance
        predicted_tools = task_context['main_task'].get('predicted_tools', [])
        if predicted_tools:
            task_prompt += f"\n  🛠️ Expected Tools: {', '.join(predicted_tools)}"
        
        # Add progress visualization
        progress = task_context['progress']
        completed = progress['main_tasks_completed']
        total = progress['main_tasks_total']
        percentage = progress['percentage']
        progress_bar = "█" * (percentage // 10) + "░" * (10 - (percentage // 10))
        task_prompt += f"\n  📈 Plan Progress: [{progress_bar}] {completed}/{total} ({percentage}%)"
        
        # Add task-specific guidance
        if 'subtask' in task_context:
            task_prompt += (
                f"\n\n💡 Focus: Complete SubTask {task_context['subtask']['id']} systematically. "
                f"The system will automatically detect completion and advance you to the next step."
            )
        else:
            task_prompt += (
                f"\n\n💡 Focus: Work on Main Task {task_context['main_task']['id']} systematically. "
                f"Use the expected tools to make measurable progress."
            )
        
        return task_prompt
    
    def _check_for_task_failure(self, tool_name: str, observation: Any) -> None:
        """Check if tool result indicates task failure and handle automatically.
        
        Args:
            tool_name: Name of the executed tool
            observation: Tool execution result
        """
        if not self.execution_engine.plan_loaded:
            return
        
        # Check for obvious failure indicators
        failure_indicators = []
        
        if isinstance(observation, Exception):
            failure_indicators.append(f"Tool {tool_name} raised exception: {str(observation)}")
        
        elif isinstance(observation, str):
            error_patterns = ['error', 'failed', 'exception', 'timeout', 'not found', 'invalid', 'denied']
            if any(pattern in observation.lower() for pattern in error_patterns):
                failure_indicators.append(f"Tool {tool_name} returned error message")
        
        elif isinstance(observation, dict):
            if observation.get('success') is False:
                failure_indicators.append(f"Tool {tool_name} returned success=False")
            if 'error' in observation and observation['error']:
                failure_indicators.append(f"Tool {tool_name} returned error: {observation['error']}")
        
        # If multiple failure indicators detected, suggest failure handling
        if len(failure_indicators) >= 1:
            if self.verbose:
                print(f"⚠️ Potential task failure detected: {'; '.join(failure_indicators)}")
            
            # Check if this is a repeated failure (stagnation)
            recent_failures = sum(1 for obs in self.recent_observations[-3:] 
                                if any(indicator in str(obs).lower() 
                                      for indicator in ['error', 'failed', 'exception']))
            
            if recent_failures >= 2:
                if self.verbose:
                    print(f"🚨 Repeated failures detected ({recent_failures}/3 recent observations)")
                
                # Auto-suggest failure handling in the next iteration
                # (This will be picked up by stagnation detection)
    
    def _check_plan_completion_status(self) -> Dict[str, Any]:
        """Check overall plan completion status and readiness for final answer.
        
        Returns:
            Dictionary with completion status and context
        """
        if not self.execution_engine.plan_loaded:
            return {"plan_loaded": False, "can_finalize": True}
        
        task_context = self.execution_engine.get_current_task_context()
        execution_summary = self.execution_engine.get_execution_summary()
        
        # Check if all tasks are completed
        all_complete = (task_context.get("status") != "executing" or 
                       execution_summary.get('completed_main_tasks', 0) == execution_summary.get('total_main_tasks', 0))
        
        return {
            "plan_loaded": True,
            "all_tasks_complete": all_complete,
            "can_finalize": all_complete,
            "progress_percentage": task_context.get('progress', {}).get('percentage', 0),
            "completed_tasks": execution_summary.get('completed_main_tasks', 0),
            "total_tasks": execution_summary.get('total_main_tasks', 0),
            "current_task": task_context.get('main_task', {}).get('id') if task_context.get("status") == "executing" else None
        }
    
    def _check_and_advance_task_if_complete(self) -> None:
        """Check if current task should be completed and advance automatically using intelligent validation."""
        if not self.execution_engine.plan_loaded:
            return
        
        # Get intelligent completion analysis
        completion_analysis = self.execution_engine.get_intelligent_completion_analysis()
        
        # Check if current task meets completion conditions
        should_complete, reason = self.execution_engine.check_task_completion_conditions()
        
        if should_complete:
            if self.verbose:
                print(f"🔍 Intelligent completion detected: {reason}")
                
                # Show detailed analysis if available
                if completion_analysis.get('main_task_analysis'):
                    main_confidence = completion_analysis['main_task_analysis']['confidence']
                    print(f"  📊 Main task confidence: {main_confidence:.2f}")
                
                if completion_analysis.get('current_subtask'):
                    subtask_validation = completion_analysis['current_subtask']['validation']
                    print(f"  📊 Subtask confidence: {subtask_validation['confidence']:.2f}")
            
            # Advance to next task
            success, message = self.execution_engine.advance_task_progression()
            
            if success and self.verbose:
                print(f"🚀 Task auto-advanced: {message}")
            elif not success and self.verbose:
                print(f"⚠️ Failed to advance task: {message}")
        elif self.verbose:
            # Show near-completion status for debugging
            if completion_analysis.get('main_task_analysis'):
                main_confidence = completion_analysis['main_task_analysis']['confidence']
                if main_confidence >= 0.5:
                    print(f"  📊 Task progress: {main_confidence:.2f} confidence - {reason}")
    
    def _create_arg_parser(self):
        """Create argument parser with current tool definitions."""
        tool_registry = {}
        for tool in self.tools:
            func_def = tool.get('function', {})
            tool_registry[func_def.get('name')] = func_def
        self._arg_parser = ToolArgumentParser(tool_registry, verbose=self.verbose)

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

    # --- Set Up -----------------------------------------------------

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
            # Use new structured planning tool with enhanced plan-driven execution instructions
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "🎯 PLAN-DRIVEN EXECUTION MODE:\n\n"
                        "1. First, create a comprehensive structured plan using the 'create_structured_plan' tool.\n"
                        "2. This will generate a detailed TodoList with main tasks and subtasks.\n"
                        "3. Once the plan is loaded, you will ALWAYS see your current task context.\n"
                        "4. Work systematically through the plan - focus on the current task/subtask shown.\n"
                        "5. The system will automatically track your progress and advance tasks when complete.\n"
                        "6. Use task management tools (get_current_task_info, get_completion_analysis) to stay aware.\n\n"
                        "Call the 'create_structured_plan' tool now to begin systematic execution."
                    ),
                }
            )

        final_text: Optional[str] = None
        stop_reason: str = ""
        
    # --- Begin Loop -----------------------------------------------------

        # Track plan loading for context injection
        plan_loaded_this_iteration: bool = False
        plan_start_context: Optional[str] = None

        for i in range(1, self.max_iterations + 1):
            # Reset plan loading tracking for this iteration
            plan_loaded_this_iteration = False
            plan_start_context = None
            
            if self.verbose:
                print(f"\n ⚜️  Iteration {i}")
                
                # Show current task context for plan-driven execution awareness
                if self.execution_engine.plan_loaded:
                    task_context = self.execution_engine.get_current_task_context()
                    if task_context.get("status") == "executing":
                        main_task = task_context['main_task']
                        print(f"  📋 Current Task: {main_task['id']} - {main_task['description']}")
                        if 'subtask' in task_context:
                            subtask = task_context['subtask']
                            print(f"    → SubTask: {subtask['id']} - {subtask['description']}")
                        
                        progress = task_context.get('progress', {})
                        completed = progress.get('main_tasks_completed', 0)
                        total = progress.get('main_tasks_total', 0)
                        if total > 0:
                            print(f"    📊 Plan Progress: {completed}/{total} ({progress.get('percentage', 0)}%)")
            
            # Inject plan-based context at regular intervals for task awareness
            if (self.execution_engine.plan_loaded and i > 1 and i % 3 == 0):
                task_context = self.execution_engine.get_current_task_context()
                if task_context.get("status") == "executing":
                    # Get completion analysis for current state
                    completion_analysis = self.execution_engine.get_intelligent_completion_analysis()
                    
                    plan_prompt = (
                        f"📋 PLAN STATUS UPDATE (Iteration {i}):\n"
                        f"Current Task: {task_context['main_task']['description']}"
                    )
                    
                    if 'subtask' in task_context:
                        plan_prompt += f"\nCurrent SubTask: {task_context['subtask']['description']}"
                    
                    # Add completion confidence if available
                    if completion_analysis.get('main_task_analysis'):
                        confidence = completion_analysis['main_task_analysis']['confidence']
                        plan_prompt += f"\nTask Completion Confidence: {confidence:.1%}"
                    
                    plan_prompt += f"\nOverall Progress: {task_context['progress']['main_tasks_completed']}/{task_context['progress']['main_tasks_total']} main tasks completed"
                    plan_prompt += "\n\nContinue working on your current task systematically."
                    
                    messages.append({
                        "role": "user",
                        "content": plan_prompt
                    })
            
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

            temperature = None if "gpt-5" in self.llm else 0.8

            response = self.client.chat.completions.create(
                model=self.llm,
                messages=messages,
                tools=self.tools if self.tools else None,
                tool_choice="auto" if self.tools else None,
                temperature=temperature        
            )

            choice = response.choices[0]
            msg = choice.message
            self.utilities.accumulate_usage(response)

            # Record assistant content (may be None when tool_calls are used)
            assistant_raw = msg.content or ""

            if self.verbose:
                print("  assistant_raw:", assistant_raw)

            step = StepTrace(iteration=i, assistant_raw=assistant_raw)
            
            # Task progress is now handled through structured planning and tool calls

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
                    
                    # Handle structured planning tool results and load into execution engine
                    if name == "create_structured_plan":
                        plan_result = observation
                        if isinstance(plan_result, dict) and plan_result.get('success'):
                            # Load the plan into execution engine
                            plan_data = plan_result.get('plan', {})
                            
                            # Convert plan_data to TodoList model
                            from .tasks.models import TodoList
                            try:
                                todo_list = TodoList.model_validate(plan_data)
                                
                                # Load plan into execution engine with enhanced status updates
                                if self.execution_engine.load_plan(todo_list):
                                    if self.verbose:
                                        print("✅ Plan loaded into execution engine")
                                        
                                        # Show initial plan overview
                                        plan_summary = self.task_manager.get_task_progress_summary()
                                        print(f"📊 Plan Overview: {plan_summary['total_main_tasks']} main tasks, {plan_summary['total_subtasks']} subtasks")
                                    
                                    # Prepare plan start context for injection after tool responses
                                    task_context = self.execution_engine.get_current_task_context()
                                    if task_context.get("status") == "executing":
                                        plan_start_context = (
                                            f"🎯 STRUCTURED PLAN LOADED & EXECUTION STARTED:\n"
                                            f"📋 Starting with Task {task_context['main_task']['id']}: {task_context['main_task']['description']}"
                                        )
                                        
                                        if 'subtask' in task_context:
                                            plan_start_context += f"\n  → First SubTask: {task_context['subtask']['description']}"
                                        
                                        # Add predicted tools for the first task
                                        predicted_tools = task_context['main_task'].get('predicted_tools', [])
                                        if predicted_tools:
                                            plan_start_context += f"\n  🛠️ Expected Tools: {', '.join(predicted_tools)}"
                                        
                                        plan_start_context += f"\n  📈 Total Plan: {task_context['progress']['main_tasks_total']} main tasks to complete"
                                        plan_start_context += (
                                            "\n\n💡 The system will automatically track your progress and advance you through tasks. "
                                            "Focus on the current task and use appropriate tools systematically."
                                        )
                                        
                                        plan_loaded_this_iteration = True
                            except Exception as e:
                                if self.verbose:
                                    print(f"⚠️ Failed to load plan into execution engine: {e}")
                    
                    # Update execution engine with tool result
                    self.execution_engine.update_task_from_tool_result(name, observation)
                    
                    # Check for task failure indicators
                    self._check_for_task_failure(name, observation)
                    
                    # Check if current task should be completed and advance if so
                    self._check_and_advance_task_if_complete()
                    
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

                # Update task progress and status automatically
                self.task_manager.update_task_progress(i)
                
                # Inject plan start context if plan was loaded this iteration (after all tool responses)
                if plan_loaded_this_iteration and plan_start_context:
                    messages.append({
                        "role": "system",
                        "content": plan_start_context
                    })
                    plan_loaded_this_iteration = False  # Reset flag
                    plan_start_context = None
                
                # Enhanced plan-driven prompting using centralized method
                base_prompt = "Analyze the tool results and continue your systematic execution."
                task_prompt = self._get_enhanced_task_prompt(i)
                
                # Ask the model to analyze the observation and decide next step or finalize the answer
                messages.append(
                    {
                        "role": "user",
                        "content": base_prompt + task_prompt,
                    }
                )

            else:
                # No tool call. Check for finality with enhanced plan awareness
                if self.utilities.looks_final(assistant_raw):
                    # Use enhanced plan completion checking
                    completion_status = self._check_plan_completion_status()
                    
                    if completion_status["can_finalize"]:
                        # Plan is complete or no plan loaded - accept final answer
                        if self.verbose and completion_status.get("plan_loaded"):
                            print(f"✅ Plan execution complete: {completion_status['completed_tasks']}/{completion_status['total_tasks']} tasks finished")
                        
                        final_text = assistant_raw
                        stop_reason = "final_message"
                        self.trace.append(step)
                        break
                    else:
                        # Reject Final Answer and show current task status
                        messages.append({"role": "assistant", "content": assistant_raw})
                        
                        # Build rejection message with execution engine context
                        if self.execution_engine.plan_loaded:
                            task_context = self.execution_engine.get_current_task_context()
                            execution_summary = self.execution_engine.get_execution_summary()
                            
                            reject_msg = (
                                "❌ Cannot accept Final Answer yet - structured plan is not complete!\n\n"
                                f"📋 Current Status: {execution_summary.get('completed_main_tasks', 0)}/{execution_summary.get('total_main_tasks', 0)} main tasks completed\n"
                            )
                            
                            if task_context.get("status") == "executing":
                                reject_msg += f"▶️ Currently working on: Task {task_context['main_task']['id']}: {task_context['main_task']['description']}\n"
                                if 'subtask' in task_context:
                                    reject_msg += f"  → SubTask: {task_context['subtask']['description']}\n"
                            
                            reject_msg += "\nPlease continue working through your structured plan before providing a Final Answer."
                        else:
                            # Fallback to old task manager approach
                            incomplete = self.task_manager.get_incomplete_tasks()
                            reject_msg = (
                                "❌ Cannot accept Final Answer yet - task list is incomplete!\n\n"
                                "You must complete ALL tasks before finalizing.\n"
                                "Incomplete tasks:\n"
                            )
                            for task in incomplete:
                                status_marker = "→" if task.get("status") == "in_progress" else " "
                                task_id = task.get('id', task.get('step', 'Unknown'))
                                reject_msg += f"{status_marker} Task {task_id}: {task['description']} ({task.get('status', 'unknown').upper()})\n"
                            reject_msg += "\nPlease continue working through your task list."
                        
                        messages.append({"role": "user", "content": reject_msg})
                        continue  # Don't break, continue the loop

                # If it's JSON step format, allow model to request tools via content
                content_tool = self.utilities.maybe_parse_json_step(assistant_raw)
                
                if content_tool:
                    name = content_tool.get("tool")
                    args = content_tool.get("args", {})
                    
                    # Skip if no valid tool name found
                    if not name:
                        if self.verbose:
                            print(f"⚠️ Skipping tool call - no valid tool name found in: {assistant_raw[:100]}...")
                        continue

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
                        self.task_manager.update_task_progress(i)
                        
                        # Inject plan start context if plan was loaded this iteration (after all tool responses)
                        if plan_loaded_this_iteration and plan_start_context:
                            messages.append({
                                "role": "system",
                                "content": plan_start_context
                            })
                            plan_loaded_this_iteration = False  # Reset flag
                            plan_start_context = None
                        
                        # Enhanced plan-driven prompting using centralized method
                        base_prompt = "Continue your systematic plan execution."
                        task_prompt = self._get_enhanced_task_prompt(i)
                        
                        messages.append({"role": "user", "content": base_prompt + task_prompt})
                    else:
                        # Normal single tool via content JSON
                        step.tool_call = {"name": name, "args": args}
                        self.utilities.update_stagnation(name, args)
                        observation = self.utilities.execute_tool_safe(name, args)
                        step.observation = observation
                        
                        # Update execution engine with tool result
                        self.execution_engine.update_task_from_tool_result(name, observation)
                        
                        # Check for task failure indicators
                        self._check_for_task_failure(name, observation)
                        
                        # Check if current task should be completed and advance if so
                        self._check_and_advance_task_if_complete()
                        
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
                        self.task_manager.update_task_progress(i)
                        
                        # Inject plan start context if plan was loaded this iteration (after all tool responses)
                        if plan_loaded_this_iteration and plan_start_context:
                            messages.append({
                                "role": "system",
                                "content": plan_start_context
                            })
                            plan_loaded_this_iteration = False  # Reset flag
                            plan_start_context = None
                        
                        # Enhanced plan-driven prompting using centralized method
                        base_prompt = "Continue your systematic plan execution."
                        task_prompt = self._get_enhanced_task_prompt(i)
                        
                        messages.append({"role": "user", "content": base_prompt + task_prompt})
                else:
                    # Enhanced guidance based on plan state
                    messages.append({"role": "assistant", "content": assistant_raw})
                    
                    # Plan-driven guidance when no tool call is made
                    if self.execution_engine.plan_loaded:
                        task_context = self.execution_engine.get_current_task_context()
                        if task_context.get("status") == "executing":
                            # Get completion analysis to guide next steps
                            completion_analysis = self.execution_engine.get_intelligent_completion_analysis()
                            
                            guidance_msg = (
                                "🎯 PLAN-DRIVEN GUIDANCE: You didn't call a tool. Based on your structured plan:\n"
                            )
                            
                            # Add current task context
                            if 'subtask' in task_context:
                                guidance_msg += f"Current SubTask: {task_context['subtask']['description']}\n"
                                
                                # Add validation guidance
                                if completion_analysis.get('current_subtask'):
                                    validation = completion_analysis['current_subtask']['validation']
                                    confidence = validation['confidence']
                                    if confidence >= 0.7:
                                        guidance_msg += "✅ This subtask appears near completion. Consider using 'advance_to_next_task' or call a final tool.\n"
                                    else:
                                        guidance_msg += f"🔄 SubTask needs more work (confidence: {confidence:.1%}). Call appropriate tools to make progress.\n"
                            else:
                                guidance_msg += f"Current Main Task: {task_context['main_task']['description']}\n"
                            
                            # Add tool suggestions
                            predicted_tools = task_context['main_task'].get('predicted_tools', [])
                            if predicted_tools:
                                guidance_msg += f"Expected Tools: {', '.join(predicted_tools)}\n"
                            
                            guidance_msg += (
                                "\nNext Steps: Either call a tool to make progress on your current task, "
                                "or if you believe the current task is complete, use 'advance_to_next_task' to move forward."
                            )
                        else:
                            guidance_msg = (
                                "You provided no tool-call. If additional work is required, either call a tool now or do further analysis. "
                                "Otherwise produce a 'Final Answer:' and stop."
                            )
                    else:
                        guidance_msg = (
                            "You provided no tool-call. If additional work is required, either call a tool now or do further analysis. "
                            "Otherwise produce a 'Final Answer:' and stop."
                        )
                    
                    messages.append(
                        {
                            "role": "user",
                            "content": guidance_msg,
                        }
                    )

            self.trace.append(step)
            
            # Save messages after each iteration
            self.message_logger.save_messages_to_json(messages, iteration=i)
            
            # Enhanced iteration tracking with plan-driven execution awareness
            iteration_data = {
                'iteration': i,
                'had_tool_call': step.tool_call is not None,
            }
            
            # Add plan execution context to iteration tracking
            if self.execution_engine.plan_loaded:
                task_context = self.execution_engine.get_current_task_context()
                if task_context.get("status") == "executing":
                    iteration_data['current_main_task'] = task_context['main_task']['id']
                    if 'subtask' in task_context:
                        iteration_data['current_subtask'] = task_context['subtask']['id']
                    iteration_data['plan_progress'] = task_context['progress']['percentage']
                    
                    # Check if plan completed this iteration
                    if task_context['progress']['main_tasks_completed'] == task_context['progress']['main_tasks_total']:
                        iteration_data['plan_completed'] = True
                        if self.verbose:
                            print("🎉 Structured plan execution completed!")
            
            # Emit iteration complete event
            self.event_manager.emit(AgentEvent.ITERATION_COMPLETE, iteration_data)

            if self.verbose:
                print("" + "-"*80)

            # Enhanced stagnation guard with plan-driven failure handling
            if self._stuck_count >= self._stuck_threshold:
                # Check for stagnation in plan execution context
                if self.execution_engine.plan_loaded:
                    is_stagnating, stagnation_reason = self.execution_engine.check_for_stagnation(
                        self.recent_observations, 
                        threshold=3
                    )
                    
                    if is_stagnating:
                        # Handle stagnation with intelligent recovery
                        if self.verbose:
                            print(f"🔄 Stagnation detected: {stagnation_reason}")
                        
                        # Suggest failure handling
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"🚨 STAGNATION DETECTED: {stagnation_reason}\n\n"
                                    "Your current task appears to be stagnating. Consider these options:\n"
                                    "1. Use 'handle_task_failure' tool with recovery strategy\n"
                                    "2. Use 'advance_to_next_task' to move forward\n"
                                    "3. Try alternative tools or approaches\n"
                                    "4. Use 'get_completion_analysis' to assess current state\n\n"
                                    "Choose an appropriate action to break out of the stagnation."
                                ),
                            }
                        )
                    else:
                        # Regular stagnation message with plan context
                        task_context = self.execution_engine.get_current_task_context()
                        current_task_info = ""
                        if task_context.get("status") == "executing":
                            current_task_info = f"\nCurrent Task: {task_context['main_task']['description']}"
                            if 'subtask' in task_context:
                                current_task_info += f"\nCurrent SubTask: {task_context['subtask']['description']}"
                        
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    "🔄 You are repeating similar actions without new progress. "
                                    f"{current_task_info}\n\n"
                                    "Consider: different tools, alternative approach, or use 'handle_task_failure' if stuck."
                                ),
                            }
                        )
                else:
                    # Original stagnation message when no plan loaded
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
                    
        # THIS IS WHERE THE AGENT LOOP ENDS 
        # THE FOLLOWING CODE IS FOR THE FINAL ANSWER AND SAVING THE MESSAGES

        else:
            stop_reason = "max_iterations"

        # If no explicit final_text was emitted, try to extract the last assistant content
        if final_text is None:
            final_text = self.utilities.extract_last_final(messages) or "Reached maximum iterations without a final answer."

        if self.verbose and final_text:
            print("✅ Final Answer:", final_text)
            
            # Show plan execution summary if plan was loaded
            if self.execution_engine.plan_loaded:
                execution_summary = self.execution_engine.get_execution_summary()
                progress_summary = self.task_manager.get_task_progress_summary()
                
                print("\n📊 PLAN EXECUTION SUMMARY:")
                print(f"  📋 Total Main Tasks: {execution_summary.get('total_main_tasks', 0)}")
                print(f"  ✅ Completed: {execution_summary.get('completed_main_tasks', 0)}")
                print(f"  📈 Final Progress: {progress_summary.get('overall_progress_percentage', 0)}%")
                print(f"  📝 Evidence Items: {progress_summary.get('execution_history_entries', 0)}")

        result = {
            "final_text": final_text,
            "iterations": len(self.trace),
            "stopped_reason": stop_reason,
            "total_tokens": self.total_tokens,
            "trace": [self.utilities.trace_to_dict(s) for s in self.trace],
        }
        
        # Add comprehensive plan execution data to result if available
        if self.execution_engine.plan_loaded:
            # Get all analytics data
            analytics_report = self.execution_engine.create_plan_analytics_report()
            
            result["plan_execution"] = {
                "execution_summary": self.execution_engine.get_execution_summary(),
                "progress_summary": self.task_manager.get_task_progress_summary(),
                "execution_analytics": self.task_manager.get_execution_analytics(),
                "plan_health": self.task_manager.get_plan_health_status(),
                "analytics_report": analytics_report,
                "plan_completed": self.execution_engine.get_current_task() is None,
                "failed_tasks": self.task_manager.get_failed_tasks(),
                "parallel_execution_potential": self.execution_engine.simulate_parallel_execution()
            }
        
        # Final save with complete trace
        if self.save_messages:
            self.message_logger.save_final_json(messages, result)
        
        return result
