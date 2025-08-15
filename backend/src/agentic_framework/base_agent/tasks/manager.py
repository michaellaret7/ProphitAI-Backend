"""Task management system with backward compatibility for ChecklistManager."""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .models import Task, TaskStatus, TaskPriority, TaskValidation


class TaskManager:
    """Enhanced task manager with state tracking and validation."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.tasks: Dict[str, Task] = {}
        self.execution_history: List[Dict] = []
        
        # Path for task state file - updated path since this is now in tasks/ subfolder
        self.state_path = Path(__file__).parent.parent.parent / "agent_output" / "task_state.json"
    
    def add_task(self, task: Task, dependencies: List[str] = None):
        """Add task with optional dependencies."""
        self.tasks[task.id] = task
        
        if dependencies:
            task.dependencies.extend(dependencies)
        
        self._update_task_states()
        
        if self.verbose:
            print(f"📝 Added task: {task.id} - {task.description}")
    
    def _update_task_states(self):
        """Update task states based on dependencies."""
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                if self._dependencies_met(task_id):
                    # Don't auto-transition to IN_PROGRESS, just mark as ready
                    pass  # Task remains PENDING but is ready to start
                else:
                    task.status = TaskStatus.BLOCKED
    
    def _dependencies_met(self, task_id: str) -> bool:
        """Check if all dependencies for a task are completed."""
        task = self.tasks.get(task_id)
        if not task or not task.dependencies:
            return True
        
        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        
        return True
    
    def get_next_tasks(self, max_parallel: int = 1) -> List[Task]:
        """Get next executable tasks considering dependencies."""
        ready_tasks = []
        
        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING and self._dependencies_met(task.id):
                ready_tasks.append(task)
        
        # Sort by priority then creation time
        ready_tasks.sort(key=lambda t: (t.priority.value, t.created_at))
        return ready_tasks[:max_parallel]
    
    def update_task_status(self, task_id: str, status: str, evidence: Dict = None, reason: str = None, iteration: int = None) -> Dict[str, Any]:
        """Update task status with evidence."""
        # Handle both old-style step numbers and new task IDs
        task = None
        
        # First try direct ID lookup
        if task_id in self.tasks:
            task = self.tasks[task_id]
        else:
            # Try to find by step number (backward compatibility)
            try:
                step_num = int(task_id) if task_id.isdigit() else int(re.search(r'\d+', str(task_id)).group())
                for t in self.tasks.values():
                    if hasattr(t, 'step') or 'step' in t.context:
                        task_step = t.context.get('step', getattr(t, 'step', None))
                        if task_step == step_num:
                            task = t
                            break
            except:
                pass
        
        if not task:
            return {"success": False, "error": f"Task '{task_id}' not found"}
        
        # Map status strings to TaskStatus enum
        status_map = {
            'started': TaskStatus.IN_PROGRESS,
            'in_progress': TaskStatus.IN_PROGRESS,
            'completed': TaskStatus.COMPLETED,
            'complete': TaskStatus.COMPLETED,
            'done': TaskStatus.COMPLETED,
            'failed': TaskStatus.FAILED,
            'blocked': TaskStatus.BLOCKED,
            'skipped': TaskStatus.SKIPPED
        }
        
        new_status = status_map.get(status.lower())
        if not new_status:
            return {"success": False, "error": f"Invalid status: {status}"}
        
        # Update task status
        old_status = task.status
        task.status = new_status
        
        # Update timing
        if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
            task.started_at = datetime.now()
        elif new_status == TaskStatus.COMPLETED:
            task.completed_at = datetime.now()
            if iteration is not None:
                task.completed_at_iteration = iteration
        
        # Store evidence if provided
        if evidence:
            task.completion_evidence.update(evidence)
            if 'outputs' in evidence:
                task.outputs.update(evidence['outputs'])
        
        # Log the update
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'task_id': task.id,
            'old_status': old_status.value,
            'new_status': new_status.value,
            'reason': reason,
            'evidence': evidence
        })
        
        # Update dependent tasks
        self._update_task_states()
        
        # Save state
        self.save_state()
        
        if self.verbose:
            status_icon = "✅" if new_status == TaskStatus.COMPLETED else "▶️" if new_status == TaskStatus.IN_PROGRESS else "❌" if new_status == TaskStatus.FAILED else "📝"
            print(f"{status_icon} Task '{task.id}': {old_status.value} -> {new_status.value}")
        
        return {"success": True, "task_id": task.id, "status": new_status.value}
    
    def mark_complete(self, task_id: str, confidence: float = 1.0) -> bool:
        """Mark a task as complete with confidence score."""
        result = self.update_task_status(
            task_id, 
            'completed',
            evidence={'confidence': confidence}
        )
        return result.get('success', False)
    
    def get_current_task(self) -> Optional[Task]:
        """Get the currently active task."""
        for task in self.tasks.values():
            if task.status == TaskStatus.IN_PROGRESS:
                return task
        return None
    
    def handle_tool_execution(self, tool_name: str, tool_result: Any) -> Optional[Dict[str, Any]]:
        """Handle tool execution and check for task completion.
        
        Args:
            tool_name: Name of the tool executed
            tool_result: Result from the tool
            
        Returns:
            Dict with task update info if task state changed, None otherwise
        """
        current_task = self.get_current_task()
        if not current_task:
            return None
        
        # Store tool result in task outputs
        if tool_name not in current_task.outputs:
            current_task.outputs[tool_name] = tool_result
        
        # Check if this completes any required tools
        if current_task.required_tools:
            if tool_name in current_task.required_tools:
                completed_tools = [t for t in current_task.required_tools if t in current_task.outputs]
                if len(completed_tools) == len(current_task.required_tools):
                    # All required tools executed
                    return {
                        'task_id': current_task.id,
                        'status': 'tools_complete',
                        'completed_tools': completed_tools
                    }
        
        return None
    
    def all_tasks_complete(self) -> bool:
        """Check if all tasks are complete."""
        if not self.tasks:
            return True
        
        return all(
            task.status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
            for task in self.tasks.values()
        )
    
    def save_state(self):
        """Save current task state to JSON."""
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'tasks': {
                task_id: task.to_dict()
                for task_id, task in self.tasks.items()
            },
            'execution_history': self.execution_history[-50:]  # Keep last 50 entries
        }
        
        try:
            with open(self.state_path, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save task state: {e}")
    
    def load_state(self):
        """Load task state from JSON."""
        try:
            if self.state_path.exists():
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                # Reconstruct tasks
                self.tasks = {}
                for task_id, task_data in state_data.get('tasks', {}).items():
                    self.tasks[task_id] = Task.from_dict(task_data)
                
                self.execution_history = state_data.get('execution_history', [])
                
                if self.verbose:
                    print(f"📂 Loaded {len(self.tasks)} tasks from state")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load task state: {e}")
    
    # === Backward Compatibility Methods ===
    
    def parse_plan_to_tasks(self, content: str, trace_length: int) -> bool:
        """Parse the agent's JSON plan into tasks."""
        try:
            # Look for JSON object in the content
            json_match = re.search(r'\{.*"plan".*\}', content, re.DOTALL)
            if not json_match:
                return False
            
            plan_data = json.loads(json_match.group(0))
            if "plan" not in plan_data:
                return False
            
            # Convert plan to tasks
            self.tasks = {}
            
            for item in plan_data["plan"]:
                step_num = item.get("step", len(self.tasks) + 1)
                description = item.get("desc", "")
                
                # Create task
                task_id = f"task_{step_num}"
                task = Task(
                    id=task_id,
                    description=description,
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.MEDIUM
                )
                task.context['step'] = step_num  # Store step number for compatibility
                self.tasks[task_id] = task
            
            self.save_state()
            
            if self.verbose:
                print(f"📋 Task list created with {len(self.tasks)} items")
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to parse plan: {e}")
            return False

    
    def update_task_progress(self, iteration: int, trace_length: int) -> None:
        """Update task progress - start first pending task if none in progress."""
        if not self.tasks:
            return
        
        # If no task is in progress, start the first pending one
        has_in_progress = any(task.status == TaskStatus.IN_PROGRESS for task in self.tasks.values())
        if not has_in_progress:
            for task in self.tasks.values():
                if task.status == TaskStatus.PENDING and self._dependencies_met(task.id):
                    task.status = TaskStatus.IN_PROGRESS
                    task.started_at_iteration = iteration
                    task.started_at = datetime.now()
                    break
        
        self.save_state()
    
    def parse_progress_from_response(self, content: str, iteration: int, trace_length: int) -> bool:
        """Parse agent response for task completion indicators."""
        if not content:
            return False
        
        content_lower = content.lower()
        updated = False
        
        # Completion patterns
        completion_patterns = [
            r"task\s+(\d+)\s+(?:is\s+)?(?:complete|completed|done|finished)",
            r"step\s+(\d+)\s+(?:is\s+)?(?:complete|completed|done|finished)",
            r"completed?\s+(?:task|step)\s+(\d+)",
            r"finished\s+(?:task|step)\s+(\d+)",
            r"✓\s*(?:task|step)\s+(\d+)",
            r"(?:task|step)\s+(\d+)\s*✓",
        ]
        
        for pattern in completion_patterns:
            matches = re.finditer(pattern, content_lower)
            for match in matches:
                task_num = int(match.group(1))
                
                # Update task system
                task_id = f"task_{task_num}"
                if task_id in self.tasks:
                    result = self.update_task_status(
                        task_id,
                        'completed',
                        evidence={'parsed_from_response': True},
                        reason=f"Detected completion in response: {match.group(0)}",
                        iteration=iteration
                    )
                    updated = result.get('success', False)
                    
                    # Start next pending task if this one completed
                    if updated:
                        for task in self.tasks.values():
                            if task.status == TaskStatus.PENDING and self._dependencies_met(task.id):
                                task.status = TaskStatus.IN_PROGRESS
                                task.started_at_iteration = iteration
                                task.started_at = datetime.now()
                                break
        
        if updated:
            self.save_state()
        
        return updated
    
    def is_checklist_complete(self) -> bool:
        """Check if all tasks are completed."""
        return self.all_tasks_complete()
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending or in-progress tasks."""
        incomplete = []
        
        for task in self.tasks.values():
            if task.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
                incomplete.append({
                    "step": task.context.get('step', task.id),
                    "description": task.description,
                    "status": task.status.value
                })
        
        return incomplete
    
    def get_task_status_prompt(self, iteration: int) -> str:
        """Generate combined analysis direction + task status prompt."""
        # Check if all tasks are complete
        all_complete = self.all_tasks_complete()
        
        # Base analysis direction
        if all_complete:
            base_prompt = (
                "Analyze the latest tool observations. Based on your analysis, either: "
                "(a) call another tool to continue iterating, or "
                "(b) produce a FINAL ANSWER preceded by 'Final Answer:' (all tasks are complete)."
            )
        else:
            base_prompt = (
                "Analyze the latest tool observations and continue working through your task list. "
                "You MUST complete all tasks before producing a Final Answer. "
                "Call the appropriate tool to continue your task."
            )
        
        # If no tasks, return just the base prompt
        if not self.tasks:
            return base_prompt
        
        # Build status display
        status_lines = ["\n\n📋 Task Progress (Iteration {}):".format(iteration)]
        
        current_task_id = None
        
        # Display tasks
        for task in self.tasks.values():
            step_num = task.context.get('step', task.id)
            
            if task.status == TaskStatus.COMPLETED:
                status_lines.append(f"[✓ DONE] {step_num}: {task.description}")
            elif task.status == TaskStatus.IN_PROGRESS:
                status_lines.append(f"→ {step_num}: {task.description} (IN PROGRESS)")
                current_task_id = task.id
            elif task.status == TaskStatus.FAILED:
                status_lines.append(f"[✗ FAILED] {step_num}: {task.description}")
            elif task.status == TaskStatus.BLOCKED:
                status_lines.append(f"[⊘ BLOCKED] {step_num}: {task.description}")
            else:
                status_lines.append(f"  {step_num}: {task.description}")
        
        # Count progress
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        total = len(self.tasks)
        
        status_lines.append(f"\nProgress: {completed}/{total} tasks completed")
        
        # Add task update instruction
        status_lines.append(
            "\n💡 You can now directly update task status using the 'update_task_status' tool "
            "when you complete a task, providing evidence of completion."
        )
        
        # Add reminder based on completion status
        if all_complete:
            status_lines.append("\n✅ All tasks complete! You may now produce your Final Answer.")
        else:
            remaining = len(self.get_incomplete_tasks())
            status_lines.append(f"\n⚠️ {remaining} tasks remaining. Continue working through your task list.")
            status_lines.append("Remember: You CANNOT produce a Final Answer until ALL tasks are complete.")
        
        return base_prompt + "\n".join(status_lines)


