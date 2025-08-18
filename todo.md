# Tool Error Memory Auto-Retry Implementation Plan

## Problem Statement
When a tool call fails, the error memory system provides guidance but doesn't automatically retry the tool in the same iteration. The agent receives the error with solution guidance but must wait for the next iteration to retry, wasting iterations and potentially losing context.

## Objective
Implement automatic tool retry within the same iteration when error memory has a solution, allowing the agent to immediately apply the fix without waiting for the next iteration.

## Implementation Plan

### Todo Items
- [x] Modify execute_tool_safe() to attempt auto-retry when solution exists
- [x] Add retry mechanism with solution injection
- [x] Update tool execution flow to handle retry responses
- [x] Add retry tracking to prevent infinite loops
- [ ] Test with portfolio analysis tool errors

## Technical Approach

### 1. Current Flow (Problem)
```
Tool fails → Record error → Get solution → Return error with guidance → Wait for next iteration → Agent retries
```

### 2. Desired Flow (Solution)
```
Tool fails → Record error → Get solution → Auto-retry with corrected args → Return success (or final error)
```

### 3. Implementation Details

#### A. Modify execute_tool_safe() in utilities.py
- When tool fails with TypeError/error
- Check if error memory has a solution
- If solution exists with high confidence (>0.7):
  - Extract example_args from solution
  - Attempt retry with corrected arguments
  - If retry succeeds: return success result
  - If retry fails: return original error + guidance

#### B. Add Retry Context Injection
- Before retry, inject solution guidance into a temporary context
- Pass corrected arguments based on example_args pattern
- Merge user's intent with correct format from memory

#### C. Retry Safety Mechanisms
- Maximum 1 retry per tool call (prevent loops)
- Only retry if confidence >= 0.7
- Track retry attempts in agent state
- Log retry attempts for debugging

### 4. Code Structure Changes
1. `base_agent/core/utilities.py`:
   - Enhance execute_tool_safe() with auto-retry logic
   - Add _attempt_retry_with_solution() helper method
   
2. `base_agent/memory/error_memory.py`:
   - Add method to merge user args with solution template
   - Add confidence threshold checking

### 5. Example Scenario
```python
# Tool called: analyze_portfolio_performance({})
# Error: "Parsed portfolio must be a non-empty dict"
# Memory solution found: {"portfolio": {"AAPL": 0.5, "MSFT": 0.5}}
# Auto-retry with: analyze_portfolio_performance({"portfolio": <extracted_from_context>})
# Success: Returns analysis results in same iteration
```

## Benefits
- Reduces iterations wasted on retrying
- Improves agent efficiency
- Better user experience (faster completion)
- Maintains context continuity
- Leverages error memory immediately

## Scope Limitations
- Only retry once per tool call
- Only retry when confidence is high
- Only for tool argument errors (not logic errors)
- Preserve original error if retry also fails

## Risk Mitigation
- Prevent infinite retry loops
- Log all retry attempts
- Maintain audit trail of corrections
- Fallback to original behavior if retry fails

## Success Criteria
- Tool errors with known solutions retry automatically
- Retry happens within same iteration
- Agent completes tasks with fewer total iterations
- Error memory solutions are applied immediately

## Review

### Implementation Complete

Successfully implemented automatic tool retry within the same iteration when error memory has a high-confidence solution.

#### Changes Made:

1. **Modified `execute_tool_safe()` in `utilities.py`**:
   - Added `is_retry` parameter to prevent infinite retry loops
   - Checks error memory for solutions when tool fails
   - Auto-retries with corrected arguments if confidence >= 0.7
   - Returns successful result or final error with guidance

2. **Added `_merge_args_with_solution()` helper method**:
   - Intelligently merges failed arguments with solution template
   - Extracts portfolio data from recent observations for portfolio tools
   - Preserves meaningful user inputs while applying corrections

3. **Retry Logic Features**:
   - **Confidence Threshold**: Only auto-retries if solution confidence >= 0.7
   - **Single Retry**: Prevents infinite loops with `is_retry` flag
   - **Smart Merging**: Combines user intent with correct format
   - **Portfolio Context**: Searches recent observations for portfolio data
   - **Verbose Logging**: Shows retry attempts and results

#### How It Works:
1. Tool fails with an error (e.g., missing portfolio argument)
2. Error memory is checked for a solution
3. If high-confidence solution exists (>= 0.7):
   - Merges failed args with solution template
   - Attempts retry with corrected arguments
   - If successful: Returns result in same iteration
   - If failed: Returns error with guidance
4. If no/low-confidence solution: Returns error (may include guidance)

#### Benefits Achieved:
- **Fewer Iterations**: Errors fixed immediately without waiting
- **Better UX**: Faster task completion
- **Context Preservation**: No loss of context between attempts
- **Learning System**: Successful retries strengthen solution confidence

#### Example Flow:
```
analyze_portfolio_performance({}) → Error: "portfolio must be non-empty"
→ Memory has solution with portfolio template
→ Auto-retry with {"portfolio": <extracted_from_context>}
→ Success! Returns analysis in same iteration
```

The implementation is complete and ready for testing with real portfolio tool errors.