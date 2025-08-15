"""Task models for enhanced task management in BaseAgent."""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime


class TaskStatus(Enum):
    """Task status states."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Task priority levels."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class TaskValidation:
    """Validation criteria for task completion."""
    required_outputs: List[str] = field(default_factory=list)
    validation_function: Optional[str] = None  # Name of validation tool
    success_indicators: List[str] = field(default_factory=list)
    min_confidence: float = 0.8


@dataclass
class Task:
    """Enhanced task model with validation and tracking."""
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Dependencies (simple list of task IDs for now)
    dependencies: List[str] = field(default_factory=list)
    
    # Tool associations
    required_tools: List[str] = field(default_factory=list)
    expected_tool_sequence: List[str] = field(default_factory=list)
    
    # Validation
    validation: Optional[TaskValidation] = None
    completion_evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Execution metadata
    max_attempts: int = 3
    current_attempt: int = 0
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Context and outputs
    context: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    
    # Iteration tracking for compatibility
    started_at_iteration: Optional[int] = None
    completed_at_iteration: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for JSON serialization."""
        return {
            'id': self.id,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'dependencies': self.dependencies,
            'required_tools': self.required_tools,
            'expected_tool_sequence': self.expected_tool_sequence,
            'completion_evidence': self.completion_evidence,
            'current_attempt': self.current_attempt,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'started_at_iteration': self.started_at_iteration,
            'completed_at_iteration': self.completed_at_iteration,
            'outputs': self.outputs,
            'errors': self.errors
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        """Create task from dictionary."""
        task = cls(
            id=data.get('id', ''),
            description=data.get('description', ''),
            status=TaskStatus(data.get('status', 'pending')),
            priority=TaskPriority(data.get('priority', 3))
        )
        
        # Set optional fields
        task.dependencies = data.get('dependencies', [])
        task.required_tools = data.get('required_tools', [])
        task.expected_tool_sequence = data.get('expected_tool_sequence', [])
        task.completion_evidence = data.get('completion_evidence', {})
        task.current_attempt = data.get('current_attempt', 0)
        task.outputs = data.get('outputs', {})
        task.errors = data.get('errors', [])
        task.started_at_iteration = data.get('started_at_iteration')
        task.completed_at_iteration = data.get('completed_at_iteration')
        
        # Parse datetime fields
        if data.get('started_at'):
            try:
                task.started_at = datetime.fromisoformat(data['started_at'])
            except:
                pass
        
        if data.get('completed_at'):
            try:
                task.completed_at = datetime.fromisoformat(data['completed_at'])
            except:
                pass
        
        return task
