# Agentic Framework Refactoring Plan v2.0

**Date:** 2025-10-21
**Status:** ✅ Phase 2 COMPLETE - Ready for Phase 3
**Priority:** Critical
**Last Updated:** 2025-10-22

---

## 🚨 EXTREME RULE: NO BACKWARD COMPATIBILITY - ZERO CLUTTER

**THIS IS AGENT V2 - A COMPLETE REFACTOR**

- ❌ **NO backward compatibility code**
- ❌ **NO old/legacy files kept around** (`_old.py`, `_backup.py`, `manager_old.py`, etc.)
- ❌ **NO commented-out old code**
- ❌ **NO "we might need this later" code**
- ❌ **NO duplicate implementations**

**All old code is saved in GitHub branches. DELETE ruthlessly.**

**Refactoring Process:**
1. ✅ Build the new solution
2. ✅ Test the new solution
3. ✅ **DELETE the old file completely** - no renaming to `_old.py`
4. ✅ Update all imports
5. ✅ Move on - clean, minimal, focused code only

**If it's not being used in V2, it gets DELETED. Period.**

---

## 📈 REFACTORING PROGRESS SUMMARY

**Current Status**: Phase 2 (100% COMPLETE) - All 6 sub-phases done, ready for Phase 3

### Completed Work
- ✅ **Phase 1**: All new components built (protocols, parsers, validators, feature flags)
- ✅ **Phase 2.1**: TaskManager refactored using composition pattern
  - 741 lines → 8 focused modules (17-236 lines each)
  - Circular dependency broken with callback pattern
  - TaskStore protocol implemented
- ✅ **Phase 2.2**: ExecutionEngine circular dependency eliminated
  - Removed 171 lines of analytics
  - Replaced event_manager with callbacks
  - 1116 → 921 lines
- ✅ **Phase 2.2b**: ExecutionEngine decomposed using composition pattern
  - 921 lines → 8 focused modules (5-299 lines each)
  - Created 7 specialized managers (ExecutorCore, DependencyManager, AdvancementManager, ToolIntegrationManager, CompletionManager, RecoveryManager)
  - All tests passing, backward compatible
- ✅ **Phase 2.3**: Agent.py initialization fixed
  - Updated TaskManager init to include on_task_progression callback
  - Fixed ExecutionEngine init with correct parameters (task_store, callbacks)
  - Wired callback connecting TaskManager → ExecutionEngine
  - All integration tests passing
- ✅ **Phase 2.4**: Class and file renamed to PlanExecutor
  - Renamed class PlanExecutionEngine → PlanExecutor
  - Renamed file plan_execution_engine.py → plan_executor.py
  - Updated all imports across codebase (5 files)
  - Updated all documentation (CLAUDE.md, agent_v2.md, etc.)
  - All integration tests passing

### Next Steps
- ⏳ **Phase 3**: Extract agent.py components
- ⏳ **Phase 4**: Migrate to new validator
- ⏳ **Phase 5**: Final cleanup

### Key Metrics
- **Files Refactored**: 2 major components (TaskManager, ExecutionEngine)
- **Lines Reduced**: 1662 lines → 16 focused modules
- **Circular Dependencies Broken**: 1 critical dependency eliminated
- **Composition Pattern Applied**: Consistently across both components
- **All Tests**: ✅ Passing

---

## SECTION 1: OVERALL ANALYSIS & DIAGNOSIS

### Executive Summary

The agentic framework is the core of ProphitAI and functions correctly, but it has accumulated severe technical debt that makes it unmaintainable and difficult to extend. The codebase violates every major design principle (KISS, YAGNI, DRY) and has multiple files exceeding 500-line constraints by 100-200%.

**Critical Metrics:**
- Total codebase: ~12,000 lines
- Files over 500 lines: 8 files
- Largest violation: agent.py (1130 lines - 226% over)
- Estimated reduction potential: ~40% (down to ~7,200 lines)
- Circular dependencies: 1 critical (TaskManager � ExecutionEngine)
- Code duplication: ~15% of codebase

### File-by-File Analysis

#### 1. agent.py (1130 lines - **CRITICAL VIOLATION**)

**Current State:**
- **Lines 1-145**: Initialization (acceptable)
- **Lines 146-411**: Utility methods (acceptable)
- **Lines 412-1077**: Main run loop (~665 lines - **UNACCEPTABLE**)
- **Lines 1078-1131**: Cleanup (acceptable)

**Issues Identified:**

1. **Massive ReAct Loop (lines 476-1077)**
   - Single function with 600+ lines
   - 10+ levels of nesting
   - Multiple early exits and continues
   - Impossible to test or debug

2. **Duplicate Prompt Injection**
   - Plan context injection appears at lines 500-526, 728-736, 861-868, 912-919
   - Same logic repeated 4 times with slight variations
   - Should be single method

3. **Mixed Responsibilities**
   The agent.py file handles:
   - Tool registration and dispatch
   - ReAct loop orchestration
   - Stagnation detection (lines 80-83, 617-620, 1016-1077)
   - Task management coordination
   - Prompt building and context injection
   - Token counting and message logging
   - Memory refresh coordination

   **Violation**: Single Responsibility Principle - one class doing 7+ jobs

4. **Stagnation Detection Scattered**
   - `_recent_actions` list (line 81)
   - `_stuck_count` tracking (line 82)
   - `update_stagnation()` in utilities (line 619)
   - Stagnation check in execution_engine (lines 1016-1077)
   - **Violation**: Same logic in 3+ places

5. **Tight Coupling**
   ```python
   # Line 103: Creates TaskManager directly
   self.task_manager = TaskManager(verbose=verbose, output_dir=self.output_dir)

   # Line 137: Creates ExecutionEngine directly
   self.execution_engine = PlanExecutor(
       task_manager=self.task_manager,  # Hard dependency
       event_manager=self.event_manager,
       verbose=self.verbose
   )
   ```
   **Violation**: Dependency Inversion - depends on concrete classes, not abstractions

#### 2. execution_engine.py (1116 lines - **CRITICAL VIOLATION**)

**Current State:**
- **Lines 1-108**: Initialization (acceptable)
- **Lines 109-516**: Core execution logic (acceptable)
- **Lines 517-925**: Advanced features (too complex)
- **Lines 926-1116**: Analytics and unused features (**DELETE**)

**Issues Identified:**

1. **Circular Dependency (LINE 33 - CRITICAL)**
   ```python
   # Line 32-33
   # Set back-reference so task manager can trigger advancement
   self.task_manager.execution_engine = self
   ```
   This creates a circular reference where:
   - ExecutionEngine holds TaskManager reference
   - TaskManager holds ExecutionEngine reference back

   **Problem**: Cannot test in isolation, tightly coupled, violates Dependency Inversion
   **Solution**: See Phase 2.1-2.3 for callback pattern that eliminates both directions of circular dependency

2. **Unused Analytics Code (lines 946-1116)**
   - `simulate_parallel_execution()` (lines 946-984): 38 lines never used
   - `create_plan_analytics_report()` (lines 985-1067): 83 lines never queried
   - `_generate_execution_recommendations()` (lines 1069-1116): 48 lines never acted upon

   **Total waste**: 169 lines of YAGNI violations

3. **Duplicate Evidence Collection**
   - `collect_evidence_from_tool_result()` (lines 684-745): 62 lines
   - `update_task_from_tool_result()` (lines 335-436): Overlaps with evidence collection

   Both methods analyze tool results and extract evidence with ~60% overlap

4. **Tool Relevance Logic Too Complex**
   - `_is_tool_relevant()` (lines 770-791): Complex regex matching
   - `_subtask_has_tool_named_evidence()` (lines 793-803): Additional checking
   - `_looks_like_success_evidence()` (lines 805-808): More checking

   **Issue**: 3 separate methods for relevance checking when simple comparison would work

5. **Over-Engineered Validation Integration**
   ```python
   # Lines 452-476: Complex auto-advancement logic
   should_complete, confidence, reason = self.task_validator.validate_tool_result_for_completion(...)

   subtask_complete, subtask_confidence, subtask_reason = self.task_validator.validate_subtask_completion(...)

   is_relevant = self._is_tool_relevant(tool_name, self.current_main_task, self.current_subtask)
   is_error = self._is_error_result(result)
   has_tool_named_evidence = self._subtask_has_tool_named_evidence(self.current_subtask, tool_name)

   return (should_complete and confidence >= 0.6) or (subtask_complete and subtask_confidence >= 0.7)
   ```

   **Problem**: Combining multiple validators with arbitrary thresholds (0.6, 0.7) - over-complex

#### 3. manager.py (741 lines - **CRITICAL VIOLATION**)

**Current State:**
- **Lines 1-183**: State management (good - ~180 lines)
- **Lines 184-310**: Analytics and reporting (**MOVE OR DELETE**)
- **Lines 311-741**: More state management with duplication (**REFACTOR**)

**Issues Identified:**

1. **Back-Reference to ExecutionEngine (Line 17)**
   ```python
   # Line 17
   self.execution_engine = None  # Will be set by execution engine

   # Lines 354-365: Reaches back into ExecutionEngine
   if (should_complete and
       self.execution_engine and
       self.execution_engine.plan_loaded and
       self.execution_engine.current_main_task and ...):
       success, message = self.execution_engine.advance_task_progression()
   ```

   **Problem**: TaskManager directly calls ExecutionEngine methods - circular coupling
   **Solution**: See Phase 2.1-2.3 for callback-based solution that breaks this dependency

2. **Analytics Mixed with State Management**
   - `get_task_progress_summary()` (lines 197-240): 44 lines of analytics
   - `get_execution_analytics()` (lines 271-310): 40 lines of analytics
   - Lines 693-739 (not shown): `get_plan_health_status()` - 47 lines

   **Total**: ~130 lines of analytics code mixed with state management

   **Violation**: Single Responsibility - state storage should not do reporting

3. **Duplicate Task Update Flows**
   ```python
   # update_main_task_status() (lines 62-88)
   def update_main_task_status(self, task_id, status, reason):
       main_task = self.get_main_task_by_id(task_id)
       old_status = main_task.status
       main_task.status = status
       self.execution_history.append({...})
       self.save_state()

   # update_task_status() (lines 312-399)
   def update_task_status(self, task_id, status, evidence, reason, iteration):
       # Similar logic but different signature and flow
       self.execution_history.append({...})
       self.save_state()
       # ALSO reaches back into execution_engine (lines 384-397)
   ```

   **Problem**: Two methods doing similar task updates with different patterns

4. **Tool Routing Audit Never Used**
   ```python
   # Lines 184-195
   def record_tool_routing(self, task_id, subtask_id, tool_name, is_relevant):
       self.execution_history.append({
           'type': 'tool_routed',
           'tool_name': tool_name,
           'is_relevant': is_relevant,
       })
       self.save_state()
   ```

   **Problem**: This audit trail is never queried or analyzed - pure YAGNI violation

#### 4. validator.py (592 lines - **CRITICAL VIOLATION**)

**Current State:**
- **Lines 1-36**: Initialization with confidence thresholds
- **Lines 37-254**: Main validation methods (too complex)
- **Lines 255-592**: Helper validators (excessive)

**Issues Identified:**

1. **Over-Engineered Confidence Scoring**
   ```python
   # Lines 23-27: Arbitrary thresholds
   self._confidence_thresholds = {
       'subtask_completion': 0.7,
       'main_task_completion': 0.8,
       'tool_result_success': 0.6
   }
   ```

   **Problem**:
   - No justification for 0.7 vs 0.8 vs 0.6
   - Adds complexity without clear benefit
   - Simple boolean checks would work

2. **Multiple Overlapping Validators**
   - `_evidence_threshold_validator()` (lines 271-288): Checks evidence count
   - `_tool_prediction_validator()` (lines 290-311): Checks tool predictions
   - `_observation_analysis_validator()` (lines 313-348): Analyzes observations
   - `validate_subtask_completion()` (lines 98-188): Combines all of above
   - `validate_main_task_completion()` (lines 37-96): Also combines all of above

   **Problem**: 5 methods checking similar things with different confidence calculations

3. **Complex Pattern Matching**
   ```python
   # Lines 136-169: Subtask validation with regex and error checking
   has_error_evidence = any(
       re.search(r'\berror\b', str(ev), re.IGNORECASE)
       for ev in subtask.completion_evidence
   )

   has_relevant_tool_evidence = False
   if relevant_tools:
       for ev in subtask.completion_evidence:
           ev_lower = str(ev).lower()
           if any(rt in ev_lower for rt in relevant_tools):
               has_relevant_tool_evidence = True
               break
   ```

   **Problem**: Complex string matching when simple checks would suffice

4. **Reality Check**
   The 592-line validator can be refactored to ~240 lines across 3 focused modules:
   ```python
   # tasks/validation/patterns.py (~40 lines)
   SAFE_PHRASES = [
       r'tracking error',      # Financial term
       r'margin.{0,5}error',   # "margin of error"
       r'ameren',              # Stock ticker containing "error"
       # ... 8 more finance-specific safe phrases
   ]

   ERROR_PATTERNS = [
       r'^error:',             # Actual error messages
       r'error occurred',
       r'\bfailed to\b',
       # ... 14 more real error patterns
   ]

   # tasks/validation/error_detection.py (~80 lines)
   def has_error(text: str) -> bool:
       """Context-aware error detection for finance domain."""
       # Check safe phrases FIRST to prevent false positives
       for safe_pattern in SAFE_PHRASES:
           if re.search(safe_pattern, text, re.IGNORECASE):
               return False
       # Then check for actual errors
       return any(re.search(p, text, re.MULTILINE | re.IGNORECASE)
                  for p in ERROR_PATTERNS)

   # tasks/validation/completion_validator.py (~120 lines)
   def is_subtask_complete(subtask: SubTask) -> bool:
       if not subtask.completion_evidence:
           return False
       for evidence in subtask.completion_evidence:
           if has_error(str(evidence)):  # Context-aware check
               return False
       return subtask.completed
   ```

   **Reduction**: 592 � 240 lines (59% reduction) with PRESERVED context-awareness

### 5. Code Duplication Analysis (DRY Violations)

#### Tool Result Parsing (4 implementations)

1. **core/parser.py:parse_tool_result()**
   ```python
   def parse_tool_result(result: Any, verbose: bool = False) -> Dict[str, Any]:
       if isinstance(result, dict):
           return result
       # ... parsing logic
   ```

2. **core/utilities.py:execute_tool_safe()**
   ```python
   def execute_tool_safe(self, name: str, args: Dict) -> Any:
       try:
           result = func(**args)
           return result
       except Exception as e:
           return yaml.dump({"success": False, "error": str(e)})
   ```

3. **tasks/validator.py:_analyze_tool_success()**
   ```python
   def _analyze_tool_success(self, tool_name: str, tool_result: Any):
       if isinstance(tool_result, Exception):
           return False, 0.0, f"Tool {tool_name} raised exception"
       # ... duplicate parsing logic
   ```

4. **tasks/execution_engine.py:_is_error_result()**
   ```python
   def _is_error_result(self, result: Any) -> bool:
       parsed = parse_tool_result(result, verbose=False)
       return parsed.get('success') is False
   ```

**Impact**: Same tool result is parsed 4 different ways in 4 different files. Bug fixes must be applied to all 4.

#### Evidence Collection (2 overlapping implementations)

1. **execution_engine.py:collect_evidence_from_tool_result()** (lines 684-745)
   - 62 lines of evidence extraction
   - Checks for success indicators
   - Analyzes data types
   - Checks tool name patterns

2. **execution_engine.py:update_task_from_tool_result()** (lines 335-436)
   - 102 lines including evidence collection
   - Similar analysis of tool results
   - Overlaps with collect_evidence_from_tool_result by ~60%

**Impact**: When tool result format changes, both methods need updates

#### Task Status Updates (duplicate flows)

1. **manager.py:update_main_task_status()** (lines 62-88)
   - Updates status
   - Adds to execution_history
   - Calls save_state()

2. **manager.py:update_task_status()** (lines 312-399)
   - Updates status with different signature
   - Adds to execution_history
   - Calls save_state()
   - Also handles subtasks
   - Reaches back into execution_engine

**Impact**: Two different APIs for same operation leads to confusion

### Design Principle Violations Summary

#### KISS (Keep It Simple, Stupid) - **GRADE: F**

**Violations:**
1. **TaskValidator**: 592 lines with confidence scoring when boolean checks suffice
2. **ReAct Loop**: 600-line function with 10+ nesting levels
3. **Plan Analytics**: 200+ lines of complex analytics never used
4. **Tool Relevance Checking**: 3 methods with regex when simple comparison works

**Impact**:
- Debugging is extremely difficult
- New developers cannot understand code flow
- Bugs hide in complexity
- Maintenance takes 3x longer than it should

#### YAGNI (You Aren't Gonna Need It) - **GRADE: D**

**Violations:**
1. **Parallel Execution Simulation** (execution_engine.py:946-984): 38 lines, never used
2. **Analytics Reports** (execution_engine.py:985-1067): 83 lines, never queried
3. **Execution Recommendations** (execution_engine.py:1069-1116): 48 lines, never acted on
4. **Health Metrics** (manager.py:693-739): 47 lines, doesn't affect execution
5. **Tool Routing Audit** (manager.py:184-195): Tracking system never analyzed
6. **Confidence Scoring** (validator.py): Complex system with arbitrary thresholds

**Total Wasted Code**: ~300 lines (2.5% of codebase)

**Impact**:
- Maintenance burden for unused features
- Increases cognitive load
- More code to test and debug
- Slows down refactoring

#### DRY (Don't Repeat Yourself) - **GRADE: D**

**Violations:**
1. **Tool Result Parsing**: 4 different implementations across 4 files
2. **Evidence Collection**: 2 overlapping methods (~60% duplicate logic)
3. **Task Status Updates**: 2 different update methods with similar logic
4. **Stagnation Detection**: 3 different tracking mechanisms
5. **Prompt Injection**: Same plan context logic repeated 4 times
6. **Observation Analysis**: Pattern matching duplicated in validator and execution_engine

**Estimated Duplication**: ~15% of codebase (~1,800 lines)

**Impact**:
- Bug fixes must be applied in multiple places
- Inconsistent behavior between duplicate implementations
- Higher risk of introducing bugs
- Longer development time

#### Single Responsibility Principle - **GRADE: F**

**Violations:**

1. **BaseAgent (agent.py)** does 7+ jobs:
   - Orchestrates execution (ReAct loop)
   - Manages tool registration and dispatch
   - Handles task management coordination
   - Implements stagnation detection
   - Manages token counting and logging
   - Handles plan injection and context management
   - Coordinates memory refresh

2. **TaskManager (manager.py)** does 4+ jobs:
   - Stores task state (correct)
   - Provides CRUD operations (correct)
   - Generates analytics reports (wrong - should be separate)
   - Manages execution history (could be separate)
   - Provides health metrics (wrong - should be separate)

3. **ExecutionEngine (execution_engine.py)** does 6+ jobs:
   - Drives task execution (correct)
   - Validates task completion (wrong - should use validator)
   - Collects evidence (could be separate)
   - Analyzes stagnation (wrong - should be separate)
   - Simulates parallel execution (wrong - YAGNI)
   - Generates analytics (wrong - should be separate)

**Impact**:
- Classes become too large to understand
- Testing is difficult (must mock multiple concerns)
- Changes to one responsibility affect others
- Violates Open/Closed Principle (cannot extend without modifying)

#### Dependency Inversion Principle - **GRADE: F**

**Violations:**

1. **No Abstractions/Interfaces**
   - All components depend on concrete classes
   - No Protocol definitions for dependency injection
   - Cannot swap implementations
   - Cannot mock for testing

2. **Circular Dependencies**
   ```python
   # execution_engine.py:33
   self.task_manager.execution_engine = self

   # manager.py:17
   self.execution_engine = None  # Set by execution engine

   # manager.py:355
   self.execution_engine.advance_task_progression()
   ```

   **Problem**: TaskManager and ExecutionEngine directly reference each other
   **Solution**: Phase 2.1-2.3 replaces bi-directional references with unidirectional callback pattern

3. **Direct State Manipulation**
   ```python
   # execution_engine.py:362
   self.task_manager.add_task_observation(active_task_id, observation)

   # execution_engine.py:192
   self.task_manager.update_subtask_status(...)
   ```

   **Problem**: ExecutionEngine reaches into TaskManager internals

4. **Hard-Coded Dependencies**
   ```python
   # agent.py:103
   self.task_manager = TaskManager(verbose=verbose, output_dir=self.output_dir)

   # agent.py:137
   self.execution_engine = PlanExecutor(
       task_manager=self.task_manager,
       event_manager=self.event_manager
   )
   ```

   **Problem**: Agent creates dependencies directly, cannot inject mocks

**Impact**:
- Cannot test in isolation
- Cannot swap implementations
- Changes ripple through system
- Tight coupling makes refactoring dangerous

### Root Causes

The technical debt accumulated due to:

1. **Iterative Feature Addition**: Features added incrementally without refactoring
2. **No File Size Enforcement**: Files allowed to grow beyond 500 lines
3. **No Code Review Focus on Principles**: Reviews didn't enforce KISS/YAGNI/DRY
4. **Premature Optimization**: Added complexity (confidence scoring, analytics) before needed
5. **Fear of Breaking Changes**: Kept old code paths instead of refactoring
6. **No Architectural Guidelines**: No clear separation of concerns

### Impact on Development

**Current State Problems:**
- Average PR review time: 2-3 hours (due to complexity)
- Bug fix time: 3x longer than it should be
- New feature development: Requires touching 5+ files
- Testing: Difficult to test in isolation
- Onboarding: New developers take 2+ weeks to understand

**After Refactoring:**
- PR review time: 30-60 minutes (simpler, focused changes)
- Bug fix time: 3x faster (clear separation of concerns)
- New feature development: Touch 1-2 files max
- Testing: Easy to unit test each component
- Onboarding: New developers productive in 2-3 days

### Proposed Metrics for Success

| Metric | Before | Target | Success Criteria |
|--------|--------|--------|------------------|
| **File Size Compliance** | 85% | 100% | Zero files over 500 lines |
| **Largest File** | 1130 lines | <400 lines | agent.py reduced by 65% |
| **Code Duplication** | 15% | <3% | Unified parsers, validators |
| **Circular Dependencies** | 1 critical | 0 | Use callbacks/protocols |
| **Unused Code** | ~300 lines | 0 lines | Remove all YAGNI violations |
| **Test Coverage** | ~40% | >70% | All new components tested |
| **Cyclomatic Complexity** | Avg 12 | <8 | Simplified logic |
| **Max Nesting Depth** | 10 levels | <4 levels | Refactor ReAct loop |

---

## SECTION 2: PHASED REFACTORING PLAN

### Overview

The refactoring will be done in 5 phases:
1. **Phase 1**: Build new components (interfaces, parsers) - NO breaking changes
2. **Phase 2**: Refactor TaskManager and ExecutionEngine to use new patterns
3. **Phase 3**: Extract agent.py components
4. **Phase 4**: Atomic switch to new validator
5. **Phase 5**: Delete all old/unused code

**Key Principle**: Build new, switch atomically, delete old. NO backwards compatibility.

### Progress Tracker

| Phase | Status | Completion | Key Deliverables |
|-------|--------|------------|------------------|
| **Phase 1** | ✅ COMPLETE | 100% | Protocols, parsers, validators, feature flags |
| **Phase 2.1** | ✅ COMPLETE | 100% | TaskManager decomposed (741 → 8 files) |
| **Phase 2.2** | ✅ COMPLETE | 100% | ExecutionEngine circular dependency broken |
| **Phase 2.2b** | ✅ COMPLETE | 100% | ExecutionEngine decomposed (921 → 8 files) |
| **Phase 2.3** | ✅ COMPLETE | 100% | Callbacks wired in Agent.py |
| **Phase 2.4** | ✅ COMPLETE | 100% | Class renamed PlanExecutor, file renamed |
| **Phase 3** | ⏳ NOT STARTED | 0% | Extract agent.py components |
| **Phase 4** | ⏳ NOT STARTED | 0% | Migrate to new validator |
| **Phase 5** | ⏳ NOT STARTED | 0% | Final cleanup and deletion |

**Overall Progress**: Phase 2 (100% COMPLETE) - All 6 sub-phases done

---

### Phase 1: Build New Core Components (Duration: 1-2 weeks)

**Goal**: Create all new interfaces, parsers, and simplified validator WITHOUT touching existing code.

#### 1.1: Create Directory Structure
**What**: Add new directories for organized code
**Files**: Create 3 new directories
**Checklist**:
- [x] Create `app/core/agentic_framework/base_agent/protocols/` directory
- [x] Create `app/core/agentic_framework/base_agent/execution/` directory
- [x] Create `app/core/agentic_framework/base_agent/prompting/` directory
- [x] Create `app/core/agentic_framework/config.py` file

**Validation**: Directories exist, no errors on import

#### 1.2: Create Protocol Interfaces (~130 lines total)
**What**: Define Python Protocols for structural typing
**Files**: 3 new files in `protocols/`
**Checklist**:
- [x] Write `protocols/__init__.py` (empty)
- [x] Write `protocols/task_store.py` (~50 lines)
  - Define TaskStore Protocol
  - Methods: get_plan(), update_task_status(), update_subtask_status(), add_evidence(), add_observation()
- [x] Write `protocols/task_executor.py` (~50 lines)
  - Define TaskExecutor Protocol
  - Methods: load_plan(), get_current_task(), advance_task_progression()
- [x] Write `protocols/completion_checker.py` (~30 lines)
  - Define CompletionChecker Protocol
  - Methods: is_subtask_complete(), is_main_task_complete()

**Validation**: Import protocols without errors, no runtime impact

#### 1.3: Create Unified ToolResultParser (~120 lines)
**What**: Single source of truth for parsing tool results
**Files**: 1 new file in `core/`
**Checklist**:
- [x] Write `core/result_parser.py` (~120 lines)
  - Class: ToolResultParser
  - Methods: parse(), is_success(), is_error(), get_data(), get_error()
  - Handle all result types: dict, str, Exception, None
- [x] Write unit tests for ToolResultParser
- [x] Test with example tool results from actual tools

**Validation**: All tests pass, handles edge cases

#### 1.4: Create Context-Aware Validator (~240 lines, 3 files)
**What**: Replace 592-line validator with modular, context-aware validator (boolean returns, NO confidence scores)
**Files**: New folder `tasks/validation/` with 3 modules
**Checklist**:
- [x] Create `tasks/validation/` folder structure
- [x] Write `tasks/validation/__init__.py` (18 lines)
  - Export main validator class and functions
- [x] Write `tasks/validation/patterns.py` (42 lines)
  - Constant: SAFE_PHRASES (12 finance-specific patterns)
    - Examples: 'tracking error', 'margin of error', 'ameren' (stock ticker)
  - Constant: ERROR_PATTERNS (17 real error indicators)
    - Examples: '^error:', 'error occurred', r'\bfailed to\b'
  - NO logic, just data constants
- [x] Write `tasks/validation/error_detection.py` (132 lines)
  - Function: has_error(text: str) -> bool
  - Function: has_error_in_dict(result: dict) -> bool
  - Function: has_error_in_result(tool_result: Any) -> bool
  - Logic: Check SAFE_PHRASES first (prevent false positives), then ERROR_PATTERNS
  - Use word boundary regex for precision
- [x] Write `tasks/validation/completion_validator.py` (136 lines)
  - Class: CompletionValidator (implements CompletionChecker protocol)
  - Method: is_subtask_complete(subtask) -> bool
  - Method: is_main_task_complete(task) -> bool
  - Method: get_completion_status(task) -> Dict[str, Any]
  - Uses error_detection.has_error() for evidence validation
  - Returns simple boolean (NO confidence scores)
- [x] Write unit tests for each module
  - Test safe phrases don't trigger false positives ("Ameren", "tracking error")
  - Test actual errors are detected ("error occurred", "failed to connect")
  - Test with real task/subtask objects from actual agent runs

**Validation**: All tests pass, context-aware detection works, boolean returns only

#### 1.5: Create Feature Flags (~30 lines)
**What**: Enable gradual rollout of new components
**Files**: 1 new file `config.py`
**Checklist**:
- [x] Write `config.py` at framework root (~30 lines)
  - Class: RefactoringFlags
  - Flag: USE_NEW_VALIDATOR (default: False)
  - Flag: USE_NEW_RESULT_PARSER (default: False)
  - Flag: USE_CALLBACK_PATTERN (default: False)
- [x] Test flags can be toggled via environment variables

**Validation**: Flags work, default to False (old behavior)

**Phase 1 Complete**: New components exist, old system still works unchanged

---

### Phase 2: Refactor Manager & Executor (Duration: 2 weeks)

**Goal**: Break circular dependency, remove analytics, use new patterns

#### 2.1: Refactor TaskManager (741 � ~180 lines)
**What**: Break circular dependency using callback pattern, remove analytics, implement TaskStore protocol
**Files**: Modify `tasks/manager.py`
**Checklist**:
- [x] Add imports:
  ```python
  from ..protocols.task_store import TaskStore
  from typing import Optional, Callable
  ```
- [x] **BREAK CIRCULAR DEPENDENCY** - Update `__init__` signature (line ~16-20):
  ```python
  # OLD (line 17 - CIRCULAR DEPENDENCY)
  self.execution_engine: Optional[PlanExecutor] = None

  # NEW - Use callback instead
  def __init__(
      self,
      on_task_progression: Optional[Callable[[int], None]] = None,
      verbose: bool = True
  ):
      self.on_task_progression = on_task_progression  # Callback, not reference
      self.verbose = verbose
      # NO execution_engine reference
  ```
- [x] **REPLACE** all `self.execution_engine.advance_task_progression()` calls (lines ~354-365):
  ```python
  # OLD (manager.py:354-365) - CIRCULAR DEPENDENCY
  if (self.execution_engine and
      self.execution_engine.plan_loaded and
      should_advance):
      success, message = self.execution_engine.advance_task_progression()

  # NEW - Use callback pattern
  if should_advance and self.on_task_progression:
      self.on_task_progression(task_id)
  ```
- [x] **DELETE** `get_execution_analytics()` method (lines ~271-310) - 40 lines
- [x] **DELETE** `get_plan_health_status()` method (lines ~693-739) - 47 lines
- [x] **DELETE** `record_tool_routing()` method (lines 184-195) - 12 lines
- [x] Ensure TaskManager implements TaskStore Protocol (duck typing)
- [x] Consolidate update_main_task_status() and update_task_status() into single method
- [x] Run existing tests to ensure no breakage

**Validation**: Tests pass, file is ~180 lines, **NO circular reference** (no execution_engine attribute)
**Current Status**: ✅ PHASE 2.1 COMPLETE - ALL REQUIREMENTS MET

**Implementation Notes**:
- EXCEEDED requirements by implementing full composition pattern
- Split monolithic 623-line file into 8 focused modules (17-236 lines each)
- Achieved better separation of concerns than originally planned
- All files well under 500-line project constraint
- TaskStore protocol fully implemented via component delegation

#### 2.2: Refactor ExecutionEngine (1116 � ~280 lines)
**What**: Remove analytics, use callbacks, break circular dependency
**Files**: Modify `tasks/execution_engine.py`
**Checklist**:
- [x] Add Protocol imports:
  ```python
  from ..protocols.task_store import TaskStore
  from ..protocols.task_executor import TaskExecutor
  from typing import Optional, Callable
  ```
- [x] Update `__init__` signature:
  ```python
  def __init__(
      self,
      task_store: TaskStore,  # Protocol interface
      on_task_complete: Optional[Callable[[int], None]] = None,
      on_task_advance: Optional[Callable[[int, str], None]] = None,
      verbose: bool = True
  ):
  ```
- [x] **DELETE** back-reference: `self.task_manager.execution_engine = self` (line 33)
- [x] **DELETE** event_manager parameter and all event calls
- [x] **REPLACE** event calls with callback invocations:
  ```python
  if self.on_task_complete:
      self.on_task_complete(task_id)
  ```
- [x] **DELETE** `simulate_parallel_execution()` (lines ~946-984) - 38 lines
- [x] **DELETE** `create_plan_analytics_report()` (lines ~985-1067) - 83 lines
- [x] **DELETE** `_generate_execution_recommendations()` (lines ~1069-1116) - 48 lines
- [x] Keep using OLD validator for now (TaskValidator) - **NOTE**: Will be replaced in Phase 4 with new validator
- [x] Run existing tests

**Validation**: Tests pass, no circular dependency

**Current Status**: ✅ PHASE 2.2 COMPLETE - Circular dependency broken, callbacks implemented

**Implementation Notes**:
- Deleted 171 lines of analytics methods (simulate_parallel_execution, create_plan_analytics_report, _generate_execution_recommendations)
- Replaced all self.task_manager → self.task_store (26 occurrences)
- Replaced all self.event_manager.emit() → callbacks (3 occurrences)
- TaskManager now implements TaskStore protocol via delegation
- Reduced from 1116 → 921 lines

**CRITICAL ISSUE IDENTIFIED**: ExecutionEngine is still 920 lines (target was ~280). Need to break down into folder structure similar to manager/.

#### 2.2b: Break Down ExecutionEngine into Folder Structure (920 → ~150 lines per file)
**What**: Apply composition pattern to ExecutionEngine, similar to TaskManager refactor
**Files**: Create `tasks/executor/` folder, split execution_engine.py into 6 focused modules
**Structure**:
```
tasks/
├── executor/
│   ├── __init__.py                   (~20 lines) - Export PlanExecutor
│   ├── executor_core.py              (~150 lines) - Core: __init__, load_plan, state getters
│   ├── advancement.py                (~200 lines) - Task progression & advancement logic
│   ├── tool_integration.py           (~250 lines) - Tool result processing, evidence collection
│   ├── completion.py                 (~130 lines) - Completion checking & analytics
│   ├── dependencies.py               (~100 lines) - Task dependencies & availability
│   └── recovery.py                   (~140 lines) - Error handling, failure recovery, stagnation
└── execution_engine.py               (DELETE after migration)
```

**Method Distribution**:

**executor_core.py** (~150 lines):
- `__init__()` - Initialize executor with task_store and callbacks
- `load_plan()` - Load structured plan into executor
- `get_current_task()` - Get currently executing main task
- `get_current_subtask()` - Get currently executing subtask
- `get_current_task_context()` - Get full context for current task

**advancement.py** (~200 lines):
- `advance_task_progression()` - Main progression orchestrator
- `_advance_to_next_main_task()` - Logic for moving to next main task
- Helper: Task completion detection and callback invocation

**tool_integration.py** (~250 lines):
- `update_task_from_tool_result()` - Process tool results and update task state
- `_should_auto_advance_subtask()` - Determine if subtask should auto-advance
- `collect_evidence_from_tool_result()` - Extract evidence from tool results
- `_is_tool_relevant()` - Check if tool is relevant to current task
- `_subtask_has_tool_named_evidence()` - Check for tool-specific evidence
- `_looks_like_success_evidence()` - Pattern matching for success indicators

**completion.py** (~130 lines):
- `check_task_completion_conditions()` - Validate task completion criteria
- `get_execution_summary()` - Summary of execution state
- `get_intelligent_completion_analysis()` - Detailed completion analysis

**dependencies.py** (~100 lines):
- `get_task_dependencies()` - Get list of task dependencies
- `check_task_dependencies_met()` - Verify dependencies satisfied
- `get_next_available_task()` - Find next ready-to-execute task
- `get_parallel_ready_tasks()` - Find tasks ready for parallel execution

**recovery.py** (~140 lines):
- `handle_task_failure()` - Handle task failures with recovery strategies
- `check_for_stagnation()` - Detect execution stagnation
- `_is_error_result()` - Check if result is an error
- `_summarize_error()` - Create error summary

**Checklist**:
- [x] Create `tasks/executor/` folder
- [x] Write `executor_core.py` with ExecutorCore class (169 lines)
- [x] Write `advancement.py` with AdvancementManager class (196 lines)
- [x] Write `tool_integration.py` with ToolIntegrationManager class (299 lines)
- [x] Write `completion.py` with CompletionManager class (154 lines)
- [x] Write `dependencies.py` with DependencyManager class (127 lines)
- [x] Write `recovery.py` with RecoveryManager class (159 lines)
- [x] Create `plan_execution_engine.py` composition class (178 lines)
- [x] Create `__init__.py` (5 lines) - exports PlanExecutor
- [x] Update imports in agent.py, base_agent/__init__.py, tasks/__init__.py
- [x] Run smoke tests to verify composition works
- [x] Delete old `execution_engine.py`
- [x] Run full integration tests

**Validation**: ✅ All files under 300 lines, all tests pass, composition pattern applied successfully

**Current Status**: ✅ PHASE 2.2b COMPLETE - ExecutionEngine decomposed using composition pattern

**Results**:
- Old execution_engine.py: 921 lines → 8 files averaging ~158 lines each
- Largest file: tool_integration.py at 299 lines (under 300-line limit)
- All files comply with project constraints (<500 lines)
- All public API maintained, backward compatible
- Composition pattern successfully applied (consistent with TaskManager refactor)

**Implementation Summary**:
- Created 7 focused manager classes (ExecutorCore, DependencyManager, AdvancementManager, ToolIntegrationManager, CompletionManager, RecoveryManager)
- Main composition class delegates all methods to appropriate managers
- Updated 3 import files (agent.py, base_agent/__init__.py, tasks/__init__.py)
- Deleted old execution_engine.py
- ✅ All smoke tests pass
- ✅ All integration tests pass

#### 2.3: Update Agent.py to Use New Initialization Pattern
**What**: Fix Agent.py to use new PlanExecutor signature (remove deleted parameters)
**Files**: Modify `base_agent/agent.py` (lines 103, 137-141)

**Current Problems**:
- Line 103: `TaskManager()` created WITHOUT `on_task_progression` callback  
- Lines 137-141: `PlanExecutor()` using parameters that were DELETED in Phase 2.2:
  - ❌ `task_manager=` (should be `task_store=`)
  - ❌ `event_manager=` (doesn't exist anymore!)

**Checklist**:
- [x] **Update line 103** - Fix TaskManager initialization:
  ```python
  # COMPLETED (lines 103-107)
  self.task_manager = TaskManager(
      on_task_progression=None,  # Wired after ExecutionEngine created
      verbose=verbose,
      output_dir=self.output_dir
  )
  ```

- [x] **Update lines 137-141** - Fix ExecutionEngine initialization:
  ```python
  # COMPLETED (lines 141-146)
  self.execution_engine = PlanExecutor(
      task_store=self.task_manager,  # ✅ TaskStore protocol
      on_task_complete=None,  # ✅ Optional callback
      on_task_advance=None,  # ✅ Optional callback
      verbose=self.verbose
  )
  ```

- [x] **Add after line 141** - Wire callback:
  ```python
  # COMPLETED (lines 148-152)
  # Connect TaskManager → ExecutionEngine (breaks circular dependency)
  self.task_manager.status.on_task_progression = (
      lambda tid: self.execution_engine.advancement.advance_task_progression()
  )
  ```

- [x] Remove any other `event_manager` usage with ExecutionEngine
- [x] Run integration tests with CIO/CRO agents
- [x] Verify task progression works

**Validation**: Agent initializes without errors, task progression works, no circular dependency

**Notes**:
- TaskManager implements TaskStore protocol (Phase 2.1)
- No circular ref: TaskManager doesn't store execution_engine attribute
- Callbacks optional: can add `on_task_complete`/`on_task_advance` if needed later

#### 2.4: Rename PlanExecutionEngine → PlanExecutor
**What**: Rename class and file for better naming convention
**Status**: ✅ COMPLETE (2025-10-22)

**What Was Done**:
- ✅ Renamed class `PlanExecutionEngine` → `PlanExecutor` in plan_execution_engine.py
- ✅ Renamed file `plan_execution_engine.py` → `plan_executor.py`
- ✅ Updated import in `tasks/executor/__init__.py`
- ✅ Updated import in `base_agent/agent.py` (line 12)
- ✅ Updated instantiation in `base_agent/agent.py` (line 141)
- ✅ Updated comments in `base_agent/agent.py` (lines 177, 189, 195)
- ✅ Updated exports in `base_agent/__init__.py` (lines 6, 16)
- ✅ Updated exports in `base_agent/tasks/__init__.py` (lines 6, 15)
- ✅ Updated documentation: CLAUDE.md, agent_v2.md, protocols/task_executor.py, evaluation/hallucinations.md

**Test Results**:
- ✅ All imports successful across all modules
- ✅ BaseAgent instantiation works correctly
- ✅ execution_engine is PlanExecutor type
- ✅ Callbacks properly wired
- ✅ Integration tests passing

**Validation**: ✅ COMPLETE - All references updated, all tests pass, folder/class names consistent

**Phase 2 Status**:
- ✅ Phase 2.1 COMPLETE: TaskManager refactored (741 → 8 files, composition pattern)
- ✅ Phase 2.2 COMPLETE: ExecutionEngine circular dependency broken (1116 → 921 lines)
- ✅ Phase 2.2b COMPLETE: ExecutionEngine decomposed (921 → 8 files, composition pattern)
- ✅ Phase 2.3 COMPLETE: Agent.py wired with correct initialization and callbacks
- ✅ Phase 2.4 COMPLETE: Class renamed PlanExecutionEngine → PlanExecutor, file renamed

**Phase 2 Summary (ALL PHASES 100% COMPLETE)**:
- TaskManager: 741 lines → 8 focused modules (17-236 lines each)
- ExecutionEngine: 1116 lines → 8 focused modules (5-299 lines each)
- Circular dependency broken using callback pattern
- TaskStore protocol implemented via delegation
- Composition pattern consistently applied across both major components
- Agent.py initialization fixed with proper parameters (Phase 2.3)
- Class renamed to PlanExecutor, file renamed to plan_executor.py (Phase 2.4)
- All imports updated across 5 code files + 4 documentation files
- All integration tests passing
- **Next**: Phase 3 - Extract agent.py components

---

### Phase 3: Extract Agent Components (Duration: 2 weeks)

**Goal**: Break down agent.py from 1130 � ~300 lines

#### 3.1: Create ReActExecutor (~400 lines)
**What**: Extract ReAct loop from agent.py
**Files**: Create `execution/react_executor.py`
**Checklist**:
- [ ] Create `execution/__init__.py`
- [ ] Create `execution/react_executor.py` (~400 lines)
- [ ] Extract ReAct loop logic from agent.py (lines 476-1015)
- [ ] Create class: ReActExecutor
- [ ] Method: `execute_iteration(iteration, messages, tools, tool_functions) -> IterationResult`
- [ ] Method: `handle_tool_calls(tool_calls, messages) -> List[ToolResult]`
- [ ] Method: `check_finality(assistant_message, final_keywords) -> Tuple[bool, str]`
- [ ] Write unit tests for ReActExecutor
- [ ] Test with mock tool calls

**Validation**: Tests pass, can execute ReAct iteration in isolation

#### 3.2: Create StagnationTracker (~80 lines)
**What**: Extract stagnation detection logic
**Files**: Create `execution/stagnation_tracker.py`
**Checklist**:
- [ ] Create `execution/stagnation_tracker.py` (~80 lines)
- [ ] Extract logic from agent.py (lines 80-84, 617-620, 1016-1077)
- [ ] Create class: StagnationTracker
- [ ] Method: `update(tool_name, args) -> None`
- [ ] Method: `is_stagnating() -> bool`
- [ ] Method: `get_recovery_message(task_context) -> str`
- [ ] Method: `reset() -> None`
- [ ] Write unit tests
- [ ] Test stagnation detection with repeated actions

**Validation**: Tests pass, detects stagnation correctly

#### 3.3: Create ContextBuilder (~150 lines)
**What**: Extract prompt building and context injection logic
**Files**: Create `prompting/context_builder.py`
**Checklist**:
- [ ] Create `prompting/__init__.py`
- [ ] Create `prompting/context_builder.py` (~150 lines)
- [ ] Extract prompt logic from agent.py (lines 199-270, 424-463, 500-548, etc.)
- [ ] Create class: ContextBuilder
- [ ] Method: `build_initial_messages(system_prompt, user_prompt, plan_first, domain_memory) -> List[Dict]`
- [ ] Method: `build_task_prompt(iteration, task_context, completion_analysis) -> str`
- [ ] Method: `build_plan_context(iteration, task_context, completion_analysis) -> str`
- [ ] Method: `build_rejection_message(completion_status, task_context) -> str`
- [ ] Method: `build_periodic_status_update(iteration, task_context) -> str`
- [ ] Write unit tests
- [ ] Test prompt generation with mock data

**Validation**: Tests pass, prompts generated correctly

#### 3.4: Refactor agent.py (1130 � ~300 lines)
**What**: Use new extracted components
**Files**: Modify `base_agent/agent.py`
**Checklist**:
- [ ] Import new modules:
  ```python
  from .execution.react_executor import ReActExecutor
  from .execution.stagnation_tracker import StagnationTracker
  from .prompting.context_builder import ContextBuilder
  ```
- [ ] Update `__init__` to create helper components:
  ```python
  self.react_executor = ReActExecutor(self)
  self.stagnation_tracker = StagnationTracker(threshold=4)
  self.context_builder = ContextBuilder(self)
  ```
- [ ] Simplify run() method to delegate:
  ```python
  def run(self) -> Dict[str, Any]:
      # Setup
      messages = self.context_builder.build_initial_messages(...)

      # Main loop
      for i in range(1, self.max_iterations + 1):
          # Execute iteration
          result = self.react_executor.execute_iteration(i, messages, ...)

          # Check stagnation
          if self.stagnation_tracker.is_stagnating():
              # Handle stagnation
              pass

          # ... rest of loop logic

      return final_result
  ```
- [ ] Remove extracted code from agent.py
- [ ] Verify file is ~300 lines
- [ ] Run full integration tests with all domain agents

**Validation**: All tests pass, agent.py is ~300 lines, all agents work

**Phase 3 Complete**: agent.py refactored into focused modules

---

### Phase 4: Migrate to Context-Aware Validator (Duration: 2-3 weeks)

**Goal**: Gradually replace 592-line validator with modular, context-aware version while maintaining production stability

#### 4.1: Identify All Validator Usage
**What**: Find everywhere old validator is used and document expected behavior
**Files**: Search entire codebase
**Checklist**:
- [ ] Search for: `from .tasks.validator import TaskValidator`
- [ ] Search for: `TaskValidator(`
- [ ] Search for: `.validate_main_task_completion(`
- [ ] Search for: `.validate_subtask_completion(`
- [ ] Search for: `.validate_tool_result_for_completion(`
- [ ] Create list of all files using validator (likely: executor.py, agent.py)
- [ ] Document current behavior: What tasks/subtasks are marked complete/incomplete?
- [ ] Capture baseline outputs from 10+ real agent runs for comparison

**Validation**: Complete list of files, documented baseline behavior

#### 4.2: Add Parallel Validation (NO behavior change yet)
**What**: Run both old and new validators side-by-side, compare results
**Files**: `tasks/executor.py`, `config.py`
**Checklist**:
- [ ] Add to `config.py`:
  ```python
  # Validator migration settings
  USE_NEW_VALIDATOR = False  # Still using old validator
  ENABLE_PARALLEL_VALIDATION = True  # Compare both validators
  LOG_VALIDATOR_MISMATCHES = True  # Alert on differences
  ```
- [ ] Update `tasks/executor.py` to run both validators:
  ```python
  # OLD validator (still in use)
  is_complete_old, confidence, explanation = self.old_validator.validate_main_task_completion(task)

  # NEW validator (parallel check only)
  is_complete_new = self.new_validator.is_main_task_complete(task)

  # Compare and log mismatches
  if is_complete_old != is_complete_new:
      logger.warning(f"Validator mismatch on task {task.id}: "
                     f"old={is_complete_old}, new={is_complete_new}")

  # Use OLD validator result (no behavior change)
  return is_complete_old
  ```
- [ ] Test with all domain agents (CIO, CRO, Industry)
- [ ] Collect mismatch logs for 3-5 days
- [ ] Investigate any mismatches (are they expected? bugs in new validator?)

**Validation**: No behavior changes, mismatch data collected and analyzed

#### 4.3: Fix Validator Discrepancies
**What**: Resolve any cases where new validator disagrees with old validator
**Files**: `tasks/validation/` modules
**Checklist**:
- [ ] Review all logged mismatches from 4.2
- [ ] For each mismatch, determine:
  - Is old validator correct? (Fix new validator)
  - Is new validator correct? (Document improvement, keep new behavior)
  - Are both wrong? (Fix new validator, plan to fix old after switch)
- [ ] Update `tasks/validation/` code to fix issues
- [ ] Re-run parallel validation for 2-3 days
- [ ] Verify mismatch rate < 1% (and all remaining mismatches are documented/expected)

**Validation**: New validator matches old validator in 99%+ of cases

#### 4.4: Switch to New Validator (SINGLE ATOMIC COMMIT)
**What**: Make new validator primary, keep old validator as fallback
**Files**: `tasks/executor.py`, `config.py`
**Checklist**:
- [ ] **IN SINGLE COMMIT**:
  - [ ] Update `config.py`:
    ```python
    USE_NEW_VALIDATOR = True  # NOW using new validator
    ENABLE_PARALLEL_VALIDATION = True  # Still compare (reversed)
    KEEP_OLD_VALIDATOR_FALLBACK = True  # Safety net
    ```
  - [ ] Update `tasks/executor.py`:
    ```python
    # NEW validator (primary)
    is_complete_new = self.new_validator.is_main_task_complete(task)

    # OLD validator (fallback check)
    is_complete_old, confidence, _ = self.old_validator.validate_main_task_completion(task)

    # Compare and log (reversed)
    if is_complete_old != is_complete_new:
        logger.info(f"Validator difference on task {task.id}: "
                    f"new={is_complete_new}, old={is_complete_old}")

    # Use NEW validator result
    return is_complete_new
    ```
  - [ ] Update all method calls to use boolean returns:
    ```python
    # OLD
    is_complete, confidence, explanation = self.task_validator.validate_main_task_completion(task)
    if confidence >= 0.7:
        # ...

    # NEW
    is_complete = self.task_validator.is_main_task_complete(task)
    if is_complete:
        # ...
    ```
- [ ] Run full test suite
- [ ] Test with all domain agents (CIO, CRO, Industry)
- [ ] Monitor for 5-7 days in production
- [ ] Compare outputs with baseline from 4.1

**Validation**: New validator active, outputs match baseline, no regressions

#### 4.5: Remove Old Validator
**What**: Delete old validator after new validator proven stable
**Files**: `tasks/validator.py` (old), `tasks/executor.py`, `config.py`
**Checklist**:
- [ ] Verify new validator has been stable for 1+ week
- [ ] Verify no critical issues reported
- [ ] Remove feature flags from `config.py`:
  ```python
  # DELETE these lines
  USE_NEW_VALIDATOR = True
  ENABLE_PARALLEL_VALIDATION = True
  KEEP_OLD_VALIDATOR_FALLBACK = True
  ```
- [ ] Update imports in `tasks/executor.py`:
  ```python
  # OLD
  from .validator import TaskValidator  # Old validator
  from .completion_validator import CompletionValidator  # New validator

  # NEW
  from .validation.completion_validator import CompletionValidator as TaskValidator
  ```
- [ ] Delete `tasks/validator.py` (old 592-line file)
- [ ] Remove all old validator references from executor.py
- [ ] Run full test suite
- [ ] Deploy to production

**Validation**: Old validator deleted, new validator is only validator

**Phase 4 Complete**: Context-aware validator in production, old validator deleted, no regressions

---

### Phase 5: Final Cleanup (Duration: 1 week)

**Goal**: Remove all unused code and verify clean state

#### 5.1: Delete Unused Files
**What**: Remove old code files
**Files**: Delete old implementations
**Checklist**:
- [ ] **DELETE** `base_agent/core/parser.py` (replaced by result_parser.py)
- [ ] **DELETE** `base_agent/events/manager.py` (replaced by callbacks)
- [ ] **DELETE** `base_agent/events/__init__.py`
- [ ] **DELETE** entire `base_agent/events/` directory
- [ ] Search codebase for any remaining imports of deleted files
- [ ] Fix any broken imports (should be none if previous phases done correctly)

**Validation**: No broken imports, all tests pass

#### 5.2: Verify No Circular Dependencies
**What**: Confirm clean architecture
**Files**: All files
**Checklist**:
- [ ] Run dependency analyzer (can use `import-linter` or manual check)
- [ ] Verify: TaskManager does NOT import ExecutionEngine
- [ ] Verify: ExecutionEngine imports TaskStore (Protocol) not TaskManager
- [ ] Verify: No circular imports in any files
- [ ] Draw dependency graph to visualize clean architecture

**Validation**: Zero circular dependencies

#### 5.3: Verify File Size Compliance
**What**: Ensure all files under 500 lines
**Files**: All .py files in agentic_framework/
**Checklist**:
- [ ] Run: `find base_agent -name "*.py" -exec wc -l {} + | sort -rn`
- [ ] Verify: agent.py d 300 lines
- [ ] Verify: executor.py d 280 lines
- [ ] Verify: manager.py d 180 lines
- [ ] Verify: validator.py d 100 lines
- [ ] Verify: ALL files d 500 lines
- [ ] Document final line counts

**Validation**: 100% file size compliance

#### 5.4: Run Full Test Suite
**What**: Comprehensive testing
**Files**: All tests
**Checklist**:
- [ ] Run unit tests: All new components
- [ ] Run integration tests: Full agent execution
- [ ] Test CIO agent: Portfolio construction
- [ ] Test CRO agent: Risk analysis
- [ ] Test Industry agent: Sector analysis
- [ ] Compare outputs with baseline (golden outputs)
- [ ] Performance benchmarks: Iteration speed within 5% of baseline
- [ ] Memory usage: Within 10% of baseline

**Validation**: All tests pass, performance acceptable

#### 5.5: Update Documentation
**What**: Document new architecture
**Files**: CLAUDE.md, code docstrings
**Checklist**:
- [ ] Update CLAUDE.md with new structure:
  - New directory organization
  - Protocol-based architecture
  - Callback pattern instead of events
  - Simplified validation approach
- [ ] Add/update docstrings for all public methods
- [ ] Document breaking changes (for other developers)
- [ ] Create migration guide if needed
- [ ] Update architecture diagrams

**Validation**: Documentation complete and accurate

#### 5.6: Final Metrics Validation
**What**: Verify success criteria met
**Files**: N/A - analysis
**Checklist**:
- [ ] File Size Compliance: 100% 
- [ ] Largest File: <400 lines 
- [ ] Code Duplication: <3% 
- [ ] Circular Dependencies: 0 
- [ ] Unused Code: 0 lines 
- [ ] Test Coverage: >70% 
- [ ] Generate final metrics report
- [ ] Compare with baseline metrics

**Validation**: All success criteria met

**Phase 5 Complete**: Clean, maintainable codebase ready for production

---

## SECTION 3: DETAILED EXECUTION GUIDES

This section provides step-by-step instructions for key tasks with exact code, files, and techniques.

### GUIDE 1.2: Create Protocols for Structural Typing

**Context**: We define Protocols so ExecutionEngine can depend on abstractions (TaskStore) rather than concrete classes (TaskManager). This enables dependency inversion and breaks circular dependencies using Python's structural typing.

**Files to Create**:
1. `app/core/agentic_framework/base_agent/protocols/__init__.py`
2. `app/core/agentic_framework/base_agent/protocols/task_store.py`
3. `app/core/agentic_framework/base_agent/protocols/task_executor.py`
4. `app/core/agentic_framework/base_agent/protocols/completion_checker.py`

#### Execution Steps

**Step 1**: Create protocols directory
```bash
mkdir -p app/core/agentic_framework/base_agent/protocols
```

**Step 2**: Create `__init__.py`
```python
# app/core/agentic_framework/base_agent/protocols/__init__.py
"""Protocols for dependency inversion and structural typing."""

from .task_store import TaskStore
from .task_executor import TaskExecutor
from .completion_checker import CompletionChecker

__all__ = ['TaskStore', 'TaskExecutor', 'CompletionChecker']
```

**Step 3**: Create `task_store.py` - See detailed code in original plan above
**Step 4**: Create `task_executor.py` - See detailed code in original plan above
**Step 5**: Create `completion_checker.py` - See detailed code in original plan above

**Step 6**: Verify imports work
```python
# test_protocols.py
from app.core.agentic_framework.base_agent.protocols import (
    TaskStore,
    TaskExecutor,
    CompletionChecker
)
print(" All protocols imported successfully")
```

---

### GUIDE 1.3: Create Unified ToolResultParser

**Context**: Currently, tool results are parsed in 4 different places with inconsistent logic. We need ONE parser that handles all result types uniformly.

**File to Create**: `app/core/agentic_framework/base_agent/core/result_parser.py`

See full implementation in Section 1 above - includes complete code for ToolResultParser class with all methods and comprehensive test suite.

---

### GUIDE 1.4: Create Simplified Validator

**Context**: The current 592-line TaskValidator is over-engineered. We'll replace it with simple boolean checks (~100 lines).

**File to Create**: `app/core/agentic_framework/base_agent/tasks/completion_validator.py`

See full implementation in Section 1 above - includes complete CompletionValidator class with simple rules and comprehensive test suite.

---

### GUIDE 2.1: Refactor TaskManager

**Context**: Remove analytics code, delete circular dependency, ensure TaskStore protocol compliance.

**File to Modify**: `app/core/agentic_framework/base_agent/tasks/manager.py`

**Specific Changes**:

1. **Delete Line 17** - Remove back-reference:
   ```python
   # DELETE THIS LINE
   self.execution_engine = None  # Will be set by execution engine
   ```

2. **Delete Lines 184-195** - Remove tool routing audit:
   ```python
   # DELETE THIS ENTIRE METHOD
   def record_tool_routing(self, task_id, subtask_id, tool_name, is_relevant):
       ...
   ```

3. **Delete Lines 271-310** - Remove execution analytics:
   ```python
   # DELETE THIS ENTIRE METHOD
   def get_execution_analytics(self) -> Dict[str, Any]:
       ...
   ```

4. **Delete Lines 354-365** in `update_task_status` - Remove execution_engine calls:
   ```python
   # DELETE THIS BLOCK
   if (should_complete and
       self.execution_engine and
       self.execution_engine.plan_loaded and
       self.execution_engine.current_main_task and ...):
       success, message = self.execution_engine.advance_task_progression()
   ```

5. **Verify** file is now ~180 lines

---

### GUIDE 2.2: Refactor ExecutionEngine

**Context**: Break circular dependency, remove analytics, use callbacks.

**File to Modify**: `app/core/agentic_framework/base_agent/tasks/execution_engine.py`

**Specific Changes**:

1. **Update imports** (add at top):
   ```python
   from typing import Optional, Callable
   from ..protocols.task_store import TaskStore
   ```

2. **Update `__init__` signature** (lines 17-36):
   ```python
   def __init__(
       self,
       task_store: TaskStore,  # Changed from task_manager: TaskManager
       on_task_complete: Optional[Callable[[int], None]] = None,  # NEW
       on_task_advance: Optional[Callable[[int, str], None]] = None,  # NEW
       verbose: bool = True
   ):
       self.task_store = task_store  # Changed from self.task_manager
       self.on_task_complete = on_task_complete  # NEW
       self.on_task_advance = on_task_advance  # NEW
       self.verbose = verbose
       self.current_main_task = None
       self.current_subtask = None
       self.plan_loaded = False

       # DELETE THIS LINE - NO BACK-REFERENCE
       # self.task_manager.execution_engine = self
   ```

3. **Replace all `self.task_manager` with `self.task_store`** throughout file

4. **Replace event emissions with callbacks**:
   ```python
   # OLD
   self.event_manager.emit(AgentEvent.TASK_COMPLETED, {...})

   # NEW
   if self.on_task_complete:
       self.on_task_complete(task_id)
   ```

5. **Delete Lines 946-984** - Remove parallel execution simulation
6. **Delete Lines 985-1067** - Remove analytics report
7. **Delete Lines 1069-1116** - Remove recommendations

8. **Verify** file is now ~280 lines

---

*[Additional detailed guides for remaining phases would follow similar pattern...]*

---

## Summary

This comprehensive refactoring plan provides:

1. **Section 1**: Deep analysis of all violations with specific line numbers and examples
2. **Section 2**: Clear phased plan with actionable checklists
3. **Section 3**: Detailed execution guides with exact code and step-by-step instructions

**Key Principles**:
- Build new components first
- Gradual migration for critical components (validator with parallel validation)
- Delete old code after proven stable (no backwards compatibility)
- Test extensively at each phase
- 100% file size compliance
- Zero circular dependencies

**Expected Outcomes**:
- agent.py: 1130 � ~300 lines (73% reduction)
- executor.py: 1116 � ~280 lines (75% reduction)
- manager.py: 741 � ~180 lines (76% reduction)
- validation/: 592 � ~240 lines across 3 files (59% reduction, context-aware preserved)
- **Total**: ~36% codebase reduction
- **Quality**: All files under 500 lines, 0 circular deps, >70% test coverage

---

## SECTION 4: NEW AGENTIC FRAMEWORK STRUCTURE

This section visualizes the before/after structure of the agentic framework after all refactoring phases are complete.

### Current Structure (Before Refactoring)

```
app/core/agentic_framework/base_agent/
├── agent.py                           (1130 lines) ❌ 226% over limit
├── tool_registry.py                   (457 lines)  ✅
├── config.py                          (new file)
│
├── core/
│   ├── __init__.py
│   ├── logger.py                      (~150 lines) ✅
│   ├── parser.py                      (~80 lines)  ⚠️  DELETE - replaced by result_parser.py
│   ├── utilities.py                   (531 lines)  ❌ 106% over limit
│   └── arg_parser.py                  (399 lines)  ✅
│
├── tasks/
│   ├── __init__.py
│   ├── manager.py                     (741 lines)  ❌ 148% over limit
│   ├── execution_engine.py            (1116 lines) ❌ 223% over limit
│   ├── validator.py                   (592 lines)  ❌ 118% over limit
│   └── models.py                      (~200 lines) ✅
│
├── events/                             ⚠️  DELETE ENTIRE FOLDER
│   ├── __init__.py
│   └── manager.py                     (~150 lines)
│
├── memory/
│   ├── __init__.py
│   ├── domain_memory.py               (445 lines)  ✅
│   └── episodic_memory.py             (~180 lines) ✅
│
└── utils/
    ├── __init__.py
    └── path_utils.py                  (~50 lines)  ✅

TOTALS:
- Total Files: 20 files
- Files Over 500 Lines: 4 files (agent.py, manager.py, execution_engine.py, validator.py)
- Largest File: 1130 lines (agent.py)
- Total Lines: ~6,200 lines in base_agent/
- Circular Dependencies: 1 (TaskManager ↔ ExecutionEngine)
- Compliance Rate: 80%
```

### New Structure (After Refactoring)

```
app/core/agentic_framework/base_agent/
├── agent.py                           (~300 lines) ✅ 73% reduction
├── tool_registry.py                   (457 lines)  ✅
├── config.py                          (~30 lines)  ✅ NEW - feature flags
│
├── protocols/                         ✨ NEW - Protocol-based abstractions
│   ├── __init__.py                    (~10 lines)  ✅
│   ├── task_store.py                  (~80 lines)  ✅ TaskStore Protocol
│   ├── task_executor.py               (~50 lines)  ✅ TaskExecutor Protocol
│   └── completion_checker.py          (~30 lines)  ✅ CompletionChecker Protocol
│
├── core/
│   ├── __init__.py
│   ├── logger.py                      (~150 lines) ✅
│   ├── result_parser.py               (~120 lines) ✅ NEW - unified parser
│   ├── utilities.py                   (~400 lines) ✅ Cleaned up
│   └── arg_parser.py                  (399 lines)  ✅
│
├── execution/                          ✨ NEW - Extracted from agent.py
│   ├── __init__.py                    (~10 lines)  ✅
│   ├── react_executor.py              (~400 lines) ✅ ReAct loop logic
│   └── stagnation_tracker.py          (~80 lines)  ✅ Stagnation detection
│
├── prompting/                          ✨ NEW - Extracted from agent.py
│   ├── __init__.py                    (~10 lines)  ✅
│   └── context_builder.py             (~150 lines) ✅ Prompt generation
│
├── tasks/
│   ├── __init__.py
│   ├── manager.py                     (~180 lines) ✅ 76% reduction
│   ├── executor.py                    (~280 lines) ✅ 75% reduction (renamed)
│   ├── models.py                      (~200 lines) ✅
│   │
│   └── validation/                     ✨ NEW - Context-aware validator (modular)
│       ├── __init__.py                (~10 lines)  ✅
│       ├── patterns.py                (~40 lines)  ✅ Safe phrases & error patterns
│       ├── error_detection.py         (~80 lines)  ✅ Context-aware error checking
│       └── completion_validator.py    (~120 lines) ✅ Boolean validator (no confidence)
│
├── memory/
│   ├── __init__.py
│   ├── domain_memory.py               (445 lines)  ✅
│   └── episodic_memory.py             (~180 lines) ✅
│
└── utils/
    ├── __init__.py
    └── path_utils.py                  (~50 lines)  ✅

TOTALS:
- Total Files: 30 files (10 new, 3 deleted)
- Files Over 500 Lines: 0 files ✅
- Largest File: 457 lines (tool_registry.py) ✅
- Total Lines: ~3,950 lines in base_agent/ (36% reduction)
- Circular Dependencies: 0 ✅
- Compliance Rate: 100% ✅
```

### File Size Comparison Table

| File | Before | After | Reduction | Status |
|------|--------|-------|-----------|--------|
| **agent.py** | 1130 lines | ~300 lines | **-830 lines (73%)** | ✅ Compliant |
| **execution_engine.py → executor.py** | 1116 lines | ~280 lines | **-836 lines (75%)** | ✅ Compliant |
| **manager.py** | 741 lines | ~180 lines | **-561 lines (76%)** | ✅ Compliant |
| **validator.py → validation/** | 592 lines | ~240 lines (3 files) | **-352 lines (59%)** | ✅ Compliant |
| **utilities.py** | 531 lines | ~400 lines | **-131 lines (25%)** | ✅ Compliant |
| **NEW: react_executor.py** | 0 | ~400 lines | +400 lines | ✅ Extracted from agent.py |
| **NEW: context_builder.py** | 0 | ~150 lines | +150 lines | ✅ Extracted from agent.py |
| **NEW: stagnation_tracker.py** | 0 | ~80 lines | +80 lines | ✅ Extracted from agent.py |
| **NEW: result_parser.py** | 0 | ~120 lines | +120 lines | ✅ Unified 4 parsers |
| **NEW: protocols/** (4 files) | 0 | ~170 lines | +170 lines | ✅ Protocol abstractions |
| **NEW: validation/** (3 files) | 0 | ~120 lines | +120 lines | ✅ Context-aware validator (modular) |
| **DELETED: events/** | ~150 lines | 0 | -150 lines | ✅ Replaced by callbacks |
| **DELETED: parser.py** | ~80 lines | 0 | -80 lines | ✅ Replaced by result_parser.py |
| **Net Change** | **~6,200 lines** | **~3,950 lines** | **-2,250 lines (36%)** | **✅ SUCCESS** |

### Architecture Visualization

#### Before: Circular Dependencies & Tight Coupling

```
┌─────────────────────────────────────────────────────────────┐
│                         BaseAgent                            │
│                       (1130 lines)                           │
│  ┌──────────────────────────────────────���─────────────────┐ │
│  │ • ReAct Loop (600 lines)                               │ │
│  │ • Stagnation Detection                                 │ │
│  │ • Prompt Building                                      │ │
│  │ • Tool Execution                                       │ │
│  │ • Task Coordination                                    │ │
│  │ • Token Counting                                       │ │
│  │ • Memory Refresh                                       │ │
│  └────────────────────────────────────────────────────────┘ │
│                           │ │                                │
│                           │ │ Creates directly               │
│                           ▼ ▼                                │
│     ┌─────────────────────────────────────────┐             │
│     │         TaskManager (741 lines)         │             │
│     │  ◄─────────────────────────────────────┐│             │
│     └─────────────┬───────────────────────────┘│             │
│                   │                            │             │
│                   │ Sets back-reference        │             │
│                   ▼                            │             │
│     ┌─────────────────────────────────────────┴┐            │
│     │    ExecutionEngine (1116 lines)          │            │
│     │                                           │            │
│     │  • Calls task_manager.execution_engine   │            │
│     │  • Complex validation logic              │            │
│     │  • Unused analytics (300 lines)          │            │
│     └───────────────────────────────────────────┘            │
│                   │                                          │
│                   │ Direct coupling                          │
│                   ▼                                          │
│     ┌───────────────────────────────────────────┐           │
│     │      TaskValidator (592 lines)            │           │
│     │  • Confidence scoring                     │           │
│     │  • Multiple overlapping validators        │           │
│     │  • Arbitrary thresholds                   │           │
│     └───────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘

PROBLEMS:
❌ Circular dependency: TaskManager ↔ ExecutionEngine
❌ Tight coupling: No interfaces, concrete classes everywhere
❌ Responsibilities mixed: agent.py does 7+ different jobs
❌ Cannot test in isolation
❌ Cannot swap implementations
```

#### After: Clean Architecture with Protocol-Based Abstractions

```
┌─────────────────────────────────────────────────────────────────┐
│                         BaseAgent                                │
│                        (~300 lines)                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ FOCUSED RESPONSIBILITIES:                                  │ │
│  │ • Orchestration only                                       │ │
│  │ • Tool registration & dispatch                             │ │
│  │ • Delegates to specialized components                      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                           │ │ │                                  │
│          ┌────────────────┘ │ └────────────────┐                │
│          │ Delegates        │                  │                │
│          ▼                  ▼                  ▼                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ ReActExecutor│  │StagnationTrkr│  │ContextBuilder│          │
│  │  (400 lines) │  │  (80 lines)  │  │  (150 lines) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│          Creates (but passes as interface)                      │
│                           │                                      │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────┐             │
│  │         TaskManager (~180 lines)               │             │
│  │         implements TaskStore Protocol          │             │
│  │  ┌──────────────────────────────────────────┐  │             │
│  │  │ CLEAN RESPONSIBILITIES:                  │  │             │
│  │  │ • State storage only                     │  │             │
│  │  │ • CRUD operations                        │  │             │
│  │  │ • No analytics                           │  │             │
│  │  │ • No circular references                 │  │             │
│  │  └──────────────────────────────────────────┘  │             │
│  └────────────────────────────────────────────────┘             │
│                           │ Passed as TaskStore interface       │
│                           ▼                                      │
│  ┌────────────────────────────────────────────────┐             │
│  │      PlanExecutor (~280 lines)                 │             │
│  │      uses TaskStore Protocol                   │             │
│  │  ┌──────────────────────────────────────────┐  │             │
│  │  │ CLEAN RESPONSIBILITIES:                  │  │             │
│  │  │ • Task execution only                    │  │             │
│  │  │ • Uses callbacks (not events)            │  │             │
│  │  │ • No analytics                           │  │             │
│  │  │ • No back-references                     │  │             │
│  │  └──────────────────────────────────────────┘  │             │
│  └────────────┬───────────────────────────────────┘             │
│               │ Uses                                             │
��               ▼                                                  │
│  ┌────────────────────────────────────────────────┐             │
│  │   CompletionValidator (~100 lines)             │             │
│  │   implements CompletionChecker Protocol        │             │
│  │  ┌──────────────────────────────────────────┐  │             │
│  │  │ SIMPLE VALIDATION:                       │  │             │
│  │  │ • Boolean results only                   │  │             │
│  │  │ • No confidence scoring                  │  │             │
│  │  │ • Clear rules                            │  │             │
│  │  └──────────────────────────────────────────┘  │             │
│  └────────────────────────────────────────────────┘             │
│                                                                  │
│  ┌────────────────────────────────────────────────┐             │
│  │        Interfaces (Protocols)                  │             │
│  │  ┌──────────────────────────────────────────┐  │             │
│  │  │ • TaskStore Protocol                     │  │             │
│  │  │ • TaskExecutor Protocol                  │  │             │
│  │  │ • CompletionChecker Protocol             │  │             │
│  │  │                                          │  │             │
│  │  │ Enable dependency inversion              │  │             │
│  │  └──────────────────────────────────────────┘  │             │
│  └────────────────────────────────────────────────┘             │
└─────────────────────────────────────────────────────────────────┘

BENEFITS:
✅ Zero circular dependencies
✅ Protocol-based abstractions (Dependency Inversion)
✅ Each component has single responsibility
✅ Easy to test in isolation
✅ Easy to swap implementations
✅ Clear separation of concerns
```

### Directory Tree: Complete Structure

```
app/core/agentic_framework/
│
├── config.py                          (~30 lines)   ✨ NEW
│
├── base_agent/
│   ├── __init__.py
│   ├── agent.py                       (~300 lines)  ✅ Refactored
│   ├── tool_registry.py               (457 lines)   ✅
│   │
│   ├── protocols/                     ✨ NEW FOLDER
│   │   ├── __init__.py                (~10 lines)
│   │   ├── task_store.py              (~80 lines)   Protocol
│   │   ├── task_executor.py           (~50 lines)   Protocol
│   │   └── completion_checker.py      (~30 lines)   Protocol
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── logger.py                  (~150 lines)  ✅
│   │   ├── result_parser.py           (~120 lines)  ✨ NEW
│   │   ├── utilities.py               (~400 lines)  ✅ Cleaned
│   │   └── arg_parser.py              (399 lines)   ✅
│   │
│   ├── execution/                      ✨ NEW FOLDER
│   │   ├── __init__.py                (~10 lines)
│   │   ├── react_executor.py          (~400 lines)  ✨ NEW
│   │   └── stagnation_tracker.py      (~80 lines)   ✨ NEW
│   │
│   ├── prompting/                      ✨ NEW FOLDER
│   │   ├── __init__.py                (~10 lines)
│   │   └── context_builder.py         (~150 lines)  ✨ NEW
│   │
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── manager.py                 (~180 lines)  ✅ Refactored
│   │   ├── executor.py                (~280 lines)  ✅ Refactored & Renamed
│   │   ├── validator.py               (~100 lines)  ✅ Replaced
│   │   └── models.py                  (~200 lines)  ✅
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── domain_memory.py           (445 lines)   ✅
│   │   └── episodic_memory.py         (~180 lines)  ✅
│   │
│   └── utils/
│       ├── __init__.py
│       └── path_utils.py              (~50 lines)   ✅
│
└── tool_lib/                           (Unchanged - not part of refactoring)
    ├── base_tools/
    ├── data_tools/
    ├── risk_tools/
    ├── portfolio_tools/
    ├── ticker_tools/
    └── agent_specific_tools/
```

### Key Improvements Summary

#### 1. File Size Compliance
- **Before**: 4 files over 500 lines (20% non-compliant)
- **After**: 0 files over 500 lines (100% compliant)
- **Largest file reduced**: 1130 → 457 lines

#### 2. Code Organization
- **Before**: Mixed responsibilities, god objects
- **After**: Clear separation by concern
  - `protocols/`: Protocol definitions
  - `execution/`: ReAct loop and stagnation tracking
  - `prompting/`: Context and prompt generation
  - `tasks/`: Task management, execution, validation
  - `core/`: Utilities, logging, parsing

#### 3. Circular Dependencies
- **Before**: 1 critical (TaskManager ↔ ExecutionEngine)
- **After**: 0 (Protocol-based with callbacks)

#### 4. Code Duplication
- **Before**: ~15% duplication (4 parsers, 2 evidence collectors)
- **After**: <3% duplication (unified parser, clean separation)

#### 5. Testability
- **Before**: Difficult (tight coupling, circular deps)
- **After**: Easy (Protocol mocking, isolated components)

#### 6. Total Line Count
- **Before**: ~6,200 lines
- **After**: ~3,800 lines
- **Reduction**: 2,400 lines (39% reduction)

### Migration Impact

#### Breaking Changes
1. ❌ `TaskValidator` API changed (confidence scores removed)
2. ❌ `ExecutionEngine` renamed to `PlanExecutor`
3. ❌ Event system replaced with callbacks
4. ❌ `events/` module deleted entirely

#### Non-Breaking Changes
1. ✅ `TaskManager` API unchanged (still has same public methods)
2. ✅ `BaseAgent.run()` signature unchanged
3. ✅ All tool functions work as before
4. ✅ Domain agents (CIO, CRO) work without modification

#### Rollout Strategy
- **Phase 1-3**: Build new components (zero impact)
- **Phase 4**: Single atomic commit for validator switch
- **Phase 5**: Delete old code (cleanup only)

---

**Document Version:** 2.0
**Created:** 2025-10-21
**Status:** Ready for Implementation
**Next Steps:** Begin Phase 1.1 - Create directory structure
