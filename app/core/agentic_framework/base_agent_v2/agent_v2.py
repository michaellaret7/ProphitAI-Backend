"""Base Agent V2 - Autonomous reasoning agent with analytical guardrails.

Main agent class that orchestrates all V2 components.
"""

from typing import Dict, List, Optional, Any
from pathlib import Path
from datetime import datetime

# V2 components
from .memory.domain_memory import DomainMemory
from .memory.episodic_memory import EpisodicMemory
from .tasks.tracker import LightweightTaskTracker
from .tasks.models import TodoList
from .execution.reasoning_loop import ReasoningExecutionLoop
from .tool_registry.registry import register_base_tools
from .core.logger import MessageLogger

# Utilities
from app.utils.choose_model_and_client import openai_model_and_client
from .utils.path_utils import create_agent_output_dir

# Planning tool
from app.core.agentic_framework.tool_lib.base_tools.planning_tool import PlanningTool


class BaseAgentV2:
    """
    Base Agent V2 - Autonomous reasoning agent with analytical guardrails.

    Key features:
    - Comprehensive analytical structure (prevents analysis gaps)
    - Agent-controlled task progression (NO automatic advancement)
    - High reasoning density (30-40% target)
    - Think → Act → Observe → Reason cycle
    - Structured analytical guardrails with execution autonomy

    Philosophy:
    - Tasks as analytical objectives (WHAT to analyze, not HOW)
    - Subtasks as systematic checkpoints (ensure comprehensive coverage)
    - Agent decides tool usage, approach, and when to advance
    - More structure is good when it's analytical structure (not meta-work)
    """

    def __init__(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        model: str = None,
        reasoning_effort: str = None,
        temperature: float = None,
        max_iterations: int = 75,
        verbose: bool = True,
        plan_first: bool = True,  # Always True in V2
        final_keywords: Optional[List[str]] = None,
        save_messages: bool = True,
        use_episodic_memory: bool = True,
        memory_refresh_interval: int = 6,  # Not used in V2 but kept for API compatibility
        simulation_date: Optional[datetime] = None
    ):
        """
        Initialize Base Agent V2.

        Args:
            system_prompt: System prompt with agent role and context
            user_prompt: User's request/query
            model: LLM model to use (default determined by choose_model_and_client)
            reasoning_effort: Reasoning effort for extended thinking models (low/medium/high)
            temperature: Temperature override
            max_iterations: Maximum iterations before stopping
            verbose: Whether to print progress
            plan_first: Always True in V2 (comprehensive planning required)
            final_keywords: Keywords indicating final answer
            save_messages: Whether to save execution artifacts
            use_episodic_memory: Whether to use episodic memory
            memory_refresh_interval: Not used in V2 (kept for API compatibility)
            simulation_date: For simulation mode (inject into tool calls)
        """
        # Select model and client (matches V1 behavior)
        self.model, self.client = openai_model_and_client(model=model)

        if verbose:
            print(f"Using model: {self.model}")
            print(f"Using client: {self.client}")

        # Core configuration
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.max_iterations = max_iterations
        self.reasoning_effort = reasoning_effort
        self.temperature = temperature
        self.verbose = verbose
        self.plan_first = plan_first  # Always True in V2
        self.final_keywords = final_keywords or ["Final Answer:", "FINAL ANSWER:"]
        self.save_messages = save_messages
        self.use_episodic_memory = use_episodic_memory
        self.memory_refresh_interval = memory_refresh_interval  # Not used in V2
        self.simulation_date = simulation_date
        self.agent_name = self.__class__.__name__

        # Set up output directory using V1 utility
        if save_messages:
            self.output_dir = create_agent_output_dir(self.agent_name)
        else:
            self.output_dir = None

        # Initialize episodic memory if enabled
        if use_episodic_memory and self.output_dir:
            self.episodic = EpisodicMemory(
                output_dir=self.output_dir,
                reset_on_init=True
            )
        else:
            self.episodic = None

        # Initialize message logger
        self.message_logger = MessageLogger(
            save_messages=save_messages,
            verbose=verbose,
            model_name=self.model,
            agent_name=self.agent_name,
            output_dir=self.output_dir
        ) if save_messages else None

        # Initialize domain memory (child classes override this)
        self.domain_memory: Optional[DomainMemory] = None
        self._initialize_domain_memory()

        # Tool registry (will be populated during run)
        self.tools: Dict[str, Any] = {}
        self.tool_schemas: List[Dict] = []

        # Token tracking (matches V1)
        self.total_tokens: int = 0
        self._cached_token_count: int = 0  # Incremental token count for performance

        # Planning tool
        self.planning_tool = PlanningTool(agent=self)

        # Task management (initialized during run)
        self.task_tracker: Optional[LightweightTaskTracker] = None
        self.todo_list: Optional[TodoList] = None

        # Execution loop (initialized during run)
        self.execution_loop: Optional[ReasoningExecutionLoop] = None

    def _initialize_domain_memory(self) -> None:
        """
        Initialize domain memory.

        Override in subclasses to load domain-specific knowledge.
        """
        pass

    def run(self) -> Dict[str, Any]:
        """
        Main entry point to run agent.

        Steps:
        1. Register base tools
        2. Create comprehensive plan using planning tool
        3. Initialize task tracker
        4. Register task control tools
        5. Run execution loop
        6. Save outputs
        7. Return final answer with analytics

        Returns:
            Dict with final_answer, reasoning_density, iterations, task_state
        """
        if self.verbose:
            print(f"\n{'='*80}")
            print(f"  Running {self.__class__.__name__} (Base Agent V2)")
            print(f"{'='*80}\n")

        # Step 1: Register base tools
        if self.verbose:
            print("Step 1: Registering base tools...")
        self._register_base_tools()

        # Step 2: Create plan
        if self.verbose:
            print("Step 2: Creating comprehensive structured plan...")
        self.todo_list = self._create_plan()

        if self.verbose:
            print(f"  Plan created: {len(self.todo_list.tasks)} main tasks")
            for task in self.todo_list.tasks:
                subtask_info = f" ({len(task.subtasks)} subtasks)" if task.subtasks else ""
                print(f"    - Task {task.id}: {task.description}{subtask_info}")

        # Step 3: Initialize task tracker
        if self.verbose:
            print("\nStep 3: Initializing task tracker...")
        self.task_tracker = LightweightTaskTracker(self.todo_list)

        # Step 3a: Save initial plan to task_state.json
        if self.save_messages:
            self._save_initial_plan()
            if self.verbose:
                print("  Saved initial plan to task_state.json")

        # Step 4: Register task control tools
        if self.verbose:
            print("Step 4: Registering task control tools...")
        self._register_task_control_tools()

        # Step 5: Run execution loop
        if self.verbose:
            print(f"\nStep 5: Starting execution loop (max {self.max_iterations} iterations)...")
            print(f"{'='*80}\n")

        self.execution_loop = ReasoningExecutionLoop(
            agent=self,
            task_tracker=self.task_tracker,
            max_iterations=self.max_iterations
        )

        result = self.execution_loop.run()

        # Step 6: Save outputs
        if self.save_messages:
            if self.verbose:
                print(f"\n{'='*80}")
                print("Step 6: Saving execution artifacts...")
            self._save_execution_artifacts(result)

        # Step 7: Print summary
        if self.verbose:
            self._print_execution_summary(result)

        return result

    def _register_base_tools(self) -> None:
        """Register base tools available to all agents."""
        register_base_tools(self)

        if self.verbose:
            print(f"  Registered {len(self.tools)} base tools")

    def _create_plan(self) -> TodoList:
        """
        Create comprehensive structured plan using planning tool.

        Returns:
            TodoList with main tasks and subtasks
        """
        # Planning tool uses agent context to create plan
        plan_result = self.planning_tool.create_plan_from_agent()

        if not plan_result.get('success'):
            raise Exception(f"Planning failed: {plan_result.get('error')}")

        # Parse TodoList from plan
        todo_list = TodoList.model_validate(plan_result['plan'])
        return todo_list

    def _register_task_control_tools(self) -> None:
        """Register V2 task control tools after task tracker initialized."""
        # Import here to avoid circular dependency
        from .tasks.tools import (
            get_current_task_info,
            advance_to_next_subtask,
            advance_to_next_main_task,
            GET_CURRENT_TASK_INFO_SCHEMA,
            ADVANCE_SUBTASK_SCHEMA,
            ADVANCE_MAIN_TASK_SCHEMA
        )

        # Register get_current_task_info
        self.add_tool(
            name="get_current_task_info",
            description=GET_CURRENT_TASK_INFO_SCHEMA['function']['description'],
            parameters=GET_CURRENT_TASK_INFO_SCHEMA['function']['parameters'],
            function=lambda **kwargs: get_current_task_info(self.task_tracker)
        )

        # Register advance_to_next_subtask
        self.add_tool(
            name="advance_to_next_subtask",
            description=ADVANCE_SUBTASK_SCHEMA['function']['description'],
            parameters=ADVANCE_SUBTASK_SCHEMA['function']['parameters'],
            function=lambda **kwargs: advance_to_next_subtask(self.task_tracker, **kwargs)
        )

        # Register advance_to_next_main_task
        self.add_tool(
            name="advance_to_next_main_task",
            description=ADVANCE_MAIN_TASK_SCHEMA['function']['description'],
            parameters=ADVANCE_MAIN_TASK_SCHEMA['function']['parameters'],
            function=lambda **kwargs: advance_to_next_main_task(self.task_tracker, **kwargs)
        )

        if self.verbose:
            print(f"  Registered 3 task control tools")
            print(f"  Total tools: {len(self.tools)}")

    def add_tool(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Any
    ) -> None:
        """
        Register a tool.

        Args:
            name: Tool name
            description: Tool description
            parameters: OpenAI function calling parameters schema
            function: Callable to execute
        """
        # Add to tools dict
        self.tools[name] = function

        # Add schema for LLM function calling
        schema = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        }
        self.tool_schemas.append(schema)

    def get_available_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all available tools with their schemas.

        Used by planning tool to understand what tools agent has.

        Returns:
            Dict mapping tool names to schema info
        """
        tools_info = {}
        for schema in self.tool_schemas:
            func_schema = schema['function']
            tools_info[func_schema['name']] = {
                'description': func_schema['description'],
                'parameters': func_schema['parameters'],
                'required': func_schema['parameters'].get('required', [])
            }
        return tools_info

    def _save_execution_artifacts(self, result: Dict[str, Any]) -> None:
        """
        Save execution artifacts to disk.

        Args:
            result: Execution result with task_state
        """
        if not self.output_dir:
            return

        import json

        # Save task state with reasoning data
        task_state = result.get('task_state', {})
        task_state_path = self.output_dir / "task_state.json"
        with open(task_state_path, 'w') as f:
            json.dump(task_state, f, indent=2)

        if self.verbose:
            print(f"  Saved task state: {task_state_path}")

        # Save execution summary
        summary = {
            "success": result.get('success'),
            "iterations": result.get('iterations'),
            "reasoning_density": result.get('reasoning_density'),
            "reasoning_density_percentage": result.get('reasoning_density_percentage'),
            "breakdown": result.get('breakdown'),
            "final_answer_provided": result.get('final_answer') is not None
        }
        summary_path = self.output_dir / "execution_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)

        if self.verbose:
            print(f"  Saved execution summary: {summary_path}")

    def _print_execution_summary(self, result: Dict[str, Any]) -> None:
        """Print execution summary."""
        print(f"\n{'='*80}")
        print("  EXECUTION COMPLETE")
        print(f"{'='*80}\n")

        print(f"Success: {result.get('success')}")
        print(f"Iterations: {result.get('iterations')}")
        print(f"Reasoning Density: {result.get('reasoning_density_percentage')}%")
        print(f"Target: 30-40%")

        breakdown = result.get('breakdown', {})
        print(f"\nIteration Breakdown:")
        print(f"  - Thinking: {breakdown.get('thinking', 0)}")
        print(f"  - Action (tools): {breakdown.get('action', 0)}")
        print(f"  - Observation: {breakdown.get('observation', 0)}")
        print(f"  - Reasoning: {breakdown.get('reasoning', 0)}")

        if result.get('final_answer'):
            print(f"\nFinal Answer Provided: YES")
        else:
            print(f"\nFinal Answer Provided: NO")
            if result.get('error'):
                print(f"Error: {result.get('error')}")

        if self.output_dir:
            print(f"\nOutputs saved to: {self.output_dir}")

        print(f"\n{'='*80}\n")

    def _save_initial_plan(self) -> None:
        """
        Save the initial plan to task_state.json immediately after creation.

        This allows users to see the plan before execution starts.
        """
        if not self.output_dir:
            return

        import json
        from datetime import datetime

        # Get initial task state from tracker
        task_state = self.task_tracker.get_task_state_for_persistence()

        # Build initial state data
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'structured_plan': task_state['todo_list'],  # TodoList as dict
            'execution_history': [],
            'status': 'plan_created'
        }

        # Save to task_state.json
        state_path = self.output_dir / "task_state.json"
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"Warning: Failed to save initial plan: {e}")

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
        from app.utils.token_count import get_chat_token_count

        if self._cached_token_count == 0:
            # First time: count everything (includes system + initial messages)
            self._cached_token_count = get_chat_token_count(new_messages, model=self.model)
        else:
            # Subsequent times: only count NEW messages
            if new_messages:
                new_token_count = get_chat_token_count(new_messages, model=self.model)
                self._cached_token_count += new_token_count

        self.total_tokens = self._cached_token_count
        return self._cached_token_count