# Production-Level Task Management Implementation Plan

## Overview
Transform the current checklist system into a robust, production-ready task management framework while maintaining compatibility with your existing `BaseAgent` architecture.

## Phase 1: Enhanced Task Model & State Machine

### 1.1 Create New Task Models
**File:** `task_models.py` (new file)

```python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional, Callable, Set
from datetime import datetime

class TaskStatus(Enum):
    PENDING = "pending"
    BLOCKED = "blocked"  # Dependencies not met
    READY = "ready"      # Dependencies met, can start
    IN_PROGRESS = "in_progress"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskPriority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4

@dataclass
class TaskValidation:
    """Validation criteria for task completion"""
    required_outputs: List[str] = field(default_factory=list)
    validation_function: Optional[str] = None  # Name of validation tool
    success_indicators: List[str] = field(default_factory=list)
    min_confidence: float = 0.8

@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: Set[str] = field(default_factory=set)
    
    # Tool associations
    required_tools: List[str] = field(default_factory=list)
    expected_tool_sequence: List[str] = field(default_factory=list)
    
    # Validation
    validation: Optional[TaskValidation] = None
    completion_evidence: Dict[str, Any] = field(default_factory=dict)
    
    # Execution metadata
    max_attempts: int = 3
    current_attempt: int = 0
    timeout_iterations: int = 10
    
    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
```

### 1.2 Upgrade ChecklistManager to TaskManager
**File:** `task_manager.py` (replacement for checklist_manager.py)

```python
import networkx as nx
from typing import List, Dict, Any, Optional, Tuple
from .task_models import Task, TaskStatus, TaskPriority

class TaskManager:
    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.task_graph = nx.DiGraph()
        self.tasks: Dict[str, Task] = {}
        self.execution_history: List[Dict] = []
        
        # File paths (maintain compatibility)
        self.checklist_path = Path(__file__).parent.parent / "agent_output" / "agent_checklist.json"
        self.state_path = Path(__file__).parent.parent / "agent_output" / "task_state.json"
        
    def add_task(self, task: Task, dependencies: List[str] = None):
        """Add task with dependency management"""
        self.tasks[task.id] = task
        self.task_graph.add_node(task.id)
        
        if dependencies:
            for dep_id in dependencies:
                self.task_graph.add_edge(dep_id, task.id)
                task.dependencies.add(dep_id)
        
        self._update_task_states()
    
    def _update_task_states(self):
        """Update task states based on dependencies"""
        for task_id, task in self.tasks.items():
            if task.status == TaskStatus.PENDING:
                if self._dependencies_met(task_id):
                    task.status = TaskStatus.READY
                else:
                    task.status = TaskStatus.BLOCKED
    
    def get_next_tasks(self, max_parallel: int = 1) -> List[Task]:
        """Get next executable tasks considering dependencies"""
        ready_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.READY
        ]
        # Sort by priority
        ready_tasks.sort(key=lambda t: (t.priority.value, t.created_at))
        return ready_tasks[:max_parallel]
```

## Phase 2: Structured Task Protocol & Validation

### 2.1 Add Validation Tools to BaseAgent
**Modifications to:** `agent.py`

```python
def _register_task_management_tools(self):
    """Register task management tools for structured updates"""
    
    # Mark task complete with evidence
    self.add_tool(
        name="update_task_status",
        description="Update the status of a task with evidence",
        parameters={
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task identifier"},
                "status": {
                    "type": "string", 
                    "enum": ["started", "completed", "failed", "blocked"],
                    "description": "New task status"
                },
                "evidence": {
                    "type": "object",
                    "description": "Evidence supporting the status change",
                    "properties": {
                        "outputs": {"type": "object"},
                        "observations": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1}
                    }
                },
                "reason": {"type": "string", "description": "Explanation for status change"}
            },
            "required": ["task_id", "status"]
        },
        function=lambda **kwargs: self.task_manager.update_task_status(**kwargs)
    )
    
    # Request task replanning
    self.add_tool(
        name="replan_tasks",
        description="Request replanning when current plan is blocked or ineffective",
        parameters={
            "type": "object",
            "properties": {
                "reason": {"type": "string"},
                "blocked_tasks": {"type": "array", "items": {"type": "string"}},
                "new_approach": {"type": "string"}
            },
            "required": ["reason"]
        },
        function=lambda **kwargs: self.task_manager.replan(**kwargs)
    )
```

### 2.2 Automatic Validation System
**File:** `task_validator.py` (new file)

```python
class TaskValidator:
    """Validates task completion based on evidence"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        self.validators: Dict[str, Callable] = {}
        self._register_default_validators()
    
    def validate_task_completion(
        self, 
        task: Task, 
        tool_executions: List[Dict],
        observations: List[Any]
    ) -> Tuple[bool, float, str]:
        """
        Returns: (is_complete, confidence, explanation)
        """
        # Check required outputs
        if task.validation and task.validation.required_outputs:
            for required in task.validation.required_outputs:
                if required not in task.outputs:
                    return False, 0.0, f"Missing required output: {required}"
        
        # Check tool execution sequence
        if task.expected_tool_sequence:
            executed_tools = [exec['tool_name'] for exec in tool_executions]
            if not self._sequence_matches(task.expected_tool_sequence, executed_tools):
                return False, 0.5, "Tool sequence doesn't match expected pattern"
        
        # Run custom validator if specified
        if task.validation and task.validation.validation_function:
            validator = self.validators.get(task.validation.validation_function)
            if validator:
                return validator(task, tool_executions, observations)
        
        # Check success indicators in observations
        if task.validation and task.validation.success_indicators:
            confidence = self._check_indicators(
                task.validation.success_indicators,
                observations
            )
            is_complete = confidence >= task.validation.min_confidence
            return is_complete, confidence, f"Indicator match confidence: {confidence}"
        
        return True, 1.0, "No validation criteria specified"
```

## Phase 3: Event-Driven Architecture

### 3.1 Event System Integration
**File:** `agent_events.py` (new file)

```python
from typing import Callable, List, Dict, Any
from enum import Enum

class AgentEvent(Enum):
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TOOL_EXECUTED = "tool_executed"
    ITERATION_COMPLETE = "iteration_complete"
    PLAN_CREATED = "plan_created"
    VALIDATION_REQUIRED = "validation_required"
    REPLAN_REQUESTED = "replan_requested"

class EventManager:
    def __init__(self):
        self.listeners: Dict[AgentEvent, List[Callable]] = {}
        
    def on(self, event: AgentEvent, handler: Callable):
        """Register event handler"""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(handler)
        
    def emit(self, event: AgentEvent, data: Dict[str, Any]):
        """Emit event to all listeners"""
        if event in self.listeners:
            for handler in self.listeners[event]:
                try:
                    handler(data)
                except Exception as e:
                    print(f"Event handler error: {e}")
```

### 3.2 Integrate Events into BaseAgent
**Modifications to:** `agent.py`

```python
def __init__(self, ...):
    # ... existing init code ...
    
    # Initialize event system
    self.event_manager = EventManager()
    self.task_manager = TaskManager(verbose=verbose)
    
    # Register event handlers
    self._register_event_handlers()

def _register_event_handlers(self):
    """Set up event-driven task management"""
    
    @self.event_manager.on(AgentEvent.TOOL_EXECUTED)
    def on_tool_executed(data: Dict):
        # Auto-detect task progress from tool execution
        tool_name = data['tool_name']
        result = data['result']
        
        current_task = self.task_manager.get_current_task()
        if current_task and tool_name in current_task.required_tools:
            # Update task outputs
            current_task.outputs[tool_name] = result
            
            # Check if task is complete
            is_complete, confidence, reason = self.task_validator.validate_task_completion(
                current_task,
                self.recent_tool_executions,
                self.recent_observations
            )
            
            if is_complete:
                self.event_manager.emit(
                    AgentEvent.TASK_COMPLETED,
                    {'task': current_task, 'confidence': confidence}
                )
    
    @self.event_manager.on(AgentEvent.TASK_COMPLETED)
    def on_task_completed(data: Dict):
        task = data['task']
        self.task_manager.mark_complete(task.id, data['confidence'])
        
        # Start next task automatically
        next_tasks = self.task_manager.get_next_tasks()
        if next_tasks:
            self.task_manager.start_task(next_tasks[0].id)
            self.event_manager.emit(
                AgentEvent.TASK_STARTED,
                {'task': next_tasks[0]}
            )
```

## Phase 4: Dynamic Replanning & Recovery

### 4.1 Replanning System
**File:** `task_replanner.py` (new file)

```python
class TaskReplanner:
    """Handles dynamic replanning when tasks fail or get blocked"""
    
    def __init__(self, agent, task_manager: TaskManager):
        self.agent = agent
        self.task_manager = task_manager
        
    def analyze_failure(self, task: Task) -> Dict[str, Any]:
        """Analyze why a task failed"""
        return {
            'task_id': task.id,
            'failure_reasons': task.errors,
            'attempted_tools': list(task.outputs.keys()),
            'iterations_spent': task.timeout_iterations,
            'dependencies_status': {
                dep_id: self.task_manager.tasks[dep_id].status
                for dep_id in task.dependencies
            }
        }
    
    def generate_recovery_plan(self, failed_task: Task) -> List[Task]:
        """Generate alternative tasks to recover from failure"""
        analysis = self.analyze_failure(failed_task)
        
        # Use LLM to generate recovery plan
        recovery_prompt = f"""
        Task "{failed_task.description}" failed.
        Failure analysis: {json.dumps(analysis, indent=2)}
        
        Generate a recovery plan with alternative tasks.
        Return JSON: {{"recovery_tasks": [...]}}
        """
        
        # Call LLM to generate recovery tasks
        response = self.agent.llm.complete(recovery_prompt)
        recovery_data = json.loads(response)
        
        return self._parse_recovery_tasks(recovery_data)
    
    def handle_blocked_tasks(self, blocked_tasks: List[Task]):
        """Handle tasks blocked by dependencies"""
        for task in blocked_tasks:
            # Check if dependencies are truly unresolvable
            if self._dependencies_permanently_failed(task):
                # Mark as skipped and find alternatives
                task.status = TaskStatus.SKIPPED
                alternatives = self.generate_alternative_path(task)
                for alt_task in alternatives:
                    self.task_manager.add_task(alt_task)
```

### 4.2 Rollback Capabilities
**Modifications to:** `task_manager.py`

```python
class TaskManager:
    # ... existing code ...
    
    def create_checkpoint(self) -> str:
        """Create a checkpoint of current state"""
        checkpoint_id = f"checkpoint_{datetime.now().isoformat()}"
        checkpoint_data = {
            'id': checkpoint_id,
            'timestamp': datetime.now().isoformat(),
            'tasks': {
                task_id: self._task_to_dict(task)
                for task_id, task in self.tasks.items()
            },
            'graph': nx.node_link_data(self.task_graph),
            'execution_history': self.execution_history.copy()
        }
        
        # Save to checkpoint file
        checkpoint_path = self.state_path.parent / f"{checkpoint_id}.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)
        
        return checkpoint_id
    
    def rollback_to_checkpoint(self, checkpoint_id: str):
        """Rollback to a previous checkpoint"""
        checkpoint_path = self.state_path.parent / f"{checkpoint_id}.json"
        
        with open(checkpoint_path, 'r') as f:
            checkpoint_data = json.load(f)
        
        # Restore state
        self.tasks = {
            task_id: self._dict_to_task(task_data)
            for task_id, task_data in checkpoint_data['tasks'].items()
        }
        self.task_graph = nx.node_link_graph(checkpoint_data['graph'])
        self.execution_history = checkpoint_data['execution_history']
```

## Phase 5: Enhanced Monitoring & Persistence

### 5.1 Structured Logging
**File:** `task_logger.py` (enhancement of manage_logger.py)

```python
class EnhancedTaskLogger(MessageLogger):
    """Extended logger with task-specific tracking"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_metrics_path = Path(__file__).parent.parent / "agent_output" / "task_metrics.json"
        
    def log_task_event(self, event_type: str, task: Task, metadata: Dict = None):
        """Log task-specific events with metrics"""
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'task_id': task.id,
            'task_status': task.status.value,
            'task_priority': task.priority.value,
            'iteration': metadata.get('iteration') if metadata else None,
            'duration_ms': self._calculate_duration(task),
            'attempt_number': task.current_attempt,
            'metadata': metadata or {}
        }
        
        # Append to metrics file
        self._append_to_metrics(event_data)
        
    def generate_execution_report(self) -> Dict:
        """Generate comprehensive execution report"""
        return {
            'total_tasks': len(self.task_manager.tasks),
            'completed_tasks': sum(
                1 for t in self.task_manager.tasks.values()
                if t.status == TaskStatus.COMPLETED
            ),
            'failed_tasks': sum(
                1 for t in self.task_manager.tasks.values()
                if t.status == TaskStatus.FAILED
            ),
            'average_completion_time': self._calculate_avg_completion_time(),
            'tool_usage_stats': self._calculate_tool_usage(),
            'bottlenecks': self._identify_bottlenecks(),
            'recovery_actions': self._count_recovery_actions()
        }
```

### 5.2 Real-time State Persistence
**Modifications to:** `agent.py`

```python
def run(self) -> Dict[str, Any]:
    # ... existing code ...
    
    # Add persistence hooks
    for i in range(1, self.max_iterations + 1):
        # ... iteration logic ...
        
        # Save state after each iteration
        self._persist_state(i)
        
        # Check for recovery needed
        if self._should_recover():
            self._execute_recovery()

def _persist_state(self, iteration: int):
    """Persist complete agent state"""
    state = {
        'iteration': iteration,
        'timestamp': datetime.now().isoformat(),
        'tasks': self.task_manager.export_state(),
        'messages': self.message_logger.get_recent_messages(10),
        'trace': [self.utilities.trace_to_dict(s) for s in self.trace[-5:]],
        'metrics': {
            'total_tokens': self.total_tokens,
            'stuck_count': self._stuck_count,
            'active_task': self.task_manager.get_current_task().id if self.task_manager.get_current_task() else None
        }
    }
    
    # Atomic write with rotation
    temp_path = self.task_manager.state_path.with_suffix('.tmp')
    with open(temp_path, 'w') as f:
        json.dump(state, f, indent=2)
    temp_path.replace(self.task_manager.state_path)
```

## Phase 6: Integration Steps

### 6.1 Backward Compatibility Layer
Create a compatibility wrapper to maintain existing functionality:

```python
class ChecklistCompatibilityWrapper:
    """Maintains backward compatibility with existing checklist system"""
    
    def __init__(self, task_manager: TaskManager):
        self.task_manager = task_manager
        
    def parse_plan_to_checklist(self, content: str, trace_length: int) -> bool:
        """Convert old-style plan to new task system"""
        # Parse existing JSON plan format
        # Convert to Task objects
        # Add to TaskManager
        pass
    
    def is_checklist_complete(self) -> bool:
        """Check if all tasks are complete"""
        return self.task_manager.all_tasks_complete()
```

### 6.2 Migration Script
**File:** `migrate_to_task_system.py`

```python
def migrate_existing_agent():
    """Migrate existing agent to new task system"""
    
    # 1. Update imports in agent.py
    # 2. Replace ChecklistManager with TaskManager
    # 3. Add event system initialization
    # 4. Update tool registration
    # 5. Modify run loop for event emission
    
    print("Migration steps:")
    print("1. Backup existing files")
    print("2. Install dependencies: pip install networkx")
    print("3. Run migration script")
    print("4. Test with existing prompts")
    print("5. Gradually adopt new features")
```

## Implementation Timeline

### Core Infrastructure
- Implement Task models and TaskManager
- Create TaskValidator
- Set up backward compatibility

### Event System
- Implement EventManager
- Integrate events into BaseAgent
- Add automatic validation

### Advanced Features
- Implement replanning system
- Add rollback capabilities
- Enhance monitoring

### Testing & Optimization
- Comprehensive testing
- Performance optimization
- Documentation

## Testing Strategy

```python
class TaskSystemTests:
    def test_backward_compatibility(self):
        """Ensure old checklist format still works"""
        pass
    
    def test_dependency_management(self):
        """Test task dependencies and blocking"""
        pass
    
    def test_automatic_validation(self):
        """Test automatic task completion detection"""
        pass
    
    def test_recovery_planning(self):
        """Test failure recovery and replanning"""
        pass
    
    def test_parallel_execution(self):
        """Test parallel task execution"""
        pass
```

## Configuration

Add to your agent initialization:

```python
agent = BaseAgent(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
    task_config={
        'validation_mode': 'automatic',  # or 'manual', 'hybrid'
        'max_parallel_tasks': 3,
        'enable_replanning': True,
        'checkpoint_frequency': 5,  # iterations
        'failure_recovery': 'automatic',
        'backward_compatible': True  # For gradual migration
    }
)
```

This implementation plan provides a production-ready upgrade path that maintains your existing structure while adding sophisticated task management capabilities suitable for complex, mission-critical agent workflows.