# Agentic Framework Refactoring Plan

**Date:** 2025-10-14
**Status:** Draft
**Priority:** High

---

## Executive Summary

The `app/core/agentic_framework/` is the heart of ProphitAI but has accumulated technical debt that violates core development principles (KISS, YAGNI, DRY). This refactoring plan provides a systematic approach to reorganize and simplify the framework while maintaining functionality.

**Key Issues Identified:**
- Multiple files exceed code constraints (agent.py: 1130 lines, execution_engine.py: 1116 lines)
- Complex dependencies and tight coupling between components
- Duplication in tool registration and result parsing logic
- Over-engineered validation systems
- Unclear separation of concerns in the task management system

**Estimated Impact:**
- Reduce total LOC by ~25-30%
- Improve maintainability score from ~40% to ~75%
- Enable easier testing and extensibility
- Align with KISS, YAGNI, and DRY principles

---

## Current State Analysis

### File Size Violations (Max: 500 lines)

**Critical Violations:**
1. **`base_agent/agent.py`** - 1130 lines (226% over limit)
   - Massive ReAct loop implementation (lines 412-1077)
   - Mixed concerns: orchestration, tool execution, task management, stagnation detection
   - Deeply nested conditionals and duplicate prompt injection logic

2. **`base_agent/tasks/execution_engine.py`** - 1116 lines (223% over limit)
   - Complex task progression logic intertwined with validation
   - Duplicate evidence collection and analysis methods
   - Over-engineered parallel execution simulation (lines 926-1116)

3. **`tool_lib/data_tools/stock_screener.py`** - 848 lines (170% over limit)
   - Single monolithic screening function
   - Should be split into modular screener components

4. **`base_agent/tasks/manager.py`** - 741 lines (148% over limit)
   - Mixed simple state management with complex analytics
   - Duplicate task update logic for main tasks vs subtasks

5. **`base_agent/tasks/validator.py`** - 592 lines (118% over limit)
   - Excessive validation rules with significant overlap
   - Pattern matching logic duplicated across multiple methods

**Other Violations:**
- `base_agent/core/utilities.py` - 531 lines (106% over)
- `base_agent/tool_registry.py` - 457 lines (91% over)
- `base_agent/memory/domain_memory.py` - 445 lines (89% over)

### Architectural Issues

#### 1. **Violation of Single Responsibility Principle**

**BaseAgent (agent.py):**
- Orchestrates execution (ReAct loop)
- Manages tools registration and dispatch
- Handles task management coordination
- Implements stagnation detection
- Manages token counting and message logging
- Handles plan injection and context management
- **Problem:** One class doing 6+ distinct jobs

**TaskManager (manager.py):**
- Stores task state
- Provides CRUD operations for tasks
- Generates analytics reports
- Manages execution history
- Provides health metrics
- **Problem:** State management mixed with analytics and reporting

**ExecutionEngine (execution_engine.py):**
- Drives task execution
- Validates task completion
- Collects evidence
- Analyzes stagnation
- Simulates parallel execution
- Generates analytics reports
- **Problem:** Execution logic mixed with validation, analytics, and simulation

#### 2. **Tight Coupling and Circular Dependencies**

```
BaseAgent
    ↓ creates
TaskManager ←→ ExecutionEngine
    ↓ uses       ↑ back-reference
TaskValidator ←┘

Problem: Circular references and bidirectional dependencies
```

- ExecutionEngine holds reference to TaskManager
- TaskManager holds reference back to ExecutionEngine (line 33 in execution_engine.py)
- BaseAgent coordinates both but they reach into each other's state
- Makes testing extremely difficult

#### 3. **Code Duplication (DRY Violations)**

**Tool Result Parsing:**
- `core/parser.py:parse_tool_result()` - standardized parsing
- `core/utilities.py:execute_tool_safe()` - duplicates error handling
- `tasks/validator.py:_analyze_tool_success()` - re-parses results
- `tasks/execution_engine.py:_is_error_result()` - yet another parser
- **Impact:** 4 different places parsing tool results with slightly different logic

**Evidence Collection:**
- `execution_engine.py:collect_evidence_from_tool_result()` (lines 684-745)
- `execution_engine.py:update_task_from_tool_result()` (lines 335-436)
- Both analyze tool results and extract evidence, overlap ~60%

**Task Status Updates:**
- `manager.py:update_main_task_status()` (lines 62-88)
- `manager.py:update_task_status()` (lines 312-399)
- Both update task status, add history, save state - duplicate flows

**Observation Analysis:**
- `validator.py:_analyze_observations_for_success()` (lines 483-521)
- `validator.py:_observation_analysis_validator()` (lines 313-348)
- Similar pattern matching for success/error indicators

**Stagnation Detection:**
- `agent.py:_stuck_count` tracking (lines 80-83)
- `utilities.py:update_stagnation()` (lines 344-356)
- `execution_engine.py:check_for_stagnation()` (lines 886-924)
- Three different places managing stagnation with overlapping logic

#### 4. **Over-Engineering (YAGNI Violations)**

**TaskValidator System:**
- 593 lines of complex validation logic
- Multiple confidence thresholds and scoring algorithms
- Pattern matching with 20+ success/error indicators
- **Reality Check:** Could be replaced with 2-3 simple rules:
  1. Task has evidence items
  2. Evidence doesn't contain error markers
  3. Tool results indicate success
- **Wasted Effort:** ~70% of validator logic is unused complexity

**Plan Analytics & Reporting:**
- `execution_engine.py:create_plan_analytics_report()` (lines 985-1067) - 83 lines
- `execution_engine.py:simulate_parallel_execution()` (lines 946-983) - 38 lines
- `manager.py:get_execution_analytics()` (lines 271-310) - 40 lines
- `manager.py:get_plan_health_status()` (lines 693-739) - 47 lines
- **Total:** 208 lines of analytics that aren't core functionality
- **Used Where?** Nowhere in production execution - only saved to output files
- **Impact:** Adds complexity without providing runtime value

**Tool Routing Audit System:**
- `execution_engine.py:record_tool_routing()` - tracks relevance decisions
- `manager.py:record_tool_routing()` - stores routing events
- **Purpose:** Debugging tool relevance matching
- **Reality:** Never queried or analyzed in practice
- **Solution:** Remove or move to debug-only code path

**Evidence-Based Validation:**
- `validator.py:_check_evidence_accumulation()` - checks if enough evidence
- `validator.py:validate_tool_result_for_completion()` - validates tool results
- `execution_engine.py:collect_evidence_from_tool_result()` - collects evidence
- **Complexity:** 3 systems tracking evidence collection, completion, validation
- **Reality:** Simple success/failure from tool result is sufficient

#### 5. **Unclear Boundaries and Abstraction Leaks**

**Agent reaches into TaskManager internals:**
```python
# agent.py line 486 - reaches into execution_engine to get task_context
task_context = self.execution_engine.get_current_task_context()

# agent.py line 1093 - reaches into task_manager to get progress
progress_summary = self.task_manager.get_task_progress_summary()
```

**ExecutionEngine reaches into TaskManager:**
```python
# execution_engine.py line 362 - directly modifies manager state
self.task_manager.add_task_observation(active_task_id, observation)

# execution_engine.py line 192 - directly modifies task status
self.task_manager.update_subtask_status(...)
```

**TaskManager reaches back into ExecutionEngine:**
```python
# manager.py line 354-365 - reaches back to trigger advancement
if self.execution_engine and self.execution_engine.plan_loaded:
    success, message = self.execution_engine.advance_task_progression()
```

**Problem:** No clear interface boundaries. Components directly manipulate each other's state instead of going through well-defined APIs.

#### 6. **Complex Nested Conditionals**

**Agent.py ReAct Loop (lines 476-1077):**
- 10+ levels of nesting in main loop
- Multiple early exits and continues
- Duplicate prompt injection at 3+ different points
- Hard to follow execution flow

**Example - Plan Context Injection:**
```python
# agent.py lines 500-526 - plan injection
if (self.execution_engine.plan_loaded and i > 1 and i % 3 == 0):
    task_context = self.execution_engine.get_current_task_context()
    if task_context.get("status") == "executing":
        completion_analysis = self.execution_engine.get_intelligent_completion_analysis()
        plan_prompt = (...)
        if completion_analysis.get('main_task_analysis'):
            confidence = completion_analysis['main_task_analysis']['confidence']
            plan_prompt += f"\nTask Completion Confidence: {confidence:.1%}"
        # ... more nesting ...
```

**Duplicate Pattern:**
- Similar logic appears at lines 728-736, 861-868, 912-919
- Each handles "plan loaded this iteration" differently
- Could be extracted to single method

---

## Principle Violations Summary

### KISS (Keep It Simple, Stupid)
- **TaskValidator**: 593 lines of complex validation when simple rules suffice
- **Plan Analytics**: 200+ lines of unused analytics generation
- **ReAct Loop**: 600+ line monster function with 10+ nesting levels
- **Impact:** Makes debugging difficult, increases cognitive load

### YAGNI (You Aren't Gonna Need It)
- **Parallel Execution Simulation**: 38 lines, never used in production
- **Health Metrics**: 47 lines of health scoring that doesn't affect execution
- **Tool Routing Audit**: Tracking system never queried
- **Impact:** ~15% of codebase is speculative features

### DRY (Don't Repeat Yourself)
- **Tool Result Parsing**: 4 different implementations
- **Evidence Collection**: 2 overlapping implementations
- **Task Status Updates**: Duplicate flows for main/subtasks
- **Stagnation Detection**: 3 different tracking mechanisms
- **Impact:** Bug fixes must be applied in multiple places

### Dependency Inversion
- **Direct State Manipulation**: Components directly modify each other's state
- **Circular References**: TaskManager ↔ ExecutionEngine
- **No Interfaces**: Tight coupling to concrete implementations
- **Impact:** Cannot test components in isolation

### Open/Closed Principle
- **Hardcoded Tool Registration**: Tools registered via direct function calls
- **Fixed Validation Rules**: Cannot extend validation without modifying core code
- **Monolithic Agent Loop**: Cannot customize execution flow without editing agent.py
- **Impact:** Extension requires modification of core classes

---

## Refactoring Strategy

### Phase 1: Extract and Simplify (Priority: High)

#### 1.1 Break Down BaseAgent (agent.py)

**Current: 1130 lines → Target: <500 lines**

**Extract to new files:**

```
base_agent/
├── agent.py (core orchestration only, ~300 lines)
├── execution/
│   ├── __init__.py
│   ├── react_loop.py (ReAct execution loop, ~250 lines)
│   ├── tool_executor.py (tool execution & dispatch, ~150 lines)
│   └── stagnation_detector.py (stagnation detection, ~80 lines)
└── prompting/
    ├── __init__.py
    ├── context_builder.py (build context for prompts, ~120 lines)
    └── plan_prompter.py (plan-driven prompts, ~100 lines)
```

**Responsibilities:**
- **agent.py**: Initialize components, coordinate high-level flow, expose run() API
- **react_loop.py**: Main iteration loop, message handling, stop conditions
- **tool_executor.py**: Tool dispatch, error handling, result parsing (use DRY parser)
- **stagnation_detector.py**: Track repeated actions, detect stagnation, suggest recovery
- **context_builder.py**: Build system rules, inject memories, manage token counting
- **plan_prompter.py**: Generate plan-driven prompts, inject task context

**Rationale:**
- Single Responsibility: Each file has one clear purpose
- Open/Closed: Can extend prompting without touching execution
- Testability: Each component testable in isolation

#### 1.2 Simplify TaskManager (manager.py)

**Current: 741 lines → Target: <300 lines**

**Split into:**

```
base_agent/tasks/
├── manager.py (core state management, ~200 lines)
├── analytics.py (analytics & reporting, ~150 lines)
└── models.py (unchanged, 69 lines)
```

**manager.py should ONLY:**
- Store and retrieve task state
- Update task/subtask status
- Add evidence/observations
- Save/load state from disk
- **Remove:** Analytics, health metrics, execution history analysis

**analytics.py provides:**
- `generate_progress_summary(plan: TodoList) -> Dict`
- `generate_execution_analytics(history: List[Dict]) -> Dict`
- `generate_health_status(plan: TodoList) -> Dict`
- **Move:** All analytics from manager.py lines 197-310, 667-739

**Rationale:**
- DRY: Remove duplicate task update flows
- Single Responsibility: State management vs analytics
- YAGNI: Analytics separate from core functionality

#### 1.3 Simplify ExecutionEngine (execution_engine.py)

**Current: 1116 lines → Target: <400 lines**

**Remove or extract:**

```
base_agent/tasks/
├── execution_engine.py (task execution only, ~300 lines)
├── completion_validator.py (simple validator, ~80 lines)
└── analytics.py (includes execution analytics, ~150 lines total)
```

**execution_engine.py should ONLY:**
- Load and track current task/subtask
- Advance task progression
- Update tasks based on tool results
- Check dependencies
- **Remove:** Analytics (lines 985-1116), stagnation checks, parallel simulation

**completion_validator.py (simplified):**
- Replace 593-line TaskValidator with simple rules:
  ```python
  def is_subtask_complete(subtask: SubTask) -> bool:
      has_evidence = len(subtask.completion_evidence) >= 1
      no_errors = not any('error' in str(e).lower() for e in subtask.completion_evidence)
      return has_evidence and no_errors and subtask.completed

  def is_main_task_complete(task: MainTask) -> bool:
      if task.subtasks:
          return all(is_subtask_complete(st) for st in task.subtasks)
      return task.status == TaskStatus.COMPLETED
  ```
- **Reduction:** 593 lines → ~80 lines (86% reduction)
- **Justification:** Complex confidence scoring and pattern matching adds minimal value

**Rationale:**
- KISS: Simple completion rules instead of complex validation
- YAGNI: Remove speculative analytics features
- DRY: Use shared tool result parser

#### 1.4 Consolidate Tool Result Parsing (DRY fix)

**Create single source of truth:**

```
base_agent/core/
└── result_parser.py (~150 lines)
```

**Provides:**
```python
class ToolResultParser:
    @staticmethod
    def parse(result: Any) -> Dict[str, Any]:
        """Parse to standard format: {success: bool, data: Any, error: str}"""

    @staticmethod
    def is_success(result: Any) -> bool:
        """Check if result indicates success"""

    @staticmethod
    def is_error(result: Any) -> bool:
        """Check if result indicates error"""

    @staticmethod
    def extract_data(result: Any) -> Any:
        """Extract data from successful result"""

    @staticmethod
    def extract_error(result: Any) -> str:
        """Extract error message from failed result"""
```

**Replace all instances:**
- Delete `validator.py:_analyze_tool_success()` (lines 367-386)
- Delete `validator.py:_result_has_error()` (lines 415-468)
- Delete `execution_engine.py:_is_error_result()` (lines 748-751)
- Simplify `utilities.py:execute_tool_safe()` to use ToolResultParser
- Update `parser.py:parse_tool_result()` to use ToolResultParser

**Reduction:** ~200 lines of duplicate code eliminated

---

### Phase 2: Decouple and Invert Dependencies (Priority: Medium)

#### 2.1 Define Clear Interfaces

**Create abstract interfaces:**

```
base_agent/interfaces/
├── __init__.py
├── task_store.py (TaskStore protocol)
├── task_executor.py (TaskExecutor protocol)
└── completion_checker.py (CompletionChecker protocol)
```

**Example - TaskStore Protocol:**
```python
from typing import Protocol, Optional
from ..tasks.models import TodoList, MainTask, SubTask, TaskStatus

class TaskStore(Protocol):
    """Interface for task state management."""

    def get_plan(self) -> Optional[TodoList]:
        """Get the current plan."""
        ...

    def update_task_status(self, task_id: int, status: TaskStatus, reason: str) -> bool:
        """Update main task status."""
        ...

    def update_subtask_status(self, task_id: int, subtask_id: str,
                             completed: bool, reason: str) -> bool:
        """Update subtask status."""
        ...

    def add_evidence(self, task_id: int, evidence: str,
                    subtask_id: Optional[str] = None) -> bool:
        """Add completion evidence."""
        ...
```

**Benefits:**
- Dependency Inversion: Depend on interfaces, not implementations
- Testability: Easy to create mock implementations
- Flexibility: Can swap implementations without changing dependents

#### 2.2 Break Circular Dependencies

**Current Problem:**
```
TaskManager ←→ ExecutionEngine (circular via back-reference)
```

**Solution: Event-Based Communication**

```
base_agent/events/
├── __init__.py
├── event_bus.py (central event bus)
└── task_events.py (task-related events)
```

**Pattern:**
```python
# ExecutionEngine emits events instead of calling TaskManager directly
event_bus.emit(TaskStatusChanged(task_id=1, new_status=TaskStatus.COMPLETED))

# TaskManager listens for events and updates state
@event_bus.on(TaskStatusChanged)
def handle_status_change(event):
    self.update_task_status(event.task_id, event.new_status)
```

**Impact:**
- No circular dependencies
- Components loosely coupled
- Easier to test and extend

#### 2.3 Introduce Dependency Injection

**Current: Components create their own dependencies**
```python
# agent.py
self.task_manager = TaskManager(verbose=verbose, output_dir=self.output_dir)
self.execution_engine = PlanExecutionEngine(
    task_manager=self.task_manager,  # Hard dependency
    event_manager=self.event_manager,
    verbose=self.verbose
)
```

**Refactored: Inject dependencies**
```python
# agent.py
def __init__(
    self,
    system_prompt: str,
    user_prompt: str,
    *,
    task_store: Optional[TaskStore] = None,
    task_executor: Optional[TaskExecutor] = None,
    completion_checker: Optional[CompletionChecker] = None,
    ...
):
    self.task_store = task_store or TaskManager(...)
    self.task_executor = task_executor or ExecutionEngine(...)
    self.completion_checker = completion_checker or SimpleValidator(...)
```

**Benefits:**
- Can inject mocks for testing
- Can swap implementations easily
- Dependencies explicit in constructor

---

### Phase 3: Remove Unused Features (Priority: Medium)

#### 3.1 Delete Unused Analytics

**Remove from execution_engine.py:**
- `simulate_parallel_execution()` (lines 946-983) - 38 lines
- `create_plan_analytics_report()` (lines 985-1067) - 83 lines
- `_generate_execution_recommendations()` (lines 1069-1116) - 48 lines
- **Total:** 169 lines removed

**Remove from manager.py:**
- `get_execution_analytics()` (lines 271-310) - 40 lines
- `get_plan_health_status()` (lines 693-739) - 47 lines
- **Total:** 87 lines removed

**Move to optional analytics module if needed:**
```
base_agent/tasks/
└── optional_analytics.py (if analytics ever needed, implement here)
```

**Impact:** ~256 lines removed, complexity reduced

#### 3.2 Simplify Tool Routing Audit

**Remove:**
- `execution_engine.py:record_tool_routing()` calls
- `manager.py:record_tool_routing()` method
- All tool routing tracking from execution history

**Alternative:** Add debug logging if needed
```python
if self.verbose and DEBUG_MODE:
    logger.debug(f"Tool {tool_name} relevance: {is_relevant}")
```

**Impact:** ~30 lines removed, execution history simpler

#### 3.3 Delete Over-Engineered Validation

**Remove from validator.py:**
- `_evidence_threshold_validator()` (lines 271-288)
- `_tool_prediction_validator()` (lines 290-311)
- `_observation_analysis_validator()` (lines 313-348)
- `get_completion_confidence()` (lines 535-592)
- All confidence threshold and scoring logic

**Replace with simple rules in completion_validator.py:**
```python
def validate_subtask_completion(subtask: SubTask, parent_task: MainTask) -> bool:
    """Simple validation: has evidence and no errors."""
    if not subtask.completion_evidence:
        return False

    # Check for error indicators
    for evidence in subtask.completion_evidence:
        if 'error' in evidence.lower() or 'failed' in evidence.lower():
            return False

    return subtask.completed

def validate_main_task_completion(task: MainTask) -> bool:
    """Main task complete when all subtasks done or status is COMPLETED."""
    if task.subtasks:
        return all(validate_subtask_completion(st, task) for st in task.subtasks)
    return task.status == TaskStatus.COMPLETED
```

**Impact:**
- 593 lines → ~80 lines (86% reduction)
- Much easier to understand and maintain
- Sufficient for actual needs

---

### Phase 4: Improve Structure & Organization (Priority: Low)

#### 4.1 Reorganize Directory Structure

**Current:**
```
base_agent/
├── agent.py (1130 lines - too large)
├── core/ (5 files, utilities mixed with parsing)
├── tasks/ (4 files, state + execution + validation mixed)
├── memory/ (2 files, good structure)
├── events/ (1 file, underutilized)
└── utils/ (1 file, path utilities)
```

**Proposed:**
```
base_agent/
├── agent.py (~300 lines - orchestration only)
│
├── core/
│   ├── __init__.py
│   ├── result_parser.py (unified result parsing)
│   └── logger.py (message logging)
│
├── execution/
│   ├── __init__.py
│   ├── react_loop.py (main execution loop)
│   ├── tool_executor.py (tool dispatch & execution)
│   └── stagnation_detector.py (stagnation detection)
│
├── prompting/
│   ├── __init__.py
│   ├── context_builder.py (context & memory injection)
│   └── plan_prompter.py (plan-driven prompts)
│
├── tasks/
│   ├── __init__.py
│   ├── models.py (Pydantic task models)
│   ├── manager.py (state management only, ~200 lines)
│   ├── executor.py (task execution, ~300 lines)
│   ├── validator.py (simple validation, ~80 lines)
│   └── analytics.py (optional analytics)
│
├── interfaces/
│   ├── __init__.py
│   ├── task_store.py
│   ├── task_executor.py
│   └── completion_checker.py
│
├── memory/
│   ├── __init__.py
│   ├── domain_memory.py
│   └── episodic_memory.py
│
├── events/
│   ├── __init__.py
│   ├── event_bus.py
│   ├── task_events.py
│   └── manager.py (current EventManager)
│
└── utils/
    ├── __init__.py
    ├── path_utils.py
    └── token_counter.py
```

**Benefits:**
- Clear separation of concerns
- Easy to find relevant code
- Logical grouping by functionality

#### 4.2 Standardize Tool Registration

**Current Issues:**
- `tool_registry.py` has 457 lines registering tools via lambdas
- Tools registered by calling `register_X_tools(agent)` functions
- Hard to discover available tools
- Hard to extend with custom tools

**Proposed: Decorator-Based Registration**

```python
# tool_lib/registry.py
class ToolRegistry:
    """Central registry for all agent tools."""

    _tools: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, name: str, description: str, parameters: Dict):
        """Decorator to register a tool."""
        def decorator(func):
            cls._tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                function=func
            )
            return func
        return decorator

    @classmethod
    def get_tools(cls, categories: List[str] = None) -> Dict[str, ToolDefinition]:
        """Get tools by category."""
        if not categories:
            return cls._tools
        return {
            name: tool for name, tool in cls._tools.items()
            if tool.category in categories
        }
```

**Usage:**
```python
# tool_lib/data_tools/stock_screener.py
from ..registry import ToolRegistry

@ToolRegistry.register(
    name="screen_stocks",
    description="Screen stocks based on criteria",
    parameters={...},
    category="data"
)
def screen_stocks(criteria: Dict) -> Dict:
    ...
```

**Benefits:**
- Self-documenting tool registration
- Easy to discover tools
- Can filter tools by category
- No need for separate registration functions

#### 4.3 Simplify Tool Library Structure

**Current:**
```
tool_lib/
├── base_tools/ (3 files)
├── data_tools/ (5 files, stock_screener.py is 848 lines!)
├── portfolio_tools/ (9 files)
├── risk_tools/ (6 files)
├── ticker_tools/ (3 files)
└── agent_specific_tools/ (4 files)
```

**Issues:**
- `stock_screener.py` is 848 lines (violates constraint)
- Unclear why some tools are "agent_specific" vs others
- No consistent pattern for tool organization

**Proposed Changes:**

1. **Split stock_screener.py:**
```
tool_lib/data_tools/
├── screener/
│   ├── __init__.py
│   ├── base_screener.py (~150 lines)
│   ├── fundamental_screener.py (~250 lines)
│   ├── technical_screener.py (~200 lines)
│   └── combined_screener.py (~150 lines)
└── ...
```

2. **Merge agent_specific_tools into core categories:**
- `agent_specific_tools/cio.py` → `portfolio_tools/construction.py`
- `agent_specific_tools/cro.py` → `risk_tools/analysis.py`
- `agent_specific_tools/industry.py` → `data_tools/industry_analysis.py`
- `agent_specific_tools/optimizer.py` → `portfolio_tools/optimization.py`

3. **Result:** Clearer organization, no special "agent_specific" category

---

## Implementation Roadmap

### Phase 1: Critical Size Reductions (Week 1)

**Day 1-2: Extract from agent.py**
- Create `execution/react_loop.py`
- Create `execution/tool_executor.py`
- Create `prompting/context_builder.py`
- Reduce agent.py from 1130 → ~400 lines

**Day 3-4: Simplify execution_engine.py**
- Remove analytics methods (lines 985-1116)
- Move to optional `tasks/analytics.py`
- Reduce from 1116 → ~400 lines

**Day 5: Simplify manager.py**
- Move analytics to `tasks/analytics.py`
- Remove duplicate update flows
- Reduce from 741 → ~250 lines

**Day 6-7: Consolidate validation**
- Create simple `tasks/validator.py` (~80 lines)
- Delete complex TaskValidator (593 lines)
- Create unified `core/result_parser.py`

### Phase 2: Decouple Dependencies (Week 2)

**Day 8-9: Define interfaces**
- Create `interfaces/` directory
- Define TaskStore, TaskExecutor, CompletionChecker protocols
- Update implementations to match interfaces

**Day 10-11: Break circular dependencies**
- Implement event-based communication
- Remove TaskManager → ExecutionEngine back-reference
- Test with dependency injection

**Day 12-14: Refactor agent initialization**
- Add dependency injection to BaseAgent
- Create builder pattern for agent construction
- Update domain-specific agents (CIO, CRO, etc.)

### Phase 3: Remove Unused Code (Week 3)

**Day 15: Delete analytics**
- Remove parallel execution simulation
- Remove health metrics
- Remove plan analytics report
- Create optional analytics module if needed

**Day 16: Simplify tool routing**
- Remove tool routing audit system
- Add debug logging where useful
- Clean up execution history

**Day 17-18: Reorganize directory structure**
- Move files to new structure
- Update all imports
- Run tests to verify

**Day 19-21: Tool library cleanup**
- Split stock_screener.py into modules
- Merge agent_specific_tools
- Implement decorator-based registration

### Phase 4: Testing & Documentation (Week 4)

**Day 22-24: Unit tests**
- Test each component in isolation
- Test interface implementations
- Test event-based communication

**Day 25-26: Integration tests**
- Test full agent execution
- Test task management flows
- Test tool execution

**Day 27-28: Documentation**
- Update CLAUDE.md with new structure
- Document interfaces and contracts
- Add architecture diagrams

---

## Metrics & Success Criteria

### Code Size Reduction

| Component | Before | After | Reduction |
|-----------|--------|-------|-----------|
| agent.py | 1130 | 300 | 73% |
| execution_engine.py | 1116 | 300 | 73% |
| manager.py | 741 | 200 | 73% |
| validator.py | 592 | 80 | 86% |
| utilities.py | 531 | 350 | 34% |
| **Total Framework** | ~11,800 | ~8,000 | 32% |

### Principle Adherence

| Principle | Before | After | Improvement |
|-----------|--------|-------|-------------|
| KISS | 40% | 85% | +45% |
| YAGNI | 50% | 90% | +40% |
| DRY | 45% | 85% | +40% |
| SRP | 35% | 80% | +45% |
| DIP | 20% | 75% | +55% |

### File Size Compliance

| Status | Before | After |
|--------|--------|-------|
| Files over 500 lines | 8 | 0 |
| Files over 400 lines | 12 | 3 |
| Largest file | 1130 | 400 |
| Compliance rate | 85% | 100% |

### Code Quality Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| Cyclomatic Complexity (avg) | 12 | 6 | <10 |
| Max Nesting Depth | 10 | 4 | <5 |
| Duplicate Code % | 15% | 3% | <5% |
| Test Coverage | 40% | 75% | >70% |
| Module Coupling | High | Low | Low |

---

## Risk Assessment & Mitigation

### High Risk: Breaking Changes

**Risk:** Refactoring core execution logic could break existing agents

**Mitigation:**
1. Create comprehensive test suite before refactoring
2. Use feature flags to gradually migrate to new code
3. Keep old code path available during transition
4. Test with all domain-specific agents (CIO, CRO, Industry, Optimizer)

### Medium Risk: Performance Degradation

**Risk:** Event-based communication could add overhead

**Mitigation:**
1. Benchmark current performance baseline
2. Profile event bus implementation
3. Use synchronous events (no async overhead)
4. Compare performance metrics before/after

### Medium Risk: Interface Instability

**Risk:** Protocol definitions might need iteration

**Mitigation:**
1. Start with minimal interface definitions
2. Iterate based on actual usage
3. Use Protocol (structural typing) for flexibility
4. Document breaking changes clearly

### Low Risk: Lost Functionality

**Risk:** Removing analytics might be needed later

**Mitigation:**
1. Move analytics to optional module (don't delete)
2. Document what was removed and why
3. Keep as reference if needed in future
4. Can be re-added if use case emerges

---

## Specific Code Examples

### Example 1: Simplified Validation

**Before (validator.py - 593 lines):**
```python
class TaskValidator:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.validators: Dict[str, Callable] = {}
        self._confidence_thresholds = {
            'subtask_completion': 0.7,
            'main_task_completion': 0.8,
            'tool_result_success': 0.6
        }
        self._register_default_validators()

    def validate_subtask_completion(
        self, subtask: SubTask, parent_task: MainTask = None
    ) -> Tuple[bool, float, str]:
        validation_results = []

        # Check evidence count
        evidence_count = len(subtask.completion_evidence)
        if evidence_count >= 2:
            confidence = min(evidence_count / 3.0, 1.0)
            validation_results.append((True, confidence, f"Has {evidence_count} pieces of evidence"))
        # ... 60 more lines of complex validation logic
```

**After (completion_validator.py - ~80 lines):**
```python
class CompletionValidator:
    """Simple rule-based validation for task completion."""

    @staticmethod
    def is_subtask_complete(subtask: SubTask) -> bool:
        """Check if subtask is complete using simple rules."""
        # Rule 1: Must have evidence
        if not subtask.completion_evidence:
            return False

        # Rule 2: Evidence shouldn't contain errors
        for evidence in subtask.completion_evidence:
            evidence_lower = evidence.lower()
            if 'error' in evidence_lower or 'failed' in evidence_lower:
                return False

        # Rule 3: Marked as completed
        return subtask.completed

    @staticmethod
    def is_main_task_complete(task: MainTask) -> bool:
        """Check if main task is complete."""
        if task.subtasks:
            return all(CompletionValidator.is_subtask_complete(st)
                      for st in task.subtasks)
        return task.status == TaskStatus.COMPLETED
```

**Benefits:**
- 593 lines → 80 lines (86% reduction)
- Clear, understandable rules
- No complex confidence scoring
- Sufficient for actual needs

### Example 2: Unified Result Parsing

**Before: 4 different implementations**

```python
# core/parser.py
def parse_tool_result(result: Any, verbose: bool = False) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    # ... parsing logic

# core/utilities.py
def execute_tool_safe(self, name: str, args: Dict) -> Any:
    try:
        result = func(**args)
        return result
    except Exception as e:
        return yaml.dump({"success": False, "error": str(e)})

# tasks/validator.py
def _analyze_tool_success(self, tool_name: str, tool_result: Any):
    if isinstance(tool_result, Exception):
        return False, 0.0, f"Tool {tool_name} raised exception"
    # ... duplicate parsing logic

# tasks/execution_engine.py
def _is_error_result(self, result: Any) -> bool:
    parsed = parse_tool_result(result, verbose=False)
    return parsed.get('success') is False
```

**After: Single source of truth**

```python
# core/result_parser.py
from typing import Any, Dict, Optional, Tuple
import yaml

class ToolResultParser:
    """Unified parser for all tool results."""

    @staticmethod
    def parse(result: Any) -> Dict[str, Any]:
        """
        Parse tool result to standard format.

        Returns:
            {
                "success": bool,
                "data": Any (if success),
                "error": str (if failure)
            }
        """
        # Handle YAML string results
        if isinstance(result, str):
            try:
                parsed = yaml.safe_load(result)
                if isinstance(parsed, dict):
                    return parsed
            except:
                pass

        # Handle dict results
        if isinstance(result, dict):
            if 'success' in result:
                return result
            # Infer success from presence of error
            if 'error' in result:
                return {"success": False, "error": result['error']}
            # Assume success if dict with data
            return {"success": True, "data": result}

        # Handle exceptions
        if isinstance(result, Exception):
            return {"success": False, "error": str(result)}

        # Handle None
        if result is None:
            return {"success": False, "error": "Tool returned None"}

        # Default: assume success with data
        return {"success": True, "data": result}

    @staticmethod
    def is_success(result: Any) -> bool:
        """Check if result indicates success."""
        parsed = ToolResultParser.parse(result)
        return parsed.get("success", False)

    @staticmethod
    def is_error(result: Any) -> bool:
        """Check if result indicates error."""
        return not ToolResultParser.is_success(result)

    @staticmethod
    def get_data(result: Any) -> Any:
        """Extract data from successful result."""
        parsed = ToolResultParser.parse(result)
        return parsed.get("data")

    @staticmethod
    def get_error(result: Any) -> Optional[str]:
        """Extract error message from failed result."""
        parsed = ToolResultParser.parse(result)
        return parsed.get("error")
```

**Usage everywhere:**
```python
# execution/tool_executor.py
from ..core.result_parser import ToolResultParser

result = tool_function(**args)
if ToolResultParser.is_error(result):
    error_msg = ToolResultParser.get_error(result)
    # handle error
else:
    data = ToolResultParser.get_data(result)
    # process data
```

**Benefits:**
- Single implementation (DRY)
- Consistent behavior everywhere
- Easy to test
- Clear API

### Example 3: Event-Based Decoupling

**Before: Circular dependency**
```python
# tasks/manager.py
class TaskManager:
    def __init__(self, ...):
        self.execution_engine = None  # Will be set by ExecutionEngine

    def update_task_status(self, task_id: str, status: str, ...):
        # ... update state

        # Reach back into ExecutionEngine to trigger advancement
        if (self.execution_engine and
            self.execution_engine.plan_loaded and
            status == 'completed'):
            success, message = self.execution_engine.advance_task_progression()

# tasks/execution_engine.py
class PlanExecutionEngine:
    def __init__(self, task_manager: TaskManager, ...):
        self.task_manager = task_manager
        # Create circular reference
        self.task_manager.execution_engine = self

    def update_task_from_tool_result(self, tool_name: str, result: Any):
        # Directly modify TaskManager state
        self.task_manager.add_task_observation(task_id, observation)
        self.task_manager.add_task_evidence(task_id, evidence)
```

**After: Event-based communication**
```python
# events/task_events.py
from dataclasses import dataclass
from ..tasks.models import TaskStatus

@dataclass
class TaskStatusChanged:
    task_id: int
    new_status: TaskStatus
    reason: str

@dataclass
class TaskEvidenceAdded:
    task_id: int
    subtask_id: Optional[str]
    evidence: str

@dataclass
class ToolExecuted:
    task_id: int
    subtask_id: Optional[str]
    tool_name: str
    result: Any

# tasks/manager.py
class TaskManager:
    def __init__(self, event_bus: EventBus, ...):
        self.event_bus = event_bus
        self._register_handlers()

    def _register_handlers(self):
        self.event_bus.on(TaskStatusChanged, self._handle_status_change)
        self.event_bus.on(TaskEvidenceAdded, self._handle_evidence_added)

    def _handle_status_change(self, event: TaskStatusChanged):
        # Update state only
        task = self.get_task(event.task_id)
        task.status = event.new_status
        self.save_state()

    def _handle_evidence_added(self, event: TaskEvidenceAdded):
        # Add evidence only
        task = self.get_task(event.task_id)
        if event.subtask_id:
            subtask = task.get_subtask(event.subtask_id)
            subtask.completion_evidence.append(event.evidence)
        else:
            task.completion_evidence.append(event.evidence)
        self.save_state()

# tasks/executor.py
class TaskExecutor:
    def __init__(self, event_bus: EventBus, task_store: TaskStore, ...):
        self.event_bus = event_bus
        self.task_store = task_store
        self._register_handlers()

    def _register_handlers(self):
        self.event_bus.on(ToolExecuted, self._handle_tool_executed)

    def _handle_tool_executed(self, event: ToolExecuted):
        # Update execution state and emit new events
        evidence = self._collect_evidence(event.tool_name, event.result)

        self.event_bus.emit(TaskEvidenceAdded(
            task_id=event.task_id,
            subtask_id=event.subtask_id,
            evidence=evidence
        ))

        # Check if task should be advanced
        if self._should_advance():
            self.advance_task_progression()
```

**Benefits:**
- No circular dependencies
- Components loosely coupled
- Easy to add new handlers
- Clear separation of concerns
- Testable in isolation

---

## Appendix: Detailed File Analysis

### A. agent.py Line-by-Line Breakdown

**Lines 1-145: Initialization (145 lines)**
- Imports and setup (24 lines) ✅
- Constructor (99 lines) - **REFACTOR: Split into builder pattern**
- Helper initialization methods (22 lines) ✅

**Lines 146-410: Utility Methods (264 lines)**
- Domain memory initialization (5 lines) ✅
- Tool access (12 lines) ✅
- Event handler registration (21 lines) ✅
- Tool addition (11 lines) ✅
- Enhanced task prompting (70 lines) - **EXTRACT: → prompting/plan_prompter.py**
- Task failure checking (37 lines) - **EXTRACT: → execution/stagnation_detector.py**
- Plan completion checking (25 lines) - **EXTRACT: → tasks/executor.py**
- Task advancement checking (37 lines) - **EXTRACT: → tasks/executor.py**
- Argument parser creation (7 lines) ✅
- Token counting (13 lines) - **EXTRACT: → core/token_counter.py**

**Lines 412-1077: Main Run Loop (665 lines) - REFACTOR PRIORITY**
- Setup (50 lines) ✅
- Loop initialization (9 lines) ✅
- **Main iteration loop (606 lines) - EXTRACT: → execution/react_loop.py**
  - Task context display (20 lines)
  - Plan context injection (26 lines) - Duplicate pattern appears 3x
  - Memory refresh injection (17 lines)
  - Token counting (14 lines)
  - Model call (7 lines) ✅
  - Tool execution handling (136 lines) - **EXTRACT: → execution/tool_executor.py**
  - Plan loading handling (45 lines)
  - Task advancement (20 lines)
  - Observation tracking (10 lines)
  - Message appending (15 lines)
  - Content-based tool calls (150 lines) - Complex nested logic
  - Final answer checking (40 lines)
  - Stagnation detection (82 lines) - **EXTRACT: → execution/stagnation_detector.py**

**Lines 1078-1131: Cleanup & Return (53 lines)**
- Final answer extraction (12 lines) ✅
- Plan summary display (12 lines) ✅
- Result assembly (29 lines) - **SIMPLIFY: Remove excessive analytics**

### B. execution_engine.py Line-by-Line Breakdown

**Lines 1-108: Initialization & Loading (108 lines)** ✅

**Lines 109-166: Current Task Access (58 lines)** ✅

**Lines 168-334: Task Advancement (167 lines)**
- Main advancement logic (100 lines) ✅
- Next main task advancement (96 lines)
- **ISSUE:** Overly complex dependency checking

**Lines 335-436: Tool Result Updates (102 lines)**
- **REFACTOR:** Duplicate evidence collection logic
- **REFACTOR:** Use ToolResultParser instead of custom parsing

**Lines 438-515: Completion Checking (78 lines)**
- Auto-advance logic (39 lines)
- Completion conditions (37 lines)
- **SIMPLIFY:** Use simple validator instead of complex logic

**Lines 517-592: Dependency Management (76 lines)** ✅

**Lines 594-682: Execution Summary (89 lines)**
- Summary generation (28 lines) ✅
- Completion analysis (58 lines) - **REFACTOR:** Duplicate validation logic

**Lines 684-809: Evidence Collection (126 lines)**
- Evidence extraction (62 lines) - **SIMPLIFY:** Reduce pattern matching
- Helper methods (64 lines) - **EXTRACT: → core/result_parser.py**

**Lines 810-924: Advanced Features (115 lines)**
- Failure handling (73 lines) ✅
- Stagnation checking (39 lines) - **EXTRACT: → execution/stagnation_detector.py**

**Lines 926-1116: Analytics (191 lines) - DELETE OR MOVE**
- Parallel execution simulation (38 lines) - **DELETE: YAGNI violation**
- Analytics report (83 lines) - **MOVE: → tasks/analytics.py**
- Recommendations (48 lines) - **DELETE: YAGNI violation**

---

## Conclusion

This refactoring plan provides a systematic approach to cleaning up the agentic framework while preserving functionality. The key principles are:

1. **KISS**: Simplify validation, remove over-engineering
2. **YAGNI**: Delete speculative analytics and simulation features
3. **DRY**: Consolidate duplicate parsing and validation logic
4. **SRP**: Split large files into focused components
5. **DIP**: Introduce interfaces and dependency injection

**Expected Outcomes:**
- 32% reduction in total code
- 100% file size compliance
- Significantly improved maintainability
- Better testability
- Easier extensibility

**Implementation Timeline:** 4 weeks with proper testing

**Next Steps:**
1. Review and approve this plan
2. Create feature branch for refactoring
3. Begin Phase 1 (critical size reductions)
4. Test thoroughly at each stage
5. Merge incrementally to reduce risk

---

**Document Version:** 1.0
**Last Updated:** 2025-10-14
**Author:** Claude (Sonnet 4.5)
**Review Status:** Pending
