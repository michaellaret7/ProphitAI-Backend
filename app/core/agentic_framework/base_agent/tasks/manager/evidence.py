"""Task evidence and observation tracking."""

from datetime import datetime
from typing import Dict, Any
from .core import TaskManagerCore


class TaskEvidenceManager:
    """Manages completion evidence and observations for tasks.

    Responsibilities:
    - Add evidence to tasks/subtasks
    - Add observations to tasks/subtasks
    - Retrieve evidence summaries
    """

    def __init__(self, core: TaskManagerCore):
        """Initialize evidence manager.

        Args:
            core: Core task manager for state access
        """
        self.core = core

    def add_evidence(self, task_id: int, evidence: str, subtask_id: str = None) -> bool:
        """Add completion evidence to a task or subtask.

        Args:
            task_id: Main task ID
            evidence: Evidence string to add
            subtask_id: Optional subtask ID

        Returns:
            True if evidence added successfully
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            return False

        if subtask_id:
            # Add evidence to subtask
            subtask = self.core.get_subtask_by_id(task_id, subtask_id)
            if subtask:
                subtask.completion_evidence.append(evidence)
                if self.core.verbose:
                    print(f"  Evidence added to SubTask {subtask_id}: {evidence}")
            else:
                return False
        else:
            # Add evidence to main task
            main_task.completion_evidence.append(evidence)
            if self.core.verbose:
                print(f"Evidence added to Task {task_id}: {evidence}")

        # Log evidence addition
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'evidence_added',
            'task_id': task_id,
            'subtask_id': subtask_id,
            'evidence': evidence
        })

        return True

    def add_observation(self, task_id: int, observation: str, subtask_id: str = None) -> bool:
        """Add observation to a task or subtask.

        Args:
            task_id: Main task ID
            observation: Observation string to add
            subtask_id: Optional subtask ID

        Returns:
            True if observation added successfully
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            return False

        if subtask_id:
            # Add observation to subtask
            subtask = self.core.get_subtask_by_id(task_id, subtask_id)
            if subtask:
                subtask.observations.append(observation)
            else:
                return False
        else:
            # Add observation to main task
            main_task.observations.append(observation)

        # Log observation addition
        self.core.execution_history.append({
            'timestamp': datetime.now().isoformat(),
            'type': 'observation_added',
            'task_id': task_id,
            'subtask_id': subtask_id,
            'observation': observation
        })

        return True

    def get_evidence_summary(self, task_id: int) -> Dict[str, Any]:
        """Get evidence summary for a specific task.

        Args:
            task_id: Main task ID

        Returns:
            Dict containing all evidence and observations for task and subtasks with success field
        """
        main_task = self.core.get_main_task_by_id(task_id)
        if not main_task:
            return {"success": False, "error": f"Task {task_id} not found"}

        # Collect evidence from main task and subtasks
        main_evidence = main_task.completion_evidence
        main_observations = main_task.observations

        subtask_evidence = {}
        subtask_observations = {}

        for subtask in main_task.subtasks:
            subtask_evidence[subtask.id] = subtask.completion_evidence
            subtask_observations[subtask.id] = subtask.observations

        return {
            "success": True,
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
