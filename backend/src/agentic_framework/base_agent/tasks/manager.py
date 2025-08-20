"""Task management system with backward compatibility for ChecklistManager."""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from .models import TaskStatus, TodoList, MainTask, SubTask


class TaskManager:
    """Simplified task manager for structured planning system."""
    
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.tasks: Dict[str, Dict[str, Any]] = {}  # Simplified task storage
        self.execution_history: List[Dict] = []
        self.structured_plan: Optional[TodoList] = None  # Store the structured plan
        
        # Path for task state file - updated path since this is now in tasks/ subfolder
        self.state_path = Path(__file__).parent.parent.parent / "agent_output" / "task_state.json"
    
    def add_structured_plan(self, plan: TodoList):
        """Add a structured plan from the planning tool."""
        self.structured_plan = plan
        
        if self.verbose:
            print(f"📝 Added structured plan with {len(plan.tasks)} main tasks")
        
        # Save state immediately after adding structured plan
        self.save_state()
    
    def get_current_structured_plan(self) -> Optional[TodoList]:
        """Get the current structured plan."""
        return self.structured_plan
    
    def get_main_task_by_id(self, task_id: int) -> Optional[MainTask]:
        """Get a main task from the structured plan by ID."""
        if not self.structured_plan:
            return None
        
        for task in self.structured_plan.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_subtask_by_id(self, main_task_id: int, subtask_id: str) -> Optional[SubTask]:
        """Get a subtask from a main task by ID."""
        main_task = self.get_main_task_by_id(main_task_id)
        if not main_task:
            return None
        
        for subtask in main_task.subtasks:
            if subtask.id == subtask_id:
                return subtask
        return None
    
    def update_main_task_status(self, task_id: int, status: TaskStatus, reason: str = None) -> bool:
        """Update main task status in real-time."""
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            if self.verbose:
                print(f"⚠️ Main task {task_id} not found")
            return False
        
        old_status = main_task.status
        main_task.status = status
        
        # Add to execution history
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_status_update',
            'task_id': task_id,
            'old_status': old_status.value,
            'new_status': status.value,
            'reason': reason
        })
        
        if self.verbose:
            print(f"📋 Main Task {task_id}: {old_status.value} → {status.value}")
        
        # Save state after update
        self.save_state()
        return True
    
    def update_subtask_status(self, main_task_id: int, subtask_id: str, completed: bool, reason: str = None) -> bool:
        """Update subtask completion status in real-time."""
        subtask = self.get_subtask_by_id(main_task_id, subtask_id)
        if not subtask:
            if self.verbose:
                print(f"⚠️ SubTask {subtask_id} in Task {main_task_id} not found")
            return False
        
        old_completed = subtask.completed
        subtask.completed = completed
        
        # Add to execution history
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'subtask_status_update',
            'main_task_id': main_task_id,
            'subtask_id': subtask_id,
            'old_completed': old_completed,
            'new_completed': completed,
            'reason': reason
        })
        
        if self.verbose:
            status_icon = "✅" if completed else "⏸️"
            print(f"  {status_icon} SubTask {subtask_id}: {'completed' if completed else 'pending'}")
        
        # Save state after update
        self.save_state()
        return True
    
    def add_task_evidence(self, task_id: int, evidence: str, subtask_id: str = None) -> bool:
        """Add completion evidence to a task or subtask."""
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return False
        
        if subtask_id:
            # Add evidence to subtask
            subtask = self.get_subtask_by_id(task_id, subtask_id)
            if subtask:
                subtask.completion_evidence.append(evidence)
                if self.verbose:
                    print(f"  📊 Evidence added to SubTask {subtask_id}: {evidence}")
            else:
                return False
        else:
            # Add evidence to main task
            main_task.completion_evidence.append(evidence)
            if self.verbose:
                print(f"📊 Evidence added to Task {task_id}: {evidence}")
        
        # Log evidence addition
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'evidence_added',
            'task_id': task_id,
            'subtask_id': subtask_id,
            'evidence': evidence
        })
        
        # Save state after update
        self.save_state()
        return True
    
    def add_task_observation(self, task_id: int, observation: str, subtask_id: str = None) -> bool:
        """Add observation to a task or subtask."""
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return False
        
        if subtask_id:
            # Add observation to subtask
            subtask = self.get_subtask_by_id(task_id, subtask_id)
            if subtask:
                subtask.observations.append(observation)
            else:
                return False
        else:
            # Add observation to main task
            main_task.observations.append(observation)
        
        # Log observation addition
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'observation_added',
            'task_id': task_id,
            'subtask_id': subtask_id,
            'observation': observation
        })
        
        # Save state after update
        self.save_state()
        return True
    
    def get_task_progress_summary(self) -> Dict[str, Any]:
        """Get comprehensive progress summary of the structured plan."""
        if not self.structured_plan:
            return {"status": "no_plan"}
        
        total_main_tasks = len(self.structured_plan.tasks)
        completed_main_tasks = sum(1 for task in self.structured_plan.tasks if task.status == TaskStatus.COMPLETED)
        in_progress_main_tasks = sum(1 for task in self.structured_plan.tasks if task.status == TaskStatus.IN_PROGRESS)
        
        # Count subtasks
        total_subtasks = sum(len(task.subtasks) for task in self.structured_plan.tasks)
        completed_subtasks = sum(
            sum(1 for subtask in task.subtasks if subtask.completed)
            for task in self.structured_plan.tasks
        )
        
        # Calculate overall progress percentage
        if total_main_tasks > 0:
            main_progress = (completed_main_tasks / total_main_tasks) * 100
        else:
            main_progress = 0
            
        if total_subtasks > 0:
            subtask_progress = (completed_subtasks / total_subtasks) * 100
        else:
            subtask_progress = 0
        
        # Overall progress (weighted average)
        if total_subtasks > 0:
            overall_progress = (main_progress * 0.6) + (subtask_progress * 0.4)
        else:
            overall_progress = main_progress
        
        return {
            "total_main_tasks": total_main_tasks,
            "completed_main_tasks": completed_main_tasks,
            "in_progress_main_tasks": in_progress_main_tasks,
            "total_subtasks": total_subtasks,
            "completed_subtasks": completed_subtasks,
            "main_task_progress_percentage": round(main_progress, 1),
            "subtask_progress_percentage": round(subtask_progress, 1),
            "overall_progress_percentage": round(overall_progress, 1),
            "execution_history_entries": len(self.execution_history)
        }
    
    def get_task_evidence_summary(self, task_id: int) -> Dict[str, Any]:
        """Get evidence summary for a specific task."""
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return {"error": f"Task {task_id} not found"}
        
        # Collect evidence from main task and subtasks
        main_evidence = main_task.completion_evidence
        main_observations = main_task.observations
        
        subtask_evidence = {}
        subtask_observations = {}
        
        for subtask in main_task.subtasks:
            subtask_evidence[subtask.id] = subtask.completion_evidence
            subtask_observations[subtask.id] = subtask.observations
        
        return {
            "task_id": task_id,
            "task_description": main_task.description,
            "task_status": main_task.status.value,
            "main_task_evidence": main_evidence,
            "main_task_observations": main_observations,
            "subtask_evidence": subtask_evidence,
            "subtask_observations": subtask_observations,
            "total_evidence_items": len(main_evidence) + sum(len(ev) for ev in subtask_evidence.values()),
            "total_observations": len(main_observations) + sum(len(obs) for obs in subtask_observations.values())
        }
    
    def modify_task_in_plan(self, task_id: int, description: str = None, predicted_tools: List[str] = None) -> bool:
        """Modify an existing task in the structured plan."""
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return False
        
        old_description = main_task.description
        old_tools = main_task.predicted_tool_use.copy()
        
        if description:
            main_task.description = description
        
        if predicted_tools:
            main_task.predicted_tool_use = predicted_tools
        
        # Log modification
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'task_modified',
            'task_id': task_id,
            'old_description': old_description,
            'new_description': description,
            'old_tools': old_tools,
            'new_tools': predicted_tools
        })
        
        if self.verbose:
            print(f"📝 Modified Task {task_id}")
            if description:
                print(f"  Description: {old_description} → {description}")
            if predicted_tools:
                print(f"  Tools: {old_tools} → {predicted_tools}")
        
        # Save state after modification
        self.save_state()
        return True
    
    def add_subtask_to_plan(self, main_task_id: int, subtask_id: str, description: str) -> bool:
        """Add a new subtask to an existing main task."""
        main_task = self.get_main_task_by_id(main_task_id)
        if not main_task:
            return False
        
        # Check if subtask ID already exists
        for existing_subtask in main_task.subtasks:
            if existing_subtask.id == subtask_id:
                if self.verbose:
                    print(f"⚠️ SubTask {subtask_id} already exists in Task {main_task_id}")
                return False
        
        # Create new subtask
        from .models import SubTask
        new_subtask = SubTask(id=subtask_id, description=description)
        main_task.subtasks.append(new_subtask)
        
        # Log addition
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'subtask_added',
            'main_task_id': main_task_id,
            'subtask_id': subtask_id,
            'description': description
        })
        
        if self.verbose:
            print(f"➕ Added SubTask {subtask_id} to Task {main_task_id}: {description}")
        
        # Save state after addition
        self.save_state()
        return True
    
    def get_execution_analytics(self) -> Dict[str, Any]:
        """Get analytics about execution history and patterns."""
        if not self.execution_history:
            return {"status": "no_history"}
        
        # Categorize history entries
        entry_types = {}
        task_updates = []
        evidence_counts = {}
        observation_counts = {}
        
        for entry in self.execution_history:
            entry_type = entry.get('type', 'unknown')
            entry_types[entry_type] = entry_types.get(entry_type, 0) + 1
            
            if entry_type in ['main_task_status_update', 'subtask_status_update']:
                task_updates.append(entry)
            
            task_id = entry.get('task_id')
            if task_id and entry_type == 'evidence_added':
                evidence_counts[task_id] = evidence_counts.get(task_id, 0) + 1
            
            if task_id and entry_type == 'observation_added':
                observation_counts[task_id] = observation_counts.get(task_id, 0) + 1
        
        # Calculate time metrics if we have timestamps
        timestamps = [entry.get('timestamp') for entry in self.execution_history if entry.get('timestamp')]
        
        return {
            "total_history_entries": len(self.execution_history),
            "entry_type_breakdown": entry_types,
            "task_updates_count": len(task_updates),
            "evidence_counts_by_task": evidence_counts,
            "observation_counts_by_task": observation_counts,
            "most_active_task": max(evidence_counts, key=evidence_counts.get) if evidence_counts else None,
            "timestamp_range": {
                "first": min(timestamps) if timestamps else None,
                "last": max(timestamps) if timestamps else None
            }
        }
    
    def update_task_status(self, task_id: str, status: str, evidence: Dict = None, reason: str = None, iteration: int = None) -> Dict[str, Any]:
        """Update task status with evidence - simplified for structured planning."""
        if self.verbose:
            print(f"📝 Task status update: {task_id} -> {status}")
        
        # Log the update for backward compatibility
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'task_id': task_id,
            'status': status,
            'reason': reason,
            'evidence': evidence,
            'iteration': iteration
        })
        
        # Save state
        self.save_state()
        
        return {"success": True, "task_id": task_id, "status": status}
    
    def mark_complete(self, task_id: str, confidence: float = 1.0) -> bool:
        """Mark a task as complete with confidence score."""
        result = self.update_task_status(
            task_id, 
            'completed',
            evidence={'confidence': confidence}
        )
        return result.get('success', False)
    
    def all_tasks_complete(self) -> bool:
        """Check if all tasks are complete - simplified."""
        # For structured plans, check if all main tasks are completed
        if self.structured_plan:
            return all(task.status == TaskStatus.COMPLETED for task in self.structured_plan.tasks)
        return True
    
    def save_state(self):
        """Save current task state to JSON."""
        state_data = {
            'timestamp': datetime.now().isoformat(),
            'structured_plan': self.structured_plan.model_dump(mode='json') if self.structured_plan else None,
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
                
                # Reconstruct structured plan
                if state_data.get('structured_plan'):
                    self.structured_plan = TodoList.model_validate(state_data['structured_plan'])
                
                self.execution_history = state_data.get('execution_history', [])
                
                if self.verbose:
                    plan_info = f" with structured plan" if self.structured_plan else ""
                    print(f"📂 Loaded task state{plan_info}")
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Failed to load task state: {e}")
    
    # === Simplified Task Management ===
    
    def update_task_progress(self, iteration: int) -> None:
        """Update task progress - simplified for structured planning."""
        if self.verbose:
            print(f"📝 Task progress update at iteration {iteration}")
        self.save_state()
    
    def is_checklist_complete(self) -> bool:
        """Check if all tasks are completed."""
        return self.all_tasks_complete()
    
    def get_incomplete_tasks(self) -> List[Dict[str, Any]]:
        """Get list of incomplete tasks from structured plan."""
        incomplete = []
        
        if self.structured_plan:
            for task in self.structured_plan.tasks:
                if task.status != TaskStatus.COMPLETED:
                    incomplete.append({
                        "id": task.id,
                        "description": task.description,
                        "status": task.status.value
                    })
        
        return incomplete
    
    def get_task_status_prompt(self, iteration: int) -> str:
        """Generate simplified analysis direction prompt."""
        all_complete = self.all_tasks_complete()
        
        if all_complete:
            return (
                "Analyze the latest tool observations. Based on your analysis, either: "
                "(a) call another tool to continue iterating, or "
                "(b) produce a FINAL ANSWER preceded by 'Final Answer:' (all tasks are complete)."
            )
        else:
            return (
                "Analyze the latest tool observations and continue working. "
                "Call the appropriate tool to make progress toward your goal."
            )

    # === Advanced Task Management ===
    
    def add_main_task_to_plan(self, task_id: int, description: str, predicted_tools: List[str] = None, insert_after: int = None) -> bool:
        """Add a new main task to the structured plan.
        
        Args:
            task_id: ID for the new task
            description: Task description
            predicted_tools: Tools predicted for this task
            insert_after: Task ID to insert after (None = append to end)
            
        Returns:
            True if task added successfully
        """
        if not self.structured_plan:
            if self.verbose:
                print("⚠️ Cannot add task: no structured plan loaded")
            return False
        
        # Check if task ID already exists
        for existing_task in self.structured_plan.tasks:
            if existing_task.id == task_id:
                if self.verbose:
                    print(f"⚠️ Task {task_id} already exists")
                return False
        
        # Create new main task
        from .models import MainTask
        new_task = MainTask(
            id=task_id,
            description=description,
            predicted_tool_use=predicted_tools or []
        )
        
        # Insert at appropriate position
        if insert_after is None:
            # Append to end
            self.structured_plan.tasks.append(new_task)
        else:
            # Find insertion point
            insert_idx = -1
            for i, task in enumerate(self.structured_plan.tasks):
                if task.id == insert_after:
                    insert_idx = i + 1
                    break
            
            if insert_idx >= 0:
                self.structured_plan.tasks.insert(insert_idx, new_task)
            else:
                # If insert_after not found, append to end
                self.structured_plan.tasks.append(new_task)
        
        # Log addition
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_added',
            'task_id': task_id,
            'description': description,
            'predicted_tools': predicted_tools,
            'insert_after': insert_after
        })
        
        if self.verbose:
            position = f"after Task {insert_after}" if insert_after else "at end"
            print(f"➕ Added Main Task {task_id} {position}: {description}")
        
        # Save state after addition
        self.save_state()
        return True
    
    def remove_main_task_from_plan(self, task_id: int, reason: str = "Manual removal") -> bool:
        """Remove a main task from the structured plan.
        
        Args:
            task_id: ID of task to remove
            reason: Reason for removal
            
        Returns:
            True if task removed successfully
        """
        if not self.structured_plan:
            return False
        
        # Find and remove task
        task_to_remove = None
        remove_idx = -1
        
        for i, task in enumerate(self.structured_plan.tasks):
            if task.id == task_id:
                task_to_remove = task
                remove_idx = i
                break
        
        if not task_to_remove:
            if self.verbose:
                print(f"⚠️ Task {task_id} not found for removal")
            return False
        
        # Remove the task
        self.structured_plan.tasks.pop(remove_idx)
        
        # Log removal
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'main_task_removed',
            'task_id': task_id,
            'description': task_to_remove.description,
            'reason': reason
        })
        
        if self.verbose:
            print(f"❌ Removed Main Task {task_id}: {task_to_remove.description}")
        
        # Save state after removal
        self.save_state()
        return True
    
    def reorder_main_tasks(self, new_order: List[int]) -> bool:
        """Reorder main tasks in the structured plan.
        
        Args:
            new_order: List of task IDs in desired order
            
        Returns:
            True if reordering successful
        """
        if not self.structured_plan:
            return False
        
        # Validate that all task IDs exist and new_order is complete
        existing_ids = {task.id for task in self.structured_plan.tasks}
        new_order_set = set(new_order)
        
        if existing_ids != new_order_set:
            if self.verbose:
                missing = existing_ids - new_order_set
                extra = new_order_set - existing_ids
                print(f"⚠️ Reorder failed: missing {missing}, extra {extra}")
            return False
        
        # Create mapping of ID to task
        task_map = {task.id: task for task in self.structured_plan.tasks}
        
        # Reorder tasks
        try:
            self.structured_plan.tasks = [task_map[task_id] for task_id in new_order]
            
            # Log reordering
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'type': 'tasks_reordered',
                'old_order': list(existing_ids),
                'new_order': new_order
            })
            
            if self.verbose:
                print(f"🔄 Reordered tasks: {new_order}")
            
            # Save state after reordering
            self.save_state()
            return True
            
        except Exception as e:
            if self.verbose:
                print(f"❌ Reorder failed: {e}")
            return False
    
    def mark_task_failed(self, task_id: int, error_message: str, recovery_suggestion: str = None) -> bool:
        """Mark a task as failed and optionally suggest recovery.
        
        Args:
            task_id: ID of the failed task
            error_message: Description of the failure
            recovery_suggestion: Optional suggestion for recovery
            
        Returns:
            True if task marked as failed
        """
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return False
        
        # Update task status to failed
        old_status = main_task.status
        main_task.status = TaskStatus.FAILED
        
        # Add failure information to completion evidence
        failure_info = f"Task failed: {error_message}"
        if recovery_suggestion:
            failure_info += f" | Recovery suggestion: {recovery_suggestion}"
        
        main_task.completion_evidence.append(failure_info)
        
        # Log failure
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'task_failed',
            'task_id': task_id,
            'old_status': old_status.value,
            'error_message': error_message,
            'recovery_suggestion': recovery_suggestion
        })
        
        if self.verbose:
            print(f"❌ Task {task_id} marked as FAILED: {error_message}")
            if recovery_suggestion:
                print(f"  💡 Recovery suggestion: {recovery_suggestion}")
        
        # Save state after failure marking
        self.save_state()
        return True
    
    def retry_failed_task(self, task_id: int, retry_reason: str = "Manual retry") -> bool:
        """Retry a failed task by resetting it to pending.
        
        Args:
            task_id: ID of the failed task to retry
            retry_reason: Reason for retry
            
        Returns:
            True if task reset for retry
        """
        main_task = self.get_main_task_by_id(task_id)
        if not main_task:
            return False
        
        if main_task.status != TaskStatus.FAILED:
            if self.verbose:
                print(f"⚠️ Task {task_id} is not in FAILED status (current: {main_task.status.value})")
            return False
        
        # Reset task status and clear failure evidence
        old_status = main_task.status
        main_task.status = TaskStatus.PENDING
        
        # Reset subtasks if any
        for subtask in main_task.subtasks:
            subtask.completed = False
            subtask.completion_evidence = []
            subtask.observations = []
        
        # Clear task evidence and observations for fresh start
        main_task.completion_evidence = []
        main_task.observations = []
        
        # Log retry
        self.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'task_retried',
            'task_id': task_id,
            'old_status': old_status.value,
            'retry_reason': retry_reason
        })
        
        if self.verbose:
            print(f"🔄 Task {task_id} reset for retry: {retry_reason}")
        
        # Save state after retry
        self.save_state()
        return True
    
    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """Get list of failed tasks with failure information.
        
        Returns:
            List of failed task information
        """
        if not self.structured_plan:
            return []
        
        failed_tasks = []
        
        for task in self.structured_plan.tasks:
            if task.status == TaskStatus.FAILED:
                # Extract failure information from evidence
                failure_evidence = [ev for ev in task.completion_evidence if 'failed' in ev.lower()]
                
                failed_tasks.append({
                    'task_id': task.id,
                    'description': task.description,
                    'failure_evidence': failure_evidence,
                    'total_evidence': len(task.completion_evidence),
                    'observations': len(task.observations)
                })
        
        return failed_tasks
    
    def get_plan_health_status(self) -> Dict[str, Any]:
        """Get overall health status of the plan execution.
        
        Returns:
            Dictionary with plan health metrics
        """
        if not self.structured_plan:
            return {"status": "no_plan"}
        
        # Count tasks by status
        status_counts = {}
        for status in TaskStatus:
            status_counts[status.value] = sum(1 for task in self.structured_plan.tasks if task.status == status)
        
        total_tasks = len(self.structured_plan.tasks)
        
        # Calculate health score
        completed = status_counts.get('completed', 0)
        failed = status_counts.get('failed', 0)
        blocked = status_counts.get('blocked', 0)
        
        # Health score: (completed - failed - blocked) / total
        health_score = ((completed - failed - blocked) / total_tasks) if total_tasks > 0 else 0
        health_score = max(0, min(1, health_score))  # Clamp between 0 and 1
        
        # Determine health status
        if health_score >= 0.8:
            health_status = "excellent"
        elif health_score >= 0.6:
            health_status = "good"
        elif health_score >= 0.4:
            health_status = "fair"
        elif health_score >= 0.2:
            health_status = "poor"
        else:
            health_status = "critical"
        
        return {
            "health_status": health_status,
            "health_score": round(health_score, 2),
            "total_tasks": total_tasks,
            "status_breakdown": status_counts,
            "completion_rate": round((completed / total_tasks) * 100, 1) if total_tasks > 0 else 0,
            "failure_rate": round((failed / total_tasks) * 100, 1) if total_tasks > 0 else 0,
            "blocked_rate": round((blocked / total_tasks) * 100, 1) if total_tasks > 0 else 0,
            "active_execution": status_counts.get('in_progress', 0) > 0
        }


