# Active Checklist Monitoring for BaseAgent

## Objective
Implement active checklist monitoring to maintain agent direction and force explicit progress tracking after each tool call.

## File Format Decision
**Use JSON format** for the checklist file because:
- Agent already outputs JSON plan in first step
- Easy to parse and update programmatically  
- Can track completion status, timestamps, and iteration numbers
- Integrates seamlessly with existing Python code

## Todo Items

### Phase 1: Setup Checklist Infrastructure
- [x] Add checklist file path to BaseAgent __init__ (backend/src/prophit_alts/core/agent_checklist.json)
- [x] Add checklist tracking attributes to BaseAgent class
- [x] Create method to parse initial JSON plan into checklist structure

### Phase 2: Checklist Management Methods
- [x] Create `_save_checklist()` method to write checklist to JSON file
- [x] Create `_load_checklist()` method to read current checklist status
- [x] Create `_update_checklist_progress()` method to mark items complete
- [x] Create `_get_checklist_prompt()` method to format current progress

### Phase 3: Integration with Agent Loop
- [x] Capture initial JSON plan from agent's first response
- [x] After each tool call, inject checklist status into user prompt
- [x] Update checklist based on completed actions
- [x] Modify the analysis prompt to include checklist context

### Phase 4: Testing & Cleanup
- [ ] Test with CRO agent to ensure checklist tracking works
- [ ] Ensure checklist file is created/updated properly
- [ ] Verify checklist progress tracking is accurate
- [ ] Clean up any debug code

## Implementation Details

### Checklist JSON Structure
```json
{
  "created_at": "2025-01-12T15:00:00",
  "iteration": 5,
  "items": [
    {
      "step": 1,
      "description": "Get larger ticker pool",
      "status": "completed",
      "completed_at_iteration": 2
    },
    {
      "step": 2,
      "description": "Analyze problem positions",
      "status": "in_progress",
      "started_at_iteration": 3
    },
    {
      "step": 3,
      "description": "Build Portfolio V1",
      "status": "pending"
    }
  ]
}
```

### Modified Prompt After Tool Calls
Instead of generic "Analyze the latest tool observations", use:
```
Current Progress (Iteration X):
✓ Step 1: Get larger ticker pool
→ Step 2: Analyze problem positions (IN PROGRESS)
  Step 3: Build Portfolio V1

Based on your checklist and latest results:
1. Mark any completed items
2. Continue with current task or move to next
3. Stay focused on your targets

Proceed with your next action.
```

## Expected Outcome
- Agent maintains clear direction throughout execution
- Explicit progress tracking visible in logs
- Reduced redundant actions and better focus
- Improved debugging and understanding of agent decisions

## Review

### Summary of Changes Made
Successfully implemented active checklist monitoring for the BaseAgent class to maintain agent focus and provide explicit progress tracking.

### Key Changes:
1. **BaseAgent.__init__**: Added checklist tracking attributes (checklist_path, checklist_items, checklist_enabled)

2. **Checklist Management Methods Added**:
   - `_parse_plan_to_checklist()`: Extracts JSON plan from agent's first response and converts to checklist
   - `_save_checklist()`: Persists checklist to JSON file in core folder
   - `_load_checklist()`: Loads existing checklist from file
   - `_update_checklist_progress()`: Updates item statuses based on iteration progress
   - `_get_checklist_prompt()`: Generates formatted checklist status for agent context

3. **Run Loop Integration**:
   - Captures initial plan after first assistant response (line 197-199)
   - Replaces generic analysis prompts with checklist-aware prompts
   - Updates checklist progress after each tool call
   - Shows progress like: "✓ Step 1: Complete | → Step 2: IN PROGRESS | Step 3: Pending"

### Technical Implementation:
- **JSON file format** chosen for simplicity and compatibility
- **Automatic progress tracking** using iteration-based heuristics
- **Graceful error handling** to prevent agent failures if checklist operations fail
- **Minimal code changes** following DRY principle - reused existing patterns

### Benefits:
- Agent now has persistent awareness of its plan
- Progress is visible in console output
- Reduces chance of agent getting stuck or losing direction
- Creates audit trail of agent decision-making
- No breaking changes to existing agent functionality

### Next Steps:
- Test with CRO agent to verify checklist creation and tracking
- Monitor agent behavior to ensure improved focus
- Fine-tune progress detection heuristics if needed