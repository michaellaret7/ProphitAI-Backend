"""AgentExecutionLoop: Manages the full multi-iteration agent loop.

This module contains the AgentExecutionLoop class responsible for orchestrating
the agent's ReAct iteration loop, coordinating LLM API calls, and delegating
to specialized components for execution, stagnation tracking, and context building.
"""

from typing import TYPE_CHECKING, Dict, List, Any, Optional

if TYPE_CHECKING:
    from ..agent import BaseAgent

from .iteration_response_processor import IterationResponseProcessor, IterationResult


class AgentExecutionLoop:
    """Manages the full multi-iteration agent execution loop.

    This class manages:
    - Iteration loop control (for loop, max iterations)
    - LLM API calls
    - Periodic context/memory injection (using ContextBuilder)
    - Component coordination (IterationResponseProcessor, StagnationTracker)
    - Message list management
    - Token counting and logging
    - Trace management
    - Verbose output coordination
    - Error handling

    Responsibilities:
    - Makes LLM API calls (client.chat.completions.create)
    - Delegates response processing to IterationResponseProcessor
    - Injects periodic context via ContextBuilder
    - Handles stagnation via StagnationTracker
    - Manages messages, tokens, trace, logging
    """

    def __init__(self, agent: 'BaseAgent'):
        """Initialize AgentExecutionLoop with agent reference.

        Args:
            agent: BaseAgent instance providing access to all components
        """
        self.agent = agent
        self.iteration_response_processor = agent.iteration_response_processor
        self.stagnation_tracker = agent.stagnation_tracker
        self.context_builder = agent.context_builder

    def execute_loop(
        self,
        messages: List[Dict],
        tools: List[Dict],
        tool_functions: Dict
    ) -> Dict[str, Any]:
        """Execute main iteration loop with proper delegation.

        This is the core orchestration method that:
        1. Runs the iteration loop (1 to max_iterations)
        2. Makes LLM API calls for each iteration
        3. Delegates response processing to IterationResponseProcessor
        4. Injects periodic context (plan updates, memory refresh)
        5. Handles stagnation detection and recovery
        6. Updates token counts and saves message logs
        7. Manages trace updates
        8. Handles errors gracefully

        Args:
            messages: Message list for LLM conversation
            tools: Tool definitions for LLM function calling
            tool_functions: Mapping of tool names to callable functions

        Returns:
            Final execution result with trace and output:
            {
                "final_answer": str,
                "trace": List[StepTrace],
                "total_tokens": int,
                "iterations": int,
                "stop_reason": str,
                "model": str
            }
        """
        final_text = None
        stop_reason = ""
        previous_message_count = len(messages)

        try:
            for i in range(1, self.agent.max_iterations + 1):
                # Print iteration status if verbose
                if self.agent.verbose:
                    self._print_iteration_status(i)

                # Inject periodic context and memory (every 3 iterations)
                self._inject_periodic_context(messages, i)

                # Update token count for new messages added
                new_messages = messages[previous_message_count:]
                if new_messages:
                    self.agent._update_token_count(new_messages)
                previous_message_count = len(messages)

                try:
                    # Make LLM API call
                    response = self.agent.client.chat.completions.create(
                        model=self.agent.model,
                        messages=messages,
                        tools=tools if tools else None,
                        **({"reasoning_effort": self.agent.reasoning_effort} if getattr(self.agent, "reasoning_effort", None) is not None else {}),
                        **({"temperature": self.agent.temperature} if getattr(self.agent, "temperature", None) is not None else {}),
                    )

                    # Accumulate actual token usage from LLM response
                    self.agent.utilities.accumulate_usage(response)

                    assistant_message = response.choices[0].message
                    assistant_raw = assistant_message.content or ""

                    # Delegate response processing to IterationResponseProcessor
                    result = self.iteration_response_processor.execute_iteration(
                        iteration=i,
                        messages=messages,
                        assistant_message=assistant_message,
                        assistant_raw=assistant_raw,
                        tools=tools,
                        tool_functions=tool_functions
                    )

                    # Update trace with iteration result
                    self._update_trace(result)

                    # Save messages after iteration
                    self.agent.message_logger.save_messages_to_json(
                        messages,
                        iteration=i,
                        total_tokens=self.agent.total_tokens,
                        input_tokens=self.agent._cached_token_count
                    )

                    # Check for finality
                    if result.is_final:
                        final_text = result.final_text
                        stop_reason = result.stop_reason or "final_answer"
                        break

                    # Handle stagnation (if applicable)
                    stagnation_msg = self._handle_stagnation(i, messages)
                    if stagnation_msg:
                        messages.append({"role": "user", "content": stagnation_msg})

                except Exception as e:
                    if self.agent.verbose:
                        print(f"⚠️ Error in iteration {i}: {e}")
                    # Log error but continue to next iteration
                    continue

            # If loop completed without finality
            if not final_text:
                stop_reason = "max_iterations"

        except KeyboardInterrupt:
            if self.agent.verbose:
                print("\n⚠️ Execution interrupted by user")
            stop_reason = "interrupted"

        # Build and return final result
        return self._build_final_result(final_text, stop_reason, i if 'i' in locals() else 0)

    def _inject_periodic_context(self, messages: List[Dict], iteration: int) -> None:
        """Inject periodic plan context and memory refresh using ContextBuilder.

        NO CONFIDENCE SCORING - Uses ContextBuilder which already removed it.

        This method injects:
        1. Plan status updates every 3 iterations (if plan-driven execution active)
        2. Domain memory refresh at configured interval

        Args:
            messages: Message list to append context to
            iteration: Current iteration number
        """
        # Inject plan status update every 3 iterations
        if iteration > 1 and iteration % 3 == 0:
            plan_context = self.context_builder.build_plan_context(iteration)
            if plan_context:
                messages.append({"role": "user", "content": plan_context})

        # Inject memory refresh at configured interval
        memory_msg = self.context_builder.build_memory_refresh(
            iteration,
            self.agent.memory_refresh_interval
        )
        if memory_msg:
            messages.append({"role": "user", "content": memory_msg})

    def _handle_stagnation(self, iteration: int, messages: List[Dict]) -> Optional[str]:
        """Handle stagnation detection and recovery using StagnationTracker.

        Checks if agent is stuck in repetitive behavior and provides recovery guidance.

        Args:
            iteration: Current iteration number
            messages: Message list (for context, not modified here)

        Returns:
            Recovery message to inject, or None if not stagnating
        """
        if self.stagnation_tracker.is_stagnating():
            if self.agent.verbose:
                print(f"\n⚠️ Stagnation detected at iteration {iteration}")
                print(f"   Repeated action count: {self.stagnation_tracker.get_stagnation_count()}")

            # Get context-aware recovery message
            recovery_msg = self.stagnation_tracker.get_recovery_message(
                execution_engine=self.agent.execution_engine,
                recent_observations=self.agent.recent_observations,
                verbose=self.agent.verbose
            )

            # Reset stagnation tracker
            self.stagnation_tracker.reset()

            return recovery_msg

        return None

    def _print_iteration_status(self, iteration: int) -> None:
        """Print verbose iteration status.

        NO CONFIDENCE SCORING in output.

        Shows:
        - Iteration number
        - Current task/subtask (if plan-driven execution active)
        - Plan progress (if applicable)

        Args:
            iteration: Current iteration number
        """
        print(f"\n ⚜️  Iteration {iteration}")

        # Show current task context if plan-driven execution active
        if self.agent.execution_engine.plan_loaded:
            task_context = self.agent.execution_engine.get_current_task_context()
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

    def _update_trace(self, result: IterationResult) -> None:
        """Update agent trace with iteration result.

        Args:
            result: IterationResult containing step trace
        """
        if result.step_trace:
            self.agent.trace.append(result.step_trace)

    def _build_final_result(self, final_text: Optional[str], stop_reason: str, iterations: int) -> Dict[str, Any]:
        """Build final execution result dictionary.

        Args:
            final_text: Final answer text (or None if not reached)
            stop_reason: Reason execution stopped (final_answer, max_iterations, interrupted)
            iterations: Number of iterations completed

        Returns:
            Structured result dictionary
        """
        return {
            "final_answer": final_text or "No final answer reached",
            "trace": self.agent.trace,
            "total_tokens": self.agent.total_tokens,
            "iterations": iterations,
            "stop_reason": stop_reason,
            "model": self.agent.model
        }
