import json
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from pathlib import Path
from dotenv import load_dotenv
from app.core.agentic_framework.tool_lib.base_tools.planning_tool import PlanningTool
from app.utils.choose_model_and_client import *
from app.utils.token_count import get_chat_token_count

# Import helper classes
from .tasks.manager import TaskManager
from .tasks.executor import PlanExecutor
from .core.logger import MessageLogger
from .core.utilities import AgentUtilities, StepTrace
from .core.arg_parser import ToolArgumentParser
from .core.result_parser import parse_tool_result
from .tasks.validation.completion_validator import CompletionValidator as TaskValidator
from .memory.domain_memory import DomainMemory
from .memory.episodic_memory import EpisodicMemory
from .tool_registry import register_base_tools, register_task_management_tools
from .utils.path_utils import create_agent_output_dir

# Import extracted components (Phase 3)
from .execution.iteration_response_processor import IterationResponseProcessor
from .execution.stagnation_tracker import StagnationTracker
from .execution.agent_execution_loop import AgentExecutionLoop
from .prompting.context_builder import ContextBuilder

load_dotenv()

class BaseAgent:
    """Foundation agent implementing ReAct pattern with native LLM tool calling.

    This agent executes autonomous task completion through:
    - ReAct loop with native tool calling (OpenAI/Claude/Grok)
    - Structured task planning and execution via PlanExecutor
    - Memory systems (domain and episodic)
    - Stagnation detection and recovery
    - Full execution tracing and token accounting

    Architecture (Phase 3 Refactor):
    - AgentExecutionLoop: Multi-iteration loop management
    - IterationResponseProcessor: Single response processing
    - ContextBuilder: Message and context injection
    - StagnationTracker: Detects and handles stagnation
    - TaskManager: Task planning and progress tracking
    - PlanExecutor: Structured plan execution engine
    """

    def __init__(self,
                system_prompt: str,
                user_prompt: str,
                *,
                model: str = None,
                reasoning_effort: str = None,
                temperature: float = None,
                max_iterations: int = 75,
                verbose: bool = True,
                plan_first: bool = True,
                final_keywords: Optional[List[str]] = None,
                save_messages: bool = True,
                use_episodic_memory: bool = True,
                memory_refresh_interval: int = 6,
                simulation_date: Optional[datetime] = None
            ):

        self.model, self.client = openai_model_and_client(model=model)

        print(f"Using model: {self.model}")
        print(f"Using client: {self.client}")

        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.reasoning_effort = reasoning_effort
        self.verbose = verbose
        self.plan_first = plan_first  # always plan first
        self.final_keywords = final_keywords or ["Final Answer:", "FINAL ANSWER:"]
        self.save_messages = save_messages
        self.use_episodic_memory = use_episodic_memory
        self.memory_refresh_interval = memory_refresh_interval
        self.simulation_date = simulation_date  # For simulation mode: inject _simulation_date into all tool calls
        self.agent_name = self.__class__.__name__ #this is for logging the agent output 
        self.temperature = temperature
        
        # OpenAI tools and local dispatch map
        self.tools: List[Dict[str, Any]] = []
        self.tool_functions: Dict[str, Callable[..., Any]] = {}

        # Trace and accounting
        self.trace: List[StepTrace] = []
        self.total_tokens: int = 0

        # Token counting cache for performance optimization
        self._cached_token_count: int = 0  # Incremental token count to avoid recounting entire message history

        # Stagnation detection (Phase 3: now handled by StagnationTracker component)
        self._stuck_threshold: int = 4  # Threshold passed to StagnationTracker

        # Initialize argument parser (will be set after tools are registered)
        self._arg_parser: Optional[ToolArgumentParser] = None

        # Create shared output directory for this agent run
        if save_messages:
            self.output_dir = create_agent_output_dir(self.agent_name)
        else:
            self.output_dir = None

        # Initialize helper classes
        self.message_logger = MessageLogger(
            save_messages=save_messages,
            verbose=verbose,
            model_name=self.model,
            agent_name=self.agent_name,
            output_dir=self.output_dir
        )
        
        self.task_manager = TaskManager(
            on_task_progression=None,  # Will wire up after ExecutionEngine created
            verbose=verbose,
            output_dir=self.output_dir
        )
        self.utilities = AgentUtilities(self)

        # Register task management tools after task manager is initialized
        register_task_management_tools(self)

        self.task_validator = TaskValidator(verbose=verbose)

        # Track recent tool executions for validation
        self.recent_tool_executions: List[Dict] = []
        self.recent_observations: List[Any] = []

        # Track consecutive failures to prevent infinite loops
        self.consecutive_failures: Dict[str, int] = {}  # tool_name -> count
        
        # Initialize domain memory (child classes override this)
        self.domain_memory: Optional[DomainMemory] = None
        self._initialize_domain_memory()

        # Initialize episodic memory (blank each session if enabled)
        self.episodic = EpisodicMemory(
            output_dir=self.output_dir,
            reset_on_init=True
        ) if self.use_episodic_memory else None

        # Register built-ins (after episodic is initialized so episodic tools are available)
        register_base_tools(self)
        
        # Initialize planning tool with agent context
        self.planning_tool = PlanningTool(agent=self)
        
        # Initialize execution engine for structured plan execution
        self.execution_engine = PlanExecutor(
            task_store=self.task_manager,  # TaskManager implements TaskStore protocol
            on_task_complete=None,  # Optional callback
            on_task_advance=None,  # Optional callback
            verbose=self.verbose
        )

        # NOTE: Task progression is handled directly in tool_call_handler.py after each tool execution
        # No callback needed here - removed to prevent infinite recursion loop
        # (tool_call_handler calls advance_task_progression() when tasks complete)

        # Initialize extracted components (Phase 3 refactor)
        self.iteration_response_processor = IterationResponseProcessor(self)
        self.stagnation_tracker = StagnationTracker(threshold=self._stuck_threshold)
        self.context_builder = ContextBuilder(self)
        self.agent_execution_loop = AgentExecutionLoop(self)

    def _initialize_domain_memory(self):
        """Initialize domain memory - override in child classes for agent-specific memories."""
        # Base agent doesn't have domain memory by default
        # Child agents should override this to load their specific memories
        pass
    
    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """Return all available tools and their information.

        Returns:
            Dictionary mapping tool names to their definitions including
            description, parameters schema, and required arguments.
        """
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

    def add_tool(self, name: str, description: str, parameters: Dict, function: Callable):
        """Register a new tool for the agent to use.

        Args:
            name: Tool name (used in LLM function calling)
            description: Tool description for LLM context
            parameters: JSON schema defining tool parameters
            function: Callable implementing the tool logic
        """
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

    def _check_for_task_failure(self, tool_name: str, observation: Any) -> None:
        """Check if tool result indicates task failure and handle automatically.

        Args:
            tool_name: Name of the executed tool
            observation: Tool execution result
        """
        if not self.execution_engine.plan_loaded:
            return

        # Check for obvious failure indicators using standardized parser
        failure_indicators = []

        # Parse observation to dict format
        parsed_obs = parse_tool_result(observation, verbose=self.verbose)

        # Check for failure
        if parsed_obs.get('success') is False:
            error_msg = parsed_obs.get('error', 'Unknown error')
            failure_indicators.append(f"Tool {tool_name} returned success=False: {error_msg}")
        
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
    
    def _create_arg_parser(self):
        """Create argument parser with current tool definitions."""
        tool_registry = {}
        for tool in self.tools:
            func_def = tool.get('function', {})
            tool_registry[func_def.get('name')] = func_def
        self._arg_parser = ToolArgumentParser(tool_registry, verbose=self.verbose)

    def _update_token_count(self, new_messages: List[Dict[str, Any]]) -> int:
        """Update token count incrementally by only counting new messages.

        This method implements a performance optimization to avoid recounting
        the entire message history on every iteration. Instead, it:
        1. On first call: counts all messages and caches the result
        2. On subsequent calls: only counts new messages and adds to cache

        Args:
            new_messages: List of new messages to add to token count

        Returns:
            Current total token count

        Note:
            This assumes messages are only appended, never modified or removed.
            If message history is manipulated, call with all messages to reset cache.
        """
        if self._cached_token_count == 0:
            # First time: count everything (includes system + initial messages)
            # This will be called on initialization with the full message list
            self._cached_token_count = get_chat_token_count(new_messages, model=self.model)
        else:
            # Subsequent times: only count NEW messages
            if new_messages:
                new_token_count = get_chat_token_count(new_messages, model=self.model)
                self._cached_token_count += new_token_count

        return self._cached_token_count

    def _print_run_header(self) -> None:
        """Print verbose header at start of agent run."""
        if not self.verbose:
            return

        print("🚀 Starting JSON ReAct run")
        print(f"Query: {self.user_prompt}")
        print("=" * 60)
        if self.save_messages:
            print(f"📝 Saving messages to: {self.message_logger.messages_log_path}")

    # --- Core run loop -----------------------------------------------------
    def run(self) -> Dict[str, Any]:
        """Execute agent run loop (orchestration only).

        This method has been refactored to delegate the main iteration loop
        to AgentExecutionLoop. It only handles:
        - Setup (arg parser, verbose header)
        - Initial message building
        - Delegation to AgentExecutionLoop
        - Return result

        Returns:
            Dict with final_answer, trace, total_tokens, iterations, stop_reason, model
        """
        # Setup: Create argument parser
        if not self._arg_parser:
            self._create_arg_parser()

        # Setup: Print verbose header
        self._print_run_header()

    # --- Set Up -----------------------------------------------------

        # Build initial messages using ContextBuilder (Phase 3 refactor)
        messages = self.context_builder.build_initial_messages(
            system_prompt=self.system_prompt,
            user_prompt=self.user_prompt,
            plan_first=self.plan_first,
            domain_memory=self.domain_memory
        )

        # Save initial messages (after optional plan-first injection to keep logs aligned)
        # Initialize token cache with full message history
        initial_token_count = self._update_token_count(messages)
        self.message_logger.save_messages_to_json(messages, iteration=0, total_tokens=self.total_tokens, input_tokens=initial_token_count)

        # Execute main loop - Delegate to AgentExecutionLoop (Phase 3.4b.2)
        result = self.agent_execution_loop.execute_loop(
            messages=messages,
            tools=self.tools,
            tool_functions=self.tool_functions
        )

        return result

