# Agent Refactoring Analysis - WebSocket Event System Discovery

## CRITICAL FINDING: WebSocket System Uses EventManager!

### Evidence Found:

**File: `app/services/shared/websocket_manager.py`**

Lines 113, 135-137:
```python
# WebSocket system subscribes to agent events
agent.event_manager.on(AgentEvent.TOOL_EXECUTED, on_tool_executed)
agent.event_manager.on(AgentEvent.ITERATION_COMPLETE, on_iteration_complete)
agent.event_manager.on(AgentEvent.TASK_STARTED, on_task_event)
agent.event_manager.on(AgentEvent.TASK_COMPLETED, on_task_event)
```

### What This Means:

The `attach_agent_stream()` function in `websocket_manager.py` subscribes to 4 agent events:

1. **TOOL_EXECUTED** (line 113) → Streams tool calls to frontend in real-time
2. **ITERATION_COMPLETE** (line 135) → Sends task state updates after each iteration
3. **TASK_STARTED** (line 136) → Sends task state when task starts
4. **TASK_COMPLETED** (line 137) → Sends task state when task completes

### What Gets Sent to Frontend:

**Tool calls:**
```json
{
  "type": "tool_call",
  "tool_name": "get_ticker_fundamentals"
}
```

**Task state updates:**
```json
{
  "type": "task_state",
  "arguments": {
    "tasks": [
      {
        "id": 1,
        "description": "Analyze portfolio",
        "status": "in_progress",
        "subtasks": [...]
      }
    ]
  }
}
```

### Impact if EventManager Deleted:

❌ **Real-time streaming will BREAK**
❌ **Frontend won't get live updates during agent execution**
❌ **Users won't see progress as agent runs**

### Solution Required:

The refactoring plan CANNOT just delete EventManager. Need to:

**Option A: Keep EventManager, wrap callbacks**
```python
# execution_engine.py
def __init__(self, task_store, on_task_complete=None, event_manager=None):
    self.on_task_complete = on_task_complete
    self.event_manager = event_manager  # Keep for WebSocket

    # When task completes:
    if self.on_task_complete:
        self.on_task_complete(task_id)  # New callback pattern
    if self.event_manager:
        self.event_manager.emit(AgentEvent.TASK_COMPLETED, {...})  # Keep events
```

**Option B: Create EventCallbackAdapter**
```python
class EventCallbackAdapter:
    """Wraps callbacks to emit events for backward compatibility."""
    def __init__(self, event_manager):
        self.events = event_manager

    def on_task_complete(self, task_id):
        # Emit old-style event for WebSocket
        self.events.emit(AgentEvent.TASK_COMPLETED, {'task_id': task_id})
```

**Option C: Refactor WebSocket to use callbacks directly**
- Inject callbacks into agent instead of subscribing to events
- More work but cleaner architecture

### Agents Were RIGHT:

All 3 review agents flagged this as a concern:
- Architecture Advisor: "Check if WebSocket router subscribes to events"
- Code Reviewer: "Event system deletion may break external consumers"
- Strategic Planner: "External dependency testing needs more detail"

### Action Required:

MUST add to refactoring plan BEFORE Phase 2:

**Phase 2.4: Migrate Event Consumers**
1. Audit WebSocket system's event dependencies
2. Choose migration strategy (A, B, or C above)
3. Test WebSocket streaming still works
4. Document breaking changes for frontend team

This is NOT optional - it's a production system dependency!
