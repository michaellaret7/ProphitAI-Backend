"""Core execution loop for Base Agent V2.

The heart of V2 - orchestrates Think → Act → Observe → Reason cycle.
"""

from typing import Dict, List, Any, Optional
from openai import OpenAI
from .iteration_tracker import IterationTracker
from .tool_handler import ToolHandler
from ..tasks.tracker import LightweightTaskTracker
from ..reasoning.prompts import ReasoningPrompter
from app.utils.choose_model_and_client import openai_model_and_client

class ReasoningExecutionLoop:
    """
    Core execution loop for Base Agent V2.

    Orchestrates:
    - Task context from LightweightTaskTracker
    - Reasoning prompts from ReasoningPrompter
    - LLM calls (OpenAI)
    - Tool execution via ToolHandler
    - Iteration tracking via IterationTracker

    Key V2 features:
    - NO automatic task advancement
    - Explicit reasoning prompts
    - High reasoning density
    - Agent controls progression
    """

    def __init__(
        self,
        agent,
        task_tracker: LightweightTaskTracker,
        max_iterations: int = 100
    ):
        """
        Initialize execution loop.

        Args:
            agent: Reference to AgentV2 instance
            task_tracker: Task tracking system
            max_iterations: Maximum iterations before stopping
        """
        self.agent = agent
        self.task_tracker = task_tracker
        self.iteration_tracker = IterationTracker(max_iterations)
        self.tool_handler = ToolHandler(agent)
        self.reasoning_prompter = ReasoningPrompter()

        # LLM client
        self.model, self.client = openai_model_and_client(self.agent.model)

        # Conversation state
        self.conversation_history: List[Dict[str, Any]] = []
        self.just_started_new_task = True  # Track if just started new task/subtask
        self.recent_tool_results: List[Any] = []  # Track recent tool results for observation prompts
        self.last_iteration_type: Optional[str] = None  # Track last iteration type for TAOAR flow

    def run(self) -> Dict[str, Any]:
        """
        Main execution loop.

        Returns:
            Dict with final_answer, reasoning_density, and stats
        """
        # Initialize conversation with system prompt
        self._initialize_conversation()

        final_answer = None
        current_iteration = 0

        # Main loop
        while self.iteration_tracker.should_continue():
            current_iteration = self.iteration_tracker.current_iteration + 1

            # Display iteration header and current task context
            if self.agent.verbose:
                self._print_iteration_header(current_iteration)

            # Build prompt for this iteration
            iteration_prompt = self._build_iteration_prompt()

            # Add user message to conversation
            self.conversation_history.append({
                "role": "user",
                "content": iteration_prompt
            })

            # Get LLM response. This is the Heart of the Reasoning Execution Loop.
            response = self._get_llm_response()

            # Check if final answer
            if self._is_final_answer(response):
                final_answer = self._extract_final_answer(response)

                # Build final result
                final_result = self._build_final_result(
                    final_answer=final_answer,
                    stop_reason="final_answer"
                )

                # Save final messages (matches V1)
                if self.agent.message_logger:
                    self.agent.message_logger.save_final_json(
                        messages=self.conversation_history,
                        result=final_result
                    )

                # Save final task state (matches V1)
                self._save_task_state()

                return final_result

            # Classify iteration type
            iteration_type = self._classify_iteration(response)

            # Record iteration
            self.iteration_tracker.record_iteration(
                iteration_type=iteration_type,
                content=response.get('content', ''),
                tool_calls=response.get('tool_calls')
            )

            # Track last iteration type for next prompt building
            self.last_iteration_type = iteration_type

            # Handle tool calls if present
            if response.get('tool_calls'):
                # NOTE: tool_handler.execute_tool_calls() already adds assistant message to conversation
                tool_results = self.tool_handler.execute_tool_calls(
                    tool_calls=response['tool_calls'],
                    conversation_history=self.conversation_history
                )

                # Track tool results for next iteration's observation prompt
                self.recent_tool_results = tool_results

                # Check if advancement tool was called
                for result in tool_results:
                    if result.tool_name in ['advance_to_next_subtask', 'advance_to_next_main_task']:
                        # Agent advanced - mark for next iteration
                        self.just_started_new_task = True
                        # Clear tool results since advancing to new phase
                        self.recent_tool_results = []
                        break

                # Record tool usage in task tracker
                self.task_tracker.increment_tool_calls(len(tool_results))

            else:
                # No tool calls - this is a reasoning/thinking/observation iteration
                # CRITICAL: Add assistant message to conversation history
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.get('content', '')
                })

                # Display thinking/observation/reasoning content
                if self.agent.verbose:
                    self._print_reasoning_content(iteration_type, response.get('content', ''))

                # Record reasoning in task tracker if appropriate
                self._record_reasoning_in_tracker(response.get('content', ''), iteration_type)

                # Clear tool results after reasoning iteration (agent has processed them)
                if iteration_type in ["observation", "reasoning"]:
                    self.recent_tool_results = []

            # Save messages after each iteration (matches V1)
            if self.agent.message_logger:
                self.agent.message_logger.save_messages_to_json(
                    messages=self.conversation_history,
                    iteration=current_iteration,
                    total_tokens=None,  # V2 doesn't track tokens (can add later if needed)
                    input_tokens=None
                )

            # Save task state periodically (matches V1)
            if current_iteration % 5 == 0:  # Every 5 iterations
                self._save_task_state()

            # Reset "just started" flag after first iteration of new task
            if self.just_started_new_task and iteration_type == "action":
                self.just_started_new_task = False

        # Max iterations reached
        final_result = self._build_final_result(
            final_answer=None,
            error="Maximum iterations reached without final answer"
        )

        # Save final state (matches V1)
        if self.agent.message_logger:
            self.agent.message_logger.save_final_json(
                messages=self.conversation_history,
                result=final_result
            )
        self._save_task_state()

        return final_result

    def _initialize_conversation(self) -> None:
        """Add system prompt to conversation history."""
        system_prompt = self.agent.system_prompt
        user_prompt = self.agent.user_prompt

        self.conversation_history.append({
            "role": "system",
            "content": system_prompt
        })

        self.conversation_history.append({
            "role": "user",
            "content": user_prompt
        })

    def _build_iteration_prompt(self) -> str:
        """
        Build prompt for current iteration.

        Uses task context and reasoning prompts based on current state.
        Implements Think → Act → Observe → Reason cycle through phase-aware prompting.
        """
        # Get current task context
        task_context = self.task_tracker.get_current_context()

        # Check if plan complete
        if task_context.get('status') == 'completed':
            return self.reasoning_prompter.build_task_context_prompt(task_context)

        # Build phase-aware prompt (TAOAR cycle)
        if self.just_started_new_task:
            # THINK phase - Just started new task/subtask, encourage thinking
            self.just_started_new_task = False  # Reset after showing thinking prompt
            return self.reasoning_prompter.build_comprehensive_iteration_prompt(
                task_context=task_context,
                phase="starting"
            )
        elif self.recent_tool_results:
            # OBSERVE phase - Just executed tools, encourage observation
            num_tools = len(self.recent_tool_results)
            obs_prompt = self.reasoning_prompter.build_observation_prompt(
                tool_results_summary=f"[See {num_tools} tool results above in conversation history]",
                num_tools_called=num_tools
            )
            # Combine task context + observation prompt
            return (self.reasoning_prompter.build_task_context_prompt(task_context) +
                    "\n\n" + obs_prompt)
        elif self.last_iteration_type == "observation":
            # REASON phase - Just made observations, now encourage reasoning and decision
            reasoning_prompt = self.reasoning_prompter.build_reasoning_prompt(has_observations=True)

            # Add advancement reminder if working on subtask
            advancement_reminder = ""
            if task_context.get('current_subtask'):
                advancement_reminder = "\n\n" + self.reasoning_prompter.build_advancement_reminder_prompt("subtask")
            elif task_context.get('current_main_task'):
                advancement_reminder = "\n\n" + self.reasoning_prompter.build_advancement_reminder_prompt("main_task")

            return (self.reasoning_prompter.build_task_context_prompt(task_context) +
                    "\n\n" + reasoning_prompt + advancement_reminder)
        else:
            # General working - show context and let agent continue
            return self.reasoning_prompter.build_task_context_prompt(task_context)

    def _get_llm_response(self) -> Dict[str, Any]:
        """
        Get response from LLM using agent's client.

        Returns:
            Dict with 'content' and optional 'tool_calls'
        """
        try:
            # Get tool schemas
            tools = self._get_tool_schemas() if hasattr(self.agent, 'tool_schemas') and self.agent.tool_schemas else None

            # Build optional parameters
            optional_params = {}
            if getattr(self.agent, "reasoning_effort", None) is not None:
                optional_params["reasoning_effort"] = self.agent.reasoning_effort
            if getattr(self.agent, "temperature", None) is not None:
                optional_params["temperature"] = self.agent.temperature

            # Call LLM via agent's client
            completion = self.agent.client.chat.completions.create(
                model=self.agent.model,
                messages=self.conversation_history,
                tools=tools,
                **optional_params
            )

            message = completion.choices[0].message

            return {
                "content": message.content or "",
                "tool_calls": message.tool_calls if message.tool_calls else None
            }

        except Exception as e:
            # LLM call failed
            return {
                "content": f"Error: LLM call failed - {e}",
                "tool_calls": None,
                "error": str(e)
            }

    def _classify_iteration(self, response: Dict[str, Any]) -> str:
        """
        Classify iteration type based on response.

        Returns:
            "thinking", "action", "observation", "reasoning", or "general"
        """
        # If has tool calls, it's an action
        if response.get('tool_calls'):
            return "action"

        # Check content for keywords
        content = response.get('content', '').lower()

        # Heuristic classification (can be improved)
        if any(keyword in content for keyword in ['thinking', 'approach', 'plan', 'strategy', 'will use']):
            return "thinking"
        elif any(keyword in content for keyword in ['observe', 'found', 'data shows', 'results show', 'pattern']):
            return "observation"
        elif any(keyword in content for keyword in ['reasoning', 'because', 'therefore', 'this means', 'based on']):
            return "reasoning"
        else:
            return "general"

    def _record_reasoning_in_tracker(self, content: str, iteration_type: str) -> None:
        """
        Record agent's reasoning in task tracker.

        Args:
            content: Agent's response content
            iteration_type: Type of iteration (thinking/observation/reasoning)
        """
        if not content:
            return

        if iteration_type == "thinking":
            self.task_tracker.record_thinking(content)
        elif iteration_type == "observation":
            self.task_tracker.record_observation(content)
        elif iteration_type == "reasoning":
            self.task_tracker.record_reasoning(content)

    def _is_final_answer(self, response: Dict[str, Any]) -> bool:
        """
        Check if response contains final answer.

        Now case-insensitive and punctuation-flexible to catch:
        - "Final Answer:" or "Final answer:" or "FINAL ANSWER:"
        - "Final answer —" (with em dash)
        - "Final answer -" (with hyphen)

        Args:
            response: LLM response

        Returns:
            True if contains final answer marker
        """
        content = response.get('content', '').strip()
        if not content:
            return False

        # Case-insensitive check - look at first 100 chars
        content_lower = content.lower()
        first_part = content_lower[:100]

        # Check for "final answer" followed by common punctuation
        return (
            first_part.startswith('final answer') or
            'final answer:' in first_part or
            'final answer —' in first_part or
            'final answer-' in first_part or
            'final answer–' in first_part  # en dash
        )

    def _extract_final_answer(self, response: Dict[str, Any]) -> str:
        """
        Extract final answer from response.

        Case-insensitive extraction that handles various punctuation.

        Args:
            response: LLM response with final answer

        Returns:
            Final answer string (everything after "final answer" marker)
        """
        content = response.get('content', '').strip()
        content_lower = content.lower()

        # Find "final answer" marker (case-insensitive)
        if 'final answer' in content_lower:
            # Find the actual position in original content
            marker_pos = content_lower.index('final answer')

            # Skip past "final answer" text
            start_pos = marker_pos + len('final answer')

            # Skip any following punctuation and whitespace (:, —, -, –, etc.)
            while start_pos < len(content) and content[start_pos] in ':—-–— \t\n':
                start_pos += 1

            return content[start_pos:].strip()

        # Fallback: return full content if no marker found
        return content

    def _build_final_result(self, final_answer: Optional[str], error: Optional[str] = None, stop_reason: str = "final_answer") -> Dict[str, Any]:
        """
        Build final result dict.

        Args:
            final_answer: The final answer (if any)
            error: Error message (if any)
            stop_reason: Reason execution stopped (final_answer/max_iterations)

        Returns:
            Dict with result, stats, and analytics
        """
        summary = self.iteration_tracker.get_summary()

        result = {
            "success": final_answer is not None,
            "final_answer": final_answer,
            "final_text": final_answer,  # V1 MessageLogger expects this key
            "iterations": summary['total_iterations'],
            "stopped_reason": stop_reason,  # V1 MessageLogger expects this key
            "reasoning_density": summary['reasoning_density'],
            "reasoning_density_percentage": summary['reasoning_density_percentage'],
            "breakdown": summary['breakdown'],
            "task_state": self.task_tracker.get_task_state_for_persistence()
        }

        if error:
            result["error"] = error

        return result

    def _get_tool_schemas(self) -> List[Dict]:
        """
        Get tool schemas for LLM function calling.

        Returns:
            List of tool schemas
        """
        if hasattr(self.agent, 'tool_schemas'):
            return self.agent.tool_schemas
        return []

    def _save_task_state(self) -> None:
        """
        Save task state to task_state.json (matches V1 format).

        Saves:
        - Current timestamp
        - Structured plan (TodoList)
        - Execution history (not used in V2 but kept for format compatibility)
        """
        if not self.agent.output_dir:
            return

        import json
        from datetime import datetime

        # Get task state from tracker
        task_state = self.task_tracker.get_task_state_for_persistence()

        # Build state data in V1 format
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'structured_plan': task_state['todo_list'],  # TodoList as dict
            'execution_history': []  # V2 doesn't use this but keep for format compatibility
        }

        # Save to task_state.json
        state_path = self.agent.output_dir / "task_state.json"
        try:
            with open(state_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.agent.verbose:
                print(f"Warning: Failed to save task state: {e}")

    def _print_iteration_header(self, iteration: int) -> None:
        """
        Print iteration header with current task context.

        Args:
            iteration: Current iteration number
        """
        # Get current task context
        task_context = self.task_tracker.get_current_context()

        print(f"\n{'═' * 80}")
        print(f"ITERATION {iteration}")
        print(f"{'═' * 80}")

        # Display current task
        current_main = task_context.get('current_main_task')
        if current_main:
            print(f"📋 Main Task {current_main['id']}: {current_main['description']}")

            # Display current subtask
            current_sub = task_context.get('current_subtask')
            if current_sub:
                print(f"   └─ Subtask {current_sub['id']}: {current_sub['description']}")

        # Check if plan is complete
        if task_context.get('status') == 'completed':
            print(f"✓ All tasks completed - ready for final answer")

        print(f"{'─' * 80}")

    def _print_reasoning_content(self, iteration_type: str, content: str) -> None:
        """
        Print thinking/observation/reasoning content.

        Args:
            iteration_type: Type of iteration (thinking/observation/reasoning)
            content: Content to display
        """
        # Map iteration type to display info
        type_map = {
            "thinking": "💭 THINKING",
            "observation": "👁️  OBSERVATION",
            "reasoning": "🧠 REASONING",
            "general": "💬 RESPONSE"
        }

        header = type_map.get(iteration_type, "💬 RESPONSE")

        # Use lighter formatting (not heavy lines like iterations)
        print(f"\n{header}")
        print(f"{'~' * 80}")

        # Show full content, no truncation
        print(content)

        print(f"{'~' * 80}")