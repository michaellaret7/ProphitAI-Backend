"""Plan Execution Engine for driving task execution based on structured plans."""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from ..events.manager import EventManager, AgentEvent
from .validator import TaskValidator
from .manager import TaskManager
from .models import TodoList, MainTask, SubTask, TaskStatus


class PlanExecutionEngine:
    """Drives task execution based on structured plans."""
    
    def __init__(self, task_manager: TaskManager, event_manager: EventManager, verbose: bool = True):
        """Initialize the execution engine.
        
        Args:
            task_manager: The task manager instance
            event_manager: The event manager for emitting task events
            verbose: Whether to print execution messages
        """
        self.task_manager = task_manager
        self.event_manager = event_manager
        self.verbose = verbose
        self.current_main_task: Optional[MainTask] = None
        self.current_subtask: Optional[SubTask] = None
        self.plan_loaded: bool = False
        
        # Set back-reference so task manager can trigger advancement
        self.task_manager.execution_engine = self
        
        # Initialize task validator for intelligent completion detection
        self.task_validator = TaskValidator(verbose=verbose)
    
    def load_plan(self, plan: TodoList) -> bool:
        """Load a structured plan into the execution engine.
        
        Args:
            plan: The TodoList to execute
            
        Returns:
            True if plan loaded successfully
        """
        try:
            # CRITICAL: Reset all task completion states to ensure fresh execution
            # This prevents the circular validation bug where pre-marked tasks skip execution
            for task in plan.tasks:
                task.status = TaskStatus.PENDING
                task.completion_evidence = []
                task.observations = []
                for subtask in task.subtasks:
                    subtask.completed = False
                    subtask.completion_evidence = []
                    subtask.observations = []
            
            # Store the plan in task manager
            self.task_manager.add_structured_plan(plan)
            
            # Initialize first task if available
            if plan.tasks:
                # Set first main task as current using TaskManager
                self.current_main_task = plan.tasks[0]
                self.task_manager.update_main_task_status(
                    self.current_main_task.id, 
                    TaskStatus.IN_PROGRESS,
                    "Plan execution started"
                )
                
                # Set first subtask if available
                if self.current_main_task.subtasks:
                    self.current_subtask = self.current_main_task.subtasks[0]
                    # Ensure subtask starts as not completed
                    self.task_manager.update_subtask_status(
                        self.current_main_task.id,
                        self.current_subtask.id,
                        False,
                        "Subtask initialized"
                    )
                
                self.plan_loaded = True
                
                if self.verbose:
                    print(f"📋 Execution Engine loaded plan with {len(plan.tasks)} main tasks")
                    print(f"▶️ Starting with Task {self.current_main_task.id}: {self.current_main_task.description}")
                    if self.current_subtask:
                        print(f"  → SubTask {self.current_subtask.id}: {self.current_subtask.description}")
                
                # Emit plan loaded event
                self.event_manager.emit(AgentEvent.PLAN_CREATED, {
                    'task_count': len(plan.tasks),
                    'structured_plan': True,
                    'execution_ready': True
                })
                
                return True
            else:
                if self.verbose:
                    print("⚠️ Plan has no tasks to execute")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"❌ Failed to load plan: {e}")
            return False
    
    def get_current_task(self) -> Optional[MainTask]:
        """Get the current main task being executed.
        
        Returns:
            The current MainTask or None if no plan loaded
        """
        if not self.plan_loaded:
            return None
        return self.current_main_task
    
    def get_current_subtask(self) -> Optional[SubTask]:
        """Get the current subtask being executed.
        
        Returns:
            The current SubTask or None if no subtask active
        """
        if not self.plan_loaded:
            return None
        return self.current_subtask
    
    def get_current_task_context(self) -> Dict[str, Any]:
        """Get context about the current task for agent prompting.
        
        Returns:
            Dictionary with current task information
        """
        if not self.plan_loaded or not self.current_main_task:
            return {"status": "no_plan"}
        
        context = {
            "status": "executing",
            "main_task": {
                "id": self.current_main_task.id,
                "description": self.current_main_task.description,
                "status": self.current_main_task.status.value,
                "predicted_tools": self.current_main_task.predicted_tool_use
            }
        }
        
        if self.current_subtask:
            context["subtask"] = {
                "id": self.current_subtask.id,
                "description": self.current_subtask.description,
                "completed": self.current_subtask.completed
            }
        
        # Add progress information
        plan = self.task_manager.get_current_structured_plan()
        if plan:
            completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
            total_main = len(plan.tasks)
            context["progress"] = {
                "main_tasks_completed": completed_main,
                "main_tasks_total": total_main,
                "percentage": int((completed_main / total_main) * 100) if total_main > 0 else 0
            }
        
        return context
    
    def advance_task_progression(self) -> Tuple[bool, str]:
        """Move to next subtask or main task.
        
        Returns:
            Tuple of (success, message) indicating what happened
        """
        if not self.plan_loaded:
            return False, "No plan loaded"
        
        plan = self.task_manager.get_current_structured_plan()
        if not plan:
            return False, "No structured plan available"
        
        # If we have a current subtask, try to advance to next subtask
        if self.current_subtask and self.current_main_task:
            current_subtask_idx = -1
            for i, st in enumerate(self.current_main_task.subtasks):
                if st.id == self.current_subtask.id:
                    current_subtask_idx = i
                    break
            
            # Check if there's a next subtask
            if current_subtask_idx >= 0 and current_subtask_idx < len(self.current_main_task.subtasks) - 1:
                # Mark current subtask as completed using TaskManager
                self.task_manager.update_subtask_status(
                    self.current_main_task.id,
                    self.current_subtask.id,
                    True,
                    "Auto-completed via task progression"
                )
                
                # Move to next subtask
                self.current_subtask = self.current_main_task.subtasks[current_subtask_idx + 1]
                
                if self.verbose:
                    print(f"  ✅ Completed SubTask {self.current_main_task.subtasks[current_subtask_idx].id}")
                    print(f"  → Moving to SubTask {self.current_subtask.id}: {self.current_subtask.description}")
                
                return True, f"Advanced to subtask {self.current_subtask.id}"
            else:
                # No more subtasks, complete main task
                if self.current_subtask:
                    self.task_manager.update_subtask_status(
                        self.current_main_task.id,
                        self.current_subtask.id,
                        True,
                        "Final subtask completed"
                    )
                
                # Complete main task using TaskManager
                self.task_manager.update_main_task_status(
                    self.current_main_task.id,
                    TaskStatus.COMPLETED,
                    "All subtasks completed"
                )
                
                # Try to advance to next main task
                return self._advance_to_next_main_task()
        
        # No subtask, try to advance main task
        if self.current_main_task:
            self.task_manager.update_main_task_status(
                self.current_main_task.id,
                TaskStatus.COMPLETED,
                "Task completed without subtasks"
            )
            return self._advance_to_next_main_task()
        
        return False, "No current task to advance"
    
    def _advance_to_next_main_task(self) -> Tuple[bool, str]:
        """Advance to the next available main task in the plan based on dependencies.
        
        Returns:
            Tuple of (success, message)
        """
        plan = self.task_manager.get_current_structured_plan()
        if not plan or not self.current_main_task:
            return False, "No plan or current task"
        
        # Mark current task as completed using TaskManager
        completed_task_id = self.current_main_task.id
        self.task_manager.update_main_task_status(
            completed_task_id,
            TaskStatus.COMPLETED,
            "Advanced to next main task"
        )
        
        if self.verbose:
            print(f"✅ Completed Task {completed_task_id}: {self.current_main_task.description}")
        
        # Emit task completion event
        self.event_manager.emit(AgentEvent.TASK_COMPLETED, {
            'task_id': completed_task_id,
            'completed': True
        })
        
        # Find next available task based on dependencies
        next_task = self.get_next_available_task()
        
        if next_task:
            # Move to next available task
            self.current_main_task = next_task
            self.task_manager.update_main_task_status(
                self.current_main_task.id,
                TaskStatus.IN_PROGRESS,
                "Started next available task"
            )
            
            # Set first subtask if available
            if self.current_main_task.subtasks:
                self.current_subtask = self.current_main_task.subtasks[0]
                # Initialize first subtask
                self.task_manager.update_subtask_status(
                    self.current_main_task.id,
                    self.current_subtask.id,
                    False,
                    "Subtask activated"
                )
            else:
                self.current_subtask = None
            
            if self.verbose:
                print(f"▶️ Starting Task {self.current_main_task.id}: {self.current_main_task.description}")
                if self.current_subtask:
                    print(f"  → SubTask {self.current_subtask.id}: {self.current_subtask.description}")
            
            # Emit task start event
            self.event_manager.emit(AgentEvent.TASK_STARTED, {
                'task_id': self.current_main_task.id,
                'description': self.current_main_task.description
            })
            
            return True, f"Advanced to main task {self.current_main_task.id}"
        else:
            # Check if all tasks are complete or if some are blocked
            pending_tasks = [t for t in plan.tasks if t.status == TaskStatus.PENDING]
            blocked_tasks = [t for t in plan.tasks if t.status == TaskStatus.BLOCKED]
            
            if blocked_tasks and not pending_tasks:
                # All remaining tasks are blocked
                if self.verbose:
                    print(f"⚠️ All remaining tasks are blocked by dependencies")
                    for task in blocked_tasks:
                        print(f"  - Task {task.id}: {task.description}")
                
                return False, f"All remaining {len(blocked_tasks)} tasks are blocked by dependencies"
            
            elif not pending_tasks and not blocked_tasks:
                # All tasks completed
                self.current_main_task = None
                self.current_subtask = None
                
                if self.verbose:
                    print("🎉 All tasks in plan completed!")
                
                # Emit plan completion event
                self.event_manager.emit(AgentEvent.PLAN_COMPLETED, {
                    'total_tasks': len(plan.tasks)
                })
                
                return True, "Plan execution completed"
            
            else:
                # This shouldn't happen but handle gracefully
                return False, "No next task available but plan not complete"
    
    def update_task_from_tool_result(self, tool_name: str, result: Any) -> bool:
        """Update task progress based on tool execution result.
        
        Args:
            tool_name: Name of the tool that was executed
            result: Result from the tool execution
            
        Returns:
            True if task was updated based on the result
        """
        # Early return if no current task (plan already completed)
        if self.current_main_task is None:
            if self.verbose:
                print("Tool result received after plan completion - ignoring")
            return False
        
        # if the plan auto-advances during this method.
        active_task_id = self.current_main_task.id
        active_subtask_id = self.current_subtask.id if self.current_subtask else None
        predicted_tools = list(self.current_main_task.predicted_tool_use or [])

        # Add tool result to observations using TaskManager
        observation = f"Tool '{tool_name}' returned: {str(result)[:200]}"

        # Always add observation to main task
        self.task_manager.add_task_observation(
            active_task_id,
            observation
        )

        # Determine relevance and success (always strict)
        is_relevant = self._is_tool_relevant(tool_name, self.current_main_task, self.current_subtask)
        is_error = self._is_error_result(result)

        if self.current_subtask and is_relevant:
            # Add observation to subtask only when relevant
            self.task_manager.add_task_observation(
                active_task_id,
                observation,
                active_subtask_id
            )

            # Collect evidence respecting error-awareness
            evidence_items = self.collect_evidence_from_tool_result(tool_name, result)
            for evidence in evidence_items:
                self.task_manager.add_task_evidence(
                    self.current_main_task.id,
                    evidence,
                    self.current_subtask.id
                )
        
        # Check if this tool was predicted for this task and assess completion
        task_completion_triggered = False
        if tool_name in predicted_tools:
            if self.verbose:
                print(f"  📊 Tool '{tool_name}' execution recorded for predicted task tool")
            
            # Check if this completes the current subtask
            if self.current_subtask:
                # Simple heuristic: if tool was predicted and executed successfully, subtask may be complete
                if not isinstance(result, Exception) and result is not None:
                    # Check if we should auto-advance subtask
                    if self._should_auto_advance_subtask(tool_name, result):
                        success, message = self.advance_task_progression()
                        if success and self.verbose:
                            print(f"  🚀 Auto-advanced: {message}")
                        task_completion_triggered = True
        
        # Add completion evidence to appropriate level (avoid duplicating on main if attached to subtask)
        evidence_items = self.collect_evidence_from_tool_result(tool_name, result)
        if self.current_subtask and is_relevant:
            # Evidence already attached to subtask above; skip duplicating on main task
            pass
        else:
            for evidence in evidence_items:
                # Avoid adding misleading success evidence at main-task level when error occurred
                if self._looks_like_success_evidence(evidence) and is_error:
                    continue
                self.task_manager.add_task_evidence(
                    active_task_id,
                    evidence
                )
        
        # State is already saved by TaskManager methods
        
        return True
    
    def _should_auto_advance_subtask(self, tool_name: str, result: Any) -> bool:
        """Determine if subtask should be auto-advanced based on intelligent validation.
        
        Args:
            tool_name: Name of the executed tool
            result: Result from tool execution
            
        Returns:
            True if subtask should be advanced
        """
        if not self.current_subtask:
            return False
        
        # Use TaskValidator for intelligent completion analysis
        should_complete, confidence, reason = self.task_validator.validate_tool_result_for_completion(
            tool_name=tool_name,
            tool_result=result,
            current_task=self.current_main_task,
            current_subtask=self.current_subtask
        )
        
        if self.verbose and should_complete:
            print(f"  🔍 Intelligent validation suggests subtask completion: {reason}")
        
        # Also check the subtask itself for completion
        subtask_complete, subtask_confidence, subtask_reason = self.task_validator.validate_subtask_completion(
            self.current_subtask,
            self.current_main_task
        )
        
        # Require relevance, success, and explicit tool-named evidence (always strict)
        is_relevant = self._is_tool_relevant(tool_name, self.current_main_task, self.current_subtask)
        is_error = self._is_error_result(result)
        has_tool_named_evidence = self._subtask_has_tool_named_evidence(self.current_subtask, tool_name)
        if not (is_relevant and not is_error and has_tool_named_evidence):
            return False

        # Auto-advance if either validator suggests completion with high confidence
        return (should_complete and confidence >= 0.6) or (subtask_complete and subtask_confidence >= 0.7)
    
    def check_task_completion_conditions(self) -> Tuple[bool, str]:
        """Check if current task should be marked as completed based on intelligent validation.
        
        Returns:
            Tuple of (should_complete, reason)
        """
        if not self.current_main_task:
            return False, "No current task"
        
        # Use TaskValidator for intelligent completion detection
        
        # First check current subtask if active
        if self.current_subtask:
            is_complete, confidence, explanation = self.task_validator.validate_subtask_completion(
                self.current_subtask, 
                self.current_main_task
            )
            
            if is_complete:
                return True, f"SubTask completion detected: {explanation} (confidence: {confidence:.2f})"
            
            # If subtask not complete but has high confidence, consider it close
            if confidence >= 0.6:
                return False, f"SubTask near completion: {explanation} (confidence: {confidence:.2f})"
        
        # Check main task completion
        is_complete, confidence, explanation = self.task_validator.validate_main_task_completion(
            self.current_main_task
        )
        
        if is_complete:
            return True, f"MainTask completion detected: {explanation} (confidence: {confidence:.2f})"
        
        # Return confidence-based assessment
        if confidence >= 0.7:
            return False, f"MainTask near completion: {explanation} (confidence: {confidence:.2f})"
        else:
            return False, f"MainTask in progress: {explanation} (confidence: {confidence:.2f})"
    
    def force_advance_task(self, reason: str = "Manual advancement") -> Tuple[bool, str]:
        """Force advancement to next task regardless of completion status.
        
        Args:
            reason: Reason for forced advancement
            
        Returns:
            Tuple of (success, message)
        """
        if not self.current_main_task:
            return False, "No current task to advance"
        
        # Mark current as completed with reason
        if self.current_subtask:
            self.current_subtask.completed = True
            self.current_subtask.completion_evidence.append(f"Force completed: {reason}")
        
        self.current_main_task.completion_evidence.append(f"Force completed: {reason}")
        
        # Advance to next
        return self.advance_task_progression()
    
    def get_task_dependencies(self, task_id: int) -> List[int]:
        """Get dependencies for a specific task.
        
        Args:
            task_id: ID of the task to check dependencies for
            
        Returns:
            List of task IDs that must be completed before this task
        """
        # For now, simple sequential dependency: task N depends on task N-1
        if task_id <= 1:
            return []
        return [task_id - 1]
    
    def check_task_dependencies_met(self, task_id: int) -> bool:
        """Check if all dependencies for a task are satisfied.
        
        Args:
            task_id: ID of task to check
            
        Returns:
            True if all dependencies are met
        """
        plan = self.task_manager.get_current_structured_plan()
        if not plan:
            return True
        
        dependencies = self.get_task_dependencies(task_id)
        
        # Check each dependency
        for dep_id in dependencies:
            # Find the dependent task
            dep_task = None
            for task in plan.tasks:
                if task.id == dep_id:
                    dep_task = task
                    break
            
            # If dependency not found or not completed, dependencies not met
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                if self.verbose:
                    print(f"  ⚠️ Task {task_id} blocked: dependency {dep_id} not completed")
                return False
        
        return True
    
    def get_next_available_task(self) -> Optional[MainTask]:
        """Get the next task that can be started based on dependencies.
        
        Returns:
            Next available MainTask or None
        """
        plan = self.task_manager.get_current_structured_plan()
        if not plan:
            return None
        
        # Re-evaluate BLOCKED tasks: if dependencies are now met, unblock to PENDING
        for task in plan.tasks:
            if task.status == TaskStatus.BLOCKED:
                if self.check_task_dependencies_met(task.id):
                    self.task_manager.update_main_task_status(
                        task.id,
                        TaskStatus.PENDING,
                        "Dependencies met; unblocked"
                    )

        # Find first pending task with satisfied dependencies
        for task in plan.tasks:
            if task.status == TaskStatus.PENDING:
                if self.check_task_dependencies_met(task.id):
                    return task
                else:
                    # Mark as blocked if dependencies not met
                    task.status = TaskStatus.BLOCKED
        
        return None
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the current execution state.
        
        Returns:
            Dictionary with execution summary
        """
        plan = self.task_manager.get_current_structured_plan()
        if not plan:
            return {"status": "no_plan"}
        
        completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
        total_main = len(plan.tasks)
        
        summary = {
            "plan_loaded": self.plan_loaded,
            "total_main_tasks": total_main,
            "completed_main_tasks": completed_main,
            "current_main_task": {
                "id": self.current_main_task.id,
                "description": self.current_main_task.description
            } if self.current_main_task else None,
            "current_subtask": {
                "id": self.current_subtask.id,
                "description": self.current_subtask.description
            } if self.current_subtask else None,
            "progress_percentage": int((completed_main / total_main) * 100) if total_main > 0 else 0
        }
        
        return summary
    
    def get_intelligent_completion_analysis(self) -> Dict[str, Any]:
        """Get detailed completion analysis using the TaskValidator.
        
        Returns:
            Dictionary with comprehensive completion analysis
        """
        if not self.current_main_task:
            return {"status": "no_current_task"}
        
        analysis = {
            "current_main_task": {
                "id": self.current_main_task.id,
                "description": self.current_main_task.description,
                "status": self.current_main_task.status.value
            }
        }
        
        # Get main task completion confidence
        main_confidence, main_breakdown = self.task_validator.get_completion_confidence(
            self.current_main_task,
            self.current_subtask
        )
        
        analysis["main_task_analysis"] = {
            "confidence": main_confidence,
            "breakdown": main_breakdown
        }
        
        # Get current subtask analysis if available
        if self.current_subtask:
            subtask_complete, subtask_confidence, subtask_explanation = self.task_validator.validate_subtask_completion(
                self.current_subtask,
                self.current_main_task
            )
            
            analysis["current_subtask"] = {
                "id": self.current_subtask.id,
                "description": self.current_subtask.description,
                "completed": self.current_subtask.completed,
                "validation": {
                    "is_complete": subtask_complete,
                    "confidence": subtask_confidence,
                    "explanation": subtask_explanation
                }
            }
        
        # Get overall plan progress
        plan = self.task_manager.get_current_structured_plan()
        if plan:
            completed_main = sum(1 for t in plan.tasks if t.status == TaskStatus.COMPLETED)
            total_main = len(plan.tasks)
            
            analysis["plan_progress"] = {
                "completed_main_tasks": completed_main,
                "total_main_tasks": total_main,
                "completion_percentage": round((completed_main / total_main) * 100, 1) if total_main > 0 else 0
            }
        
        return analysis
    
    def collect_evidence_from_tool_result(self, tool_name: str, result: Any) -> List[str]:
        """Automatically collect evidence from tool results.
        
        Args:
            tool_name: Name of the executed tool
            result: Result from tool execution
            
        Returns:
            List of evidence strings extracted from the result
        """
        evidence_items = []

        is_error = self._is_error_result(result)

        if is_error:
            # Record explicit failure evidence without implying success
            message = self._summarize_error(result)
            evidence_items.append(f"Tool {tool_name} returned error{': ' + message if message else ''}")
            return evidence_items

        # Basic evidence: tool execution (success path only)
        evidence_items.append(f"Successfully executed tool '{tool_name}'")

        # Analyze result for specific evidence (success path)
        if isinstance(result, dict):
            if result.get('success'):
                evidence_items.append(f"Tool {tool_name} returned success=True")

            # Look for data indicators
            data_keys = ['data', 'results', 'output', 'response', 'items']
            for key in data_keys:
                if key in result and result[key]:
                    evidence_items.append(f"Tool {tool_name} returned {key} with content")

        elif isinstance(result, list):
            if len(result) > 0:
                evidence_items.append(f"Tool {tool_name} returned list with {len(result)} items")

        elif isinstance(result, str):
            text = result.strip()
            if len(text) > 20:
                evidence_items.append(f"Tool {tool_name} returned substantial text output")

        # Check for completion-indicating tool names (success path)
        completion_indicators = {
            'get': 'Data retrieval completed',
            'fetch': 'Data fetching completed',
            'retrieve': 'Data retrieval completed',
            'analyze': 'Analysis completed',
            'calculate': 'Calculation completed',
            'process': 'Processing completed',
            'create': 'Creation completed',
            'generate': 'Generation completed'
        }

        for indicator, evidence_text in completion_indicators.items():
            if indicator in tool_name.lower():
                evidence_items.append(evidence_text)
                break

        return evidence_items

    # --- Helper methods for strict validation ---
    def _is_error_result(self, result: Any) -> bool:
        if isinstance(result, Exception):
            return True
        if isinstance(result, dict):
            if result.get('success') is False:
                return True
            err_val = result.get('error')
            if err_val:
                try:
                    return bool(str(err_val).strip())
                except Exception:
                    return True
        if isinstance(result, str):
            import re
            text = result.lower()
            # Use word boundary regex to avoid false positives from substrings
            # Also check for common error patterns at the start of lines or messages
            # First check for common non-error phrases that contain these words
            safe_phrases = [
                r'room for error',      # Common financial phrase
                r'margin.{0,5}error',   # "margin of error" or "margin for error"
                r'trial.{0,5}error',    # "trial and error"
                r'human error',         # Common phrase
                r'rounding error',      # Mathematical term
                r'tracking error',      # Financial term
                r'forecast error',      # Statistical term
                r'measurement error',   # Scientific term
            ]
            
            # If any safe phrase is found, it's not an error
            for safe_pattern in safe_phrases:
                if re.search(safe_pattern, text, re.IGNORECASE):
                    return False
            
            # Now check for actual error patterns
            error_patterns = [
                r'^error:',             # line starting with "error:"
                r'^failed:',            # line starting with "failed:"
                r'^exception:',         # line starting with "exception:"
                r'error occurred',      # phrase "error occurred"
                r'error calling',       # phrase "error calling" (common in tool errors)
                r'returned error',      # phrase "returned error"
                r'raised error',        # phrase "raised error"
                r'threw error',         # phrase "threw error"
                r'error message',       # phrase "error message"
                r'traceback',           # Python traceback indicator
                r'\bfailed to\b',       # phrase "failed to"
                r'\bunable to\b',       # phrase "unable to"
                r'\bcould not\b',       # phrase "could not"
                r'permission denied',   # permission error
                r'access denied',       # access error
                r'not found',           # not found error
                r'timeout',             # timeout error
                r'exception',           # exception (but not in safe contexts)
            ]
            return any(re.search(pattern, text, re.MULTILINE | re.IGNORECASE) for pattern in error_patterns)
        return False

    def _summarize_error(self, result: Any) -> str:
        try:
            if isinstance(result, Exception):
                return str(result)
            if isinstance(result, dict):
                if result.get('error'):
                    return str(result.get('error'))
                # Common error shapes
                for key in ['message', 'detail', 'details']:
                    if key in result:
                        return str(result[key])
            if isinstance(result, str):
                return result[:160]
        except Exception:
            return ""
        return ""

    def _is_tool_relevant(self, tool_name: str, main_task: MainTask, subtask: Optional[SubTask]) -> bool:
        if not main_task or not subtask:
            return False
        try:
            tool = str(tool_name).strip().lower()
            predicted = [str(t).strip().lower() for t in (main_task.predicted_tool_use or [])]
            in_predicted = tool in predicted
            in_description = tool in str(subtask.description).lower()
            # Relaxed relevance: predicted OR mentioned in subtask description
            return in_predicted or in_description
        except Exception:
            return False

    def _subtask_has_tool_named_evidence(self, subtask: SubTask, tool_name: str) -> bool:
        if not subtask:
            return False
        t = str(tool_name).strip().lower()
        for ev in subtask.completion_evidence:
            try:
                if t in str(ev).lower():
                    return True
            except Exception:
                continue
        return False

    def _looks_like_success_evidence(self, evidence_text: str) -> bool:
        text = (evidence_text or "").lower()
        success_markers = ['successfully executed tool', 'returned success=true', 'completed', 'retrieval completed', 'analysis completed', 'calculation completed', 'processing completed', 'creation completed', 'generation completed']
        return any(marker in text for marker in success_markers)

    # === Advanced Task Management ===
    
    def handle_task_failure(self, error_message: str, recovery_strategy: str = "retry") -> Tuple[bool, str]:
        """Handle task failure with intelligent recovery strategies.
        
        Args:
            error_message: Description of the failure
            recovery_strategy: Strategy to use ('retry', 'skip', 'alternative')
            
        Returns:
            Tuple of (success, message)
        """
        if not self.current_main_task:
            return False, "No current task to handle failure for"
        
        task_id = self.current_main_task.id
        
        if recovery_strategy == "retry":
            # Mark as failed and suggest retry
            self.task_manager.mark_task_failed(
                task_id, 
                error_message, 
                "Consider retrying with different approach or tools"
            )
            
            # Reset current task for retry
            success = self.task_manager.retry_failed_task(task_id, f"Auto-retry after: {error_message}")
            
            if success:
                return True, f"Task {task_id} reset for retry"
            else:
                return False, f"Failed to reset task {task_id} for retry"
        
        elif recovery_strategy == "skip":
            # Mark as skipped and move to next
            self.task_manager.update_main_task_status(
                task_id,
                TaskStatus.SKIPPED,
                f"Skipped due to failure: {error_message}"
            )
            
            # Advance to next task
            success, message = self.advance_task_progression()
            return success, f"Skipped failed task, {message}"
        
        elif recovery_strategy == "alternative":
            # Don't mark as failed - instead mark current subtask as complete with alternative approach
            # This allows progression to continue
            
            # Add evidence about using alternative approach
            self.task_manager.add_task_evidence(
                task_id,
                f"Alternative approach used due to: {error_message}"
            )
            
            # If there's a current subtask, mark it as complete to allow progression
            if self.current_subtask:
                self.task_manager.update_subtask_status(
                    self.current_main_task.id,
                    self.current_subtask.id,
                    True,  # Mark as complete
                    f"Completed with alternative approach: {error_message}"
                )
                
                # Now advance to next subtask
                success, message = self.advance_task_progression()
                if success:
                    return True, f"Task {task_id} continued with alternative approach, {message}"
                else:
                    return True, f"Task {task_id} used alternative approach, but no next subtask"
            
            return True, f"Task {task_id} marked for alternative approach"
        
        else:
            return False, f"Unknown recovery strategy: {recovery_strategy}"
    
    def check_for_stagnation(self, recent_observations: List[Any], threshold: int = 3) -> Tuple[bool, str]:
        """Check if task execution is stagnating.
        
        Args:
            recent_observations: Recent tool observations
            threshold: Number of similar observations that indicate stagnation
            
        Returns:
            Tuple of (is_stagnating, reason)
        """
        if not self.current_main_task or len(recent_observations) < threshold:
            return False, "Insufficient data for stagnation check"
        
        # Check for repeated similar observations
        recent_strings = [str(obs)[:100] for obs in recent_observations[-threshold:]]
        
        # Simple stagnation check: if all recent observations are very similar
        unique_observations = set(recent_strings)
        if len(unique_observations) == 1:
            return True, f"Last {threshold} observations are identical"
        
        # Check for error repetition
        error_count = sum(1 for obs in recent_strings if any(
            error_word in obs.lower() for error_word in ['error', 'failed', 'exception']
        ))
        
        if error_count >= threshold - 1:
            return True, f"Repeated errors detected in last {threshold} observations"
        
        # Check for no progress indicators
        progress_indicators = ['success', 'completed', 'returned', 'generated', 'retrieved']
        progress_count = sum(1 for obs in recent_strings if any(
            indicator in obs.lower() for indicator in progress_indicators
        ))
        
        if progress_count == 0 and len(recent_strings) >= threshold:
            return True, f"No progress indicators in last {threshold} observations"
        
        return False, "No stagnation detected"
    
    def get_parallel_ready_tasks(self) -> List[MainTask]:
        """Get tasks that can be executed in parallel (no dependencies blocking).
        
        Returns:
            List of MainTasks ready for parallel execution
        """
        plan = self.task_manager.get_current_structured_plan()
        if not plan:
            return []
        
        parallel_ready = []
        
        for task in plan.tasks:
            if task.status == TaskStatus.PENDING:
                # Check if dependencies are met
                if self.check_task_dependencies_met(task.id):
                    parallel_ready.append(task)
        
        return parallel_ready
    
    def simulate_parallel_execution(self, max_parallel: int = 2) -> Dict[str, Any]:
        """Simulate what parallel execution would look like.
        
        Args:
            max_parallel: Maximum number of tasks to run in parallel
            
        Returns:
            Dictionary with parallel execution simulation
        """
        ready_tasks = self.get_parallel_ready_tasks()
        
        if not ready_tasks:
            return {
                "parallel_possible": False,
                "reason": "No tasks ready for parallel execution"
            }
        
        # Limit to max_parallel
        parallel_tasks = ready_tasks[:max_parallel]
        
        simulation = {
            "parallel_possible": True,
            "recommended_parallel_count": len(parallel_tasks),
            "max_parallel_requested": max_parallel,
            "parallel_tasks": [
                {
                    "id": task.id,
                    "description": task.description,
                    "predicted_tools": task.predicted_tool_use,
                    "estimated_tool_count": len(task.predicted_tool_use)
                }
                for task in parallel_tasks
            ],
            "sequential_alternative": len(ready_tasks),
            "potential_time_savings": f"{min(len(parallel_tasks), max_parallel)}x speedup potential"
        }
        
        return simulation
    
    def create_plan_analytics_report(self) -> Dict[str, Any]:
        """Create comprehensive analytics report for plan execution.
        
        Returns:
            Dictionary with detailed plan analytics
        """
        if not self.plan_loaded:
            return {"status": "no_plan"}
        
        plan = self.task_manager.get_current_structured_plan()
        execution_summary = self.get_execution_summary()
        progress_summary = self.task_manager.get_task_progress_summary()
        execution_analytics = self.task_manager.get_execution_analytics()
        plan_health = self.task_manager.get_plan_health_status()
        
        # Task complexity analysis
        task_complexity = []
        for task in plan.tasks:
            complexity_score = (
                len(task.subtasks) * 2 +  # Subtask count weighted
                len(task.predicted_tool_use) +  # Tool count
                len(task.description.split()) / 10  # Description complexity
            )
            
            task_complexity.append({
                "task_id": task.id,
                "complexity_score": round(complexity_score, 1),
                "subtask_count": len(task.subtasks),
                "predicted_tool_count": len(task.predicted_tool_use),
                "description_length": len(task.description)
            })
        
        # Execution efficiency metrics
        total_evidence = sum(len(task.completion_evidence) for task in plan.tasks)
        total_observations = sum(len(task.observations) for task in plan.tasks)
        
        # Failed and blocked task analysis
        failed_tasks = self.task_manager.get_failed_tasks()
        blocked_tasks = [task for task in plan.tasks if task.status == TaskStatus.BLOCKED]
        
        analytics_report = {
            "plan_overview": {
                "total_main_tasks": execution_summary.get('total_main_tasks', 0),
                "total_subtasks": progress_summary.get('total_subtasks', 0),
                "plan_loaded": self.plan_loaded,
                "execution_active": execution_summary.get('current_main_task') is not None
            },
            "progress_metrics": {
                "overall_progress": progress_summary.get('overall_progress_percentage', 0),
                "main_task_progress": progress_summary.get('main_task_progress_percentage', 0),
                "subtask_progress": progress_summary.get('subtask_progress_percentage', 0),
                "completion_rate": plan_health.get('completion_rate', 0)
            },
            "health_metrics": {
                "health_status": plan_health.get('health_status', 'unknown'),
                "health_score": plan_health.get('health_score', 0),
                "failure_rate": plan_health.get('failure_rate', 0),
                "blocked_rate": plan_health.get('blocked_rate', 0)
            },
            "complexity_analysis": {
                "average_complexity": round(sum(t['complexity_score'] for t in task_complexity) / len(task_complexity), 1) if task_complexity else 0,
                "most_complex_task": max(task_complexity, key=lambda t: t['complexity_score']) if task_complexity else None,
                "total_predicted_tools": sum(t['predicted_tool_count'] for t in task_complexity),
                "task_complexity_breakdown": task_complexity
            },
            "execution_efficiency": {
                "total_evidence_items": total_evidence,
                "total_observations": total_observations,
                "evidence_per_task": round(total_evidence / len(plan.tasks), 1) if plan.tasks else 0,
                "observations_per_task": round(total_observations / len(plan.tasks), 1) if plan.tasks else 0,
                "execution_history_entries": execution_analytics.get('total_history_entries', 0)
            },
            "failure_analysis": {
                "failed_task_count": len(failed_tasks),
                "blocked_task_count": len(blocked_tasks),
                "failed_tasks": failed_tasks,
                "blocked_task_ids": [task.id for task in blocked_tasks]
            },
            "parallel_execution": self.simulate_parallel_execution(),
            "recommendations": self._generate_execution_recommendations()
        }
        
        return analytics_report
    
    def _generate_execution_recommendations(self) -> List[str]:
        """Generate recommendations for improving plan execution.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        if not self.plan_loaded:
            return ["Load a structured plan to begin systematic execution"]
        
        plan = self.task_manager.get_current_structured_plan()
        plan_health = self.task_manager.get_plan_health_status()
        
        # Health-based recommendations
        if plan_health.get('health_score', 0) < 0.5:
            recommendations.append("Plan health is concerning - consider reviewing failed/blocked tasks")
        
        if plan_health.get('failure_rate', 0) > 20:
            recommendations.append("High failure rate detected - consider task simplification or tool alternatives")
        
        if plan_health.get('blocked_rate', 0) > 10:
            recommendations.append("Tasks are getting blocked - review task dependencies")
        
        # Progress-based recommendations
        progress = self.task_manager.get_task_progress_summary()
        if progress.get('overall_progress_percentage', 0) < 25:
            recommendations.append("Low progress - focus on completing current task systematically")
        
        # Parallel execution recommendations
        parallel_sim = self.simulate_parallel_execution()
        if parallel_sim.get('parallel_possible') and parallel_sim.get('recommended_parallel_count', 0) > 1:
            recommendations.append(f"Consider parallel execution of {parallel_sim['recommended_parallel_count']} tasks for efficiency")
        
        # Task complexity recommendations
        failed_tasks = self.task_manager.get_failed_tasks()
        if failed_tasks:
            recommendations.append(f"Consider breaking down {len(failed_tasks)} failed tasks into smaller subtasks")
        
        # Evidence collection recommendations
        if progress.get('execution_history_entries', 0) < len(plan.tasks) * 2:
            recommendations.append("Increase evidence collection - use task management tools more frequently")
        
        # Default recommendation
        if not recommendations:
            recommendations.append("Plan execution is healthy - continue systematic execution")
        
        return recommendations
