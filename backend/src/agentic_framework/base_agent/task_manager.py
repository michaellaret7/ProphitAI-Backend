"""Task management system with backward compatibility for ChecklistManager."""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

from .task_models import Task, TaskStatus, TaskPriority, TaskValidation


class TaskManager:
    """Enhanced task manager with state tracking and validation."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.tasks: Dict[str, Task] = {}
        self.execution_history: List[Dict] = []
        
        # Maintain file paths for compatibility
        self.checklist_path = Path(__file__).parent.parent / "agent_output" / "agent_checklist.json"
        self.state_path = Path(__file__).parent.parent / "agent_output" / "task_state.json"
        
        # Checklist compatibility
        self.checklist_enabled = False
        self.checklist_items: List[Dict[str, Any]] = []
        
        # Clear the checklist file at start
        try:
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump({}, f)
        except Exception:
            pass
    
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
    
    def update_task_status(self, task_id: str, status: str, evidence: Dict = None, reason: str = None) -> Dict[str, Any]:
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
    
    def parse_plan_to_checklist(self, content: str, trace_length: int) -> bool:
        """Parse the agent's JSON plan into checklist items (backward compatibility)."""
        try:
            # Look for JSON object in the content
            json_match = re.search(r'\{.*"plan".*\}', content, re.DOTALL)
            if not json_match:
                return False
            
            plan_data = json.loads(json_match.group(0))
            if "plan" not in plan_data:
                return False
            
            # Convert plan to both old checklist and new tasks
            self.checklist_items = []
            self.tasks = {}
            
            for item in plan_data["plan"]:
                step_num = item.get("step", len(self.checklist_items) + 1)
                description = item.get("desc", "")
                
                # Old checklist format
                self.checklist_items.append({
                    "step": step_num,
                    "description": description,
                    "status": "pending",
                    "started_at_iteration": None,
                    "completed_at_iteration": None
                })
                
                # New task format
                task_id = f"task_{step_num}"
                task = Task(
                    id=task_id,
                    description=description,
                    status=TaskStatus.PENDING,
                    priority=TaskPriority.MEDIUM
                )
                task.context['step'] = step_num  # Store step number for compatibility
                self.tasks[task_id] = task
            
            self.checklist_enabled = True
            self.save_checklist(trace_length)
            self.save_state()
            
            if self.verbose:
                print(f"📋 Checklist created with {len(self.checklist_items)} items")
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to parse plan: {e}")
            return False
    
    def save_checklist(self, trace_length: int) -> None:
        """Save current checklist to JSON file (backward compatibility)."""
        if not self.checklist_enabled:
            return
        
        try:
            checklist_data = {
                "created_at": datetime.now().isoformat(),
                "current_iteration": trace_length,
                "items": self.checklist_items
            }
            
            with open(self.checklist_path, "w", encoding="utf-8") as f:
                json.dump(checklist_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to save checklist: {e}")
    
    def update_checklist_progress(self, iteration: int, trace_length: int) -> None:
        """Update checklist based on recent tool calls (backward compatibility)."""
        if not self.checklist_enabled or not self.checklist_items:
            return
        
        # Sync with task states
        for idx, item in enumerate(self.checklist_items):
            task_id = f"task_{item['step']}"
            if task_id in self.tasks:
                task = self.tasks[task_id]
                
                # Map task status to checklist status
                if task.status == TaskStatus.COMPLETED:
                    item['status'] = 'completed'
                    if not item.get('completed_at_iteration'):
                        item['completed_at_iteration'] = iteration
                elif task.status == TaskStatus.IN_PROGRESS:
                    item['status'] = 'in_progress'
                    if not item.get('started_at_iteration'):
                        item['started_at_iteration'] = iteration
                elif task.status == TaskStatus.FAILED:
                    item['status'] = 'failed'
                else:
                    item['status'] = 'pending'
        
        # If no task is in progress, start the first pending one
        has_in_progress = any(item["status"] == "in_progress" for item in self.checklist_items)
        if not has_in_progress:
            for item in self.checklist_items:
                if item["status"] == "pending":
                    item["status"] = "in_progress"
                    item["started_at_iteration"] = iteration
                    
                    # Update corresponding task
                    task_id = f"task_{item['step']}"
                    if task_id in self.tasks:
                        self.tasks[task_id].status = TaskStatus.IN_PROGRESS
                        self.tasks[task_id].started_at_iteration = iteration
                    break
        
        self.save_checklist(trace_length)
        self.save_state()
    
    def parse_progress_from_response(self, content: str, iteration: int, trace_length: int) -> bool:
        """Parse agent response for task completion indicators (backward compatibility)."""
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
                
                # Update new task system
                task_id = f"task_{task_num}"
                if task_id in self.tasks:
                    result = self.update_task_status(
                        task_id,
                        'completed',
                        evidence={'parsed_from_response': True},
                        reason=f"Detected completion in response: {match.group(0)}"
                    )
                    updated = result.get('success', False)
                
                # Update old checklist
                for item in self.checklist_items:
                    if item.get("step") == task_num:
                        if item["status"] == "in_progress":
                            item["status"] = "completed"
                            item["completed_at_iteration"] = iteration
                            
                            # Start next pending task
                            for next_item in self.checklist_items:
                                if next_item["status"] == "pending":
                                    next_item["status"] = "in_progress"
                                    next_item["started_at_iteration"] = iteration
                                    
                                    # Update corresponding task
                                    next_task_id = f"task_{next_item['step']}"
                                    if next_task_id in self.tasks:
                                        self.tasks[next_task_id].status = TaskStatus.IN_PROGRESS
                                        self.tasks[next_task_id].started_at_iteration = iteration
                                    break
                        break
        
        if updated:
            self.save_checklist(trace_length)
            self.save_state()
        
        return updated
    
    def is_checklist_complete(self) -> bool:
        """Check if all checklist items are completed (backward compatibility)."""
        # Use new task system if available
        if self.tasks:
            return self.all_tasks_complete()
        
        # Fall back to old checklist
        if not self.checklist_enabled or not self.checklist_items:
            return True
        
        return all(item.get("status") == "completed" for item in self.checklist_items)
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending or in-progress tasks (backward compatibility)."""
        incomplete = []
        
        # Use new task system if available
        if self.tasks:
            for task in self.tasks.values():
                if task.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
                    incomplete.append({
                        "step": task.context.get('step', task.id),
                        "description": task.description,
                        "status": task.status.value
                    })
        else:
            # Fall back to old checklist
            for item in self.checklist_items:
                if item.get("status") != "completed":
                    incomplete.append({
                        "step": item.get("step", "?"),
                        "description": item.get("description", ""),
                        "status": item.get("status", "pending")
                    })
        
        return incomplete
    
    def get_checklist_prompt(self, iteration: int) -> str:
        """Generate combined analysis direction + checklist status prompt (backward compatibility)."""
        # Check if checklist is complete
        checklist_complete = self.is_checklist_complete()
        
        # Base analysis direction
        if checklist_complete:
            base_prompt = (
                "Analyze the latest tool observations. Based on your analysis, either: "
                "(a) call another tool to continue iterating, or "
                "(b) produce a FINAL ANSWER preceded by 'Final Answer:' (all checklist items are complete)."
            )
        else:
            base_prompt = (
                "Analyze the latest tool observations and continue working through your checklist. "
                "You MUST complete all checklist items before producing a Final Answer. "
                "Call the appropriate tool to continue your task."
            )
        
        # If no checklist/tasks, return just the base prompt
        if not self.checklist_enabled and not self.tasks:
            return base_prompt
        
        # Build status display
        status_lines = ["\n\n📋 Task Progress (Iteration {}):".format(iteration)]
        
        current_task_id = None
        
        # Display tasks
        if self.tasks:
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
        else:
            # Fall back to old checklist display
            for item in self.checklist_items:
                step_num = item.get("step", "?")
                desc = item.get("description", "")
                status = item.get("status", "pending")
                
                if status == "completed":
                    status_lines.append(f"[✓ DONE] Step {step_num}: {desc}")
                elif status == "in_progress":
                    status_lines.append(f"→ Step {step_num}: {desc} (IN PROGRESS)")
                    current_task_id = f"Step {step_num}"
                else:
                    status_lines.append(f"  Step {step_num}: {desc}")
        
        # Count progress
        if self.tasks:
            completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
            total = len(self.tasks)
        else:
            completed = sum(1 for item in self.checklist_items if item["status"] == "completed")
            total = len(self.checklist_items)
        
        status_lines.append(f"\nProgress: {completed}/{total} tasks completed")
        
        # Add task update instruction
        status_lines.append(
            "\n💡 You can now directly update task status using the 'update_task_status' tool "
            "when you complete a task, providing evidence of completion."
        )
        
        # Add reminder based on completion status
        if checklist_complete:
            status_lines.append("\n✅ All tasks complete! You may now produce your Final Answer.")
        else:
            remaining = len(self.get_incomplete_tasks())
            status_lines.append(f"\n⚠️ {remaining} tasks remaining. Continue working through your checklist.")
            status_lines.append("Remember: You CANNOT produce a Final Answer until ALL tasks are complete.")
        
        return base_prompt + "\n".join(status_lines)


class ChecklistCompatibilityWrapper:
    """Maintains backward compatibility with existing checklist system."""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
    
    def parse_plan_to_checklist(self, content: str, trace_length: int) -> bool:
        """Convert old-style plan to new task system."""
        return self.task_manager.parse_plan_to_checklist(content, trace_length)
    
    def is_checklist_complete(self) -> bool:
        """Check if all tasks are complete."""
        return self.task_manager.is_checklist_complete()
    
    def update_checklist_progress(self, iteration: int, trace_length: int) -> None:
        """Update checklist progress."""
        self.task_manager.update_checklist_progress(iteration, trace_length)
    
    def parse_progress_from_response(self, content: str, iteration: int, trace_length: int) -> bool:
        """Parse progress from response."""
        return self.task_manager.parse_progress_from_response(content, iteration, trace_length)
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """Get incomplete tasks."""
        return self.task_manager.get_incomplete_tasks()
    
    def get_checklist_prompt(self, iteration: int) -> str:
        """Get checklist prompt."""
        return self.task_manager.get_checklist_prompt(iteration)
    
    def save_checklist(self, trace_length: int) -> None:
        """Save checklist."""
        self.task_manager.save_checklist(trace_length)
