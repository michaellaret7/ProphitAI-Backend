"""Event system for agent task management."""

from typing import Callable, List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class AgentEvent(Enum):
    """Core agent events."""
    # Task lifecycle events
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_BLOCKED = "task_blocked"
    TASK_SKIPPED = "task_skipped"
    
    # Tool execution events
    TOOL_EXECUTED = "tool_executed"
    TOOL_FAILED = "tool_failed"
    
    # Agent lifecycle events
    ITERATION_COMPLETE = "iteration_complete"
    PLAN_CREATED = "plan_created"
    
    # Validation events
    VALIDATION_REQUIRED = "validation_required"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"


class EventManager:
    """Simple event manager for agent operations."""
    
    def __init__(self, verbose: bool = False):
        """Initialize event manager.
        
        Args:
            verbose: Whether to print event notifications
        """
        self.verbose = verbose
        self.listeners: Dict[AgentEvent, List[Callable]] = {}
        self.event_history: List[Dict[str, Any]] = []
        self._max_history = 100  # Keep last 100 events
        
    def on(self, event: AgentEvent, handler: Callable) -> None:
        """Register an event handler.
        
        Args:
            event: The event type to listen for
            handler: Callable that will be invoked with event data
        """
        if event not in self.listeners:
            self.listeners[event] = []
        
        if handler not in self.listeners[event]:
            self.listeners[event].append(handler)
            
            if self.verbose:
                print(f"📡 Registered handler for {event.value}")
    
    def off(self, event: AgentEvent, handler: Callable) -> None:
        """Unregister an event handler.
        
        Args:
            event: The event type
            handler: The handler to remove
        """
        if event in self.listeners and handler in self.listeners[event]:
            self.listeners[event].remove(handler)
    
    def emit(self, event: AgentEvent, data: Dict[str, Any] = None) -> None:
        """Emit an event to all registered listeners.
        
        Args:
            event: The event to emit
            data: Optional data to pass to handlers
        """
        if data is None:
            data = {}
        
        # Add metadata
        event_data = {
            'event': event.value,
            'timestamp': datetime.now().isoformat(),
            'data': data
        }
        
        # Record in history
        self.event_history.append(event_data)
        if len(self.event_history) > self._max_history:
            self.event_history.pop(0)
        
        if self.verbose:
            print(f"🟢 Event: {event.value}")
            if data:
                # Print key data points
                if 'task_id' in data:
                    print(f"   Task: {data['task_id']}")
                if 'tool_name' in data:
                    print(f"   Tool: {data['tool_name']}")
        
        # Call all registered handlers
        if event in self.listeners:
            for handler in self.listeners[event]:
                try:
                    handler(data)
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️ Event handler error for {event.value}: {e}")
    
    def emit_task_started(self, task_id: str, task_description: str = None) -> None:
        """Convenience method to emit task started event."""
        self.emit(AgentEvent.TASK_STARTED, {
            'task_id': task_id,
            'description': task_description
        })
    
    def emit_task_completed(self, task_id: str, outputs: Dict = None, confidence: float = 1.0) -> None:
        """Convenience method to emit task completed event."""
        self.emit(AgentEvent.TASK_COMPLETED, {
            'task_id': task_id,
            'outputs': outputs or {},
            'confidence': confidence
        })
    
    def emit_task_failed(self, task_id: str, error: str = None) -> None:
        """Convenience method to emit task failed event."""
        self.emit(AgentEvent.TASK_FAILED, {
            'task_id': task_id,
            'error': error
        })
    
    def emit_tool_executed(self, tool_name: str, args: Dict, result: Any) -> None:
        """Convenience method to emit tool executed event."""
        self.emit(AgentEvent.TOOL_EXECUTED, {
            'tool_name': tool_name,
            'args': args,
            'result': result
        })
    
    def get_event_history(self, event_type: Optional[AgentEvent] = None) -> List[Dict[str, Any]]:
        """Get event history, optionally filtered by type.
        
        Args:
            event_type: Optional event type to filter by
            
        Returns:
            List of event records
        """
        if event_type is None:
            return self.event_history.copy()
        
        return [
            e for e in self.event_history 
            if e['event'] == event_type.value
        ]
    
    def clear_history(self) -> None:
        """Clear event history."""
        self.event_history.clear()
    
    def get_listener_count(self, event: Optional[AgentEvent] = None) -> int:
        """Get count of registered listeners.
        
        Args:
            event: Optional event to get count for, or total if None
            
        Returns:
            Number of registered listeners
        """
        if event is None:
            return sum(len(handlers) for handlers in self.listeners.values())
        
        return len(self.listeners.get(event, []))
