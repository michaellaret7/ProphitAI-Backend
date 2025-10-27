# Base Agent Reasoning Enhancement Implementation Plan

**Target:** Transform base_agent from task executor → intelligent analyst
**Approach:** Incremental in-place improvements with validation at each stage
**Timeline:** 2-3 weeks (4 phases)
**Success Metric:** 56% task mgmt overhead → 20%, enable deep reasoning

---

## Executive Summary

This plan implements the findings from [agent_reasoning_analysis.md](agent_reasoning_analysis.md) by systematically improving the base_agent folder through **incremental, testable changes**. We will NOT create a new base_agent_v3—instead, we evolve the existing architecture.

**Core Philosophy:**
> **Reduce overhead, enable reasoning, maintain reliability**

**Key Targets:**
- Tool call distribution: 56% → 20% task management
- Context utilization: 40% → 75% high-signal tokens
- Execution pattern: Deterministic → Adaptive with continuous reasoning

---

## Guiding Principles

### 1. Incremental Changes with Validation
- Make one change at a time
- Test after each change
- Maintain rollback capability
- Never break existing functionality

### 2. Backward Compatibility
- Keep old tools available initially (mark deprecated)
- Provide migration period
- Test with existing agents (OptimizerAgent)

### 3. Low-Risk First, High-Impact Priority
- Start with easy wins (prompt changes, frequency adjustments)
- Build up to complex changes (plan modification, adaptive execution)
- Each phase should improve agent without requiring subsequent phases

### 4. Continuous Testing
- Use OptimizerAgent as benchmark
- Compare metrics: tool call ratio, iteration count, reasoning depth
- Validate portfolio output quality remains high
- Monitor for regressions

---

## Phase 1: Reduce Overhead (Week 1: Days 1-3)

**Goal:** Free up cognitive capacity by reducing task management overhead
**Target:** 56% → 35% task management overhead
**Risk Level:** Low
**Expected Effort:** 2-3 days

### Change 1.1: Modify PlanningTool Prompt (Priority: CRITICAL)

**Why First?**
- Zero code changes, just prompt engineering
- Enables all subsequent reasoning enhancements
- Immediate impact on plan quality
- No dependencies

**File:** `app/core/agentic_framework/tool_lib/base_tools/planning_tool.py`

**Current Problem (Lines 130-134):**
```python
"✗ No thinking-only items (e.g., 'Brainstorm', 'Consider', 'Reflect').\n"
```

**Changes:**

1. **Remove prohibition on thinking subtasks** (Line ~133):
```python
# REMOVE THIS LINE:
"✗ No thinking-only items (e.g., 'Brainstorm', 'Consider', 'Reflect').\n"

# REPLACE WITH:
"✓ Include synthesis subtasks for complex analysis:\n"
"  - 'Synthesize metrics and formulate strategy'\n"
"  - 'Analyze trade-offs and select approach'\n"
"  - 'Review results and adjust strategy if needed'\n"
"✓ Thinking subtasks are valuable—they create space for reasoning.\n"
```

2. **Add guidance for right-sizing subtask count** (Line ~120):
```python
# ADD AFTER "PLANNING GUIDANCE:" section:
"SUBTASK GRANULARITY:\n"
"- Simple tasks: 0-2 subtasks (or no subtasks if steps are obvious)\n"
"- Moderate tasks: 2-4 subtasks\n"
"- Complex tasks: 3-6 subtasks maximum\n"
"- AVOID: Breaking every tool call into a separate subtask\n"
"- PREFER: Grouping related actions (e.g., 'Run and analyze core metrics' vs. 'Run metric 1', 'Run metric 2', ...)\n\n"
```

3. **Strengthen examples to show consolidated subtasks** (Line ~141):
```python
# MODIFY the "Request: 'Analyze energy sector and build portfolio' → Moderate" example:

# CURRENT (Over-specified):
"Task 2: Analyze fundamentals (quality, valuation, growth)\n"
"  Subtask 2a: Compute ROIC/margins/FCF\n"
"  Subtask 2b: Compute valuation (P/E, EV/EBITDA)\n"

# CHANGE TO (Right-sized):
"Task 2: Analyze fundamentals and form investment thesis\n"
"  Subtask 2a: Compute and synthesize quality metrics (ROIC, margins, FCF)\n"
"  Subtask 2b: Assess valuation and compare to sector peers\n"
"  Subtask 2c: Form conviction ranking with supporting evidence\n"
```

**Testing:**
1. Run OptimizerAgent with modified planning prompt
2. Inspect generated plan structure
3. Expected: 8 main tasks, 15-18 subtasks (down from 30)
4. Expected: At least 1-2 "synthesis" or "analyze" subtasks included
5. Validate: Agent still completes optimization successfully

**Success Criteria:**
- ✅ Plan has ≤20 total subtasks
- ✅ At least 2 subtasks include words: "synthesize", "analyze", "form", "compare"
- ✅ No single task has >6 subtasks
- ✅ Agent completes task without errors

**Rollback:** Revert planning_tool.py to git HEAD

---

### Change 1.2: Reduce Context Injection Frequency (Priority: HIGH)

**Why Second?**
- Simple change (one line)
- Reduces context bloat immediately
- Low risk (agent won't forget task in 6 iterations)

**File:** `app/core/agentic_framework/base_agent/execution/agent_execution_loop.py`

**Current (Line 182):**
```python
# Inject plan status update every 3 iterations
if iteration > 1 and iteration % 3 == 0:
```

**Change to:**
```python
# Inject plan status update every 6 iterations
# Rationale: Reduce context bloat; agent doesn't forget task in 6 iterations
if iteration > 1 and iteration % 6 == 0:
```

**Additional Change (Line 190):**
Also reduce memory refresh interval default:

**File:** `app/core/agentic_framework/base_agent/agent.py` (Line 63)

**Current:**
```python
memory_refresh_interval: int = 6,
```

**Change to:**
```python
memory_refresh_interval: int = 10,  # Less frequent memory refresh to reduce overhead
```

**Testing:**
1. Run OptimizerAgent (84 iterations)
2. Count plan status injections in agent_messages.json
3. Expected: ~14 injections (down from 28)
4. Verify: Agent stays on task and doesn't get confused

**Success Criteria:**
- ✅ Plan status injections reduced by ~50%
- ✅ Message history smaller by ~500-800 tokens
- ✅ Agent completes task correctly

**Rollback:** Change back to `% 3` and `interval = 6`

---

### Change 1.3: Aggressive Evidence Pruning (Priority: HIGH)

**Why Third?**
- Reduces task_state.json bloat
- No impact on LLM reasoning (evidence is for debugging)
- Medium complexity but high value

**File:** `app/core/agentic_framework/base_agent/tasks/executor/tool_integration.py`

**Current Issue:** Every tool call generates 4 evidence entries (Lines ~50-120)

**Implementation:**

1. **Add evidence filtering logic** (Insert after imports):
```python
# Evidence logging configuration
ALWAYS_LOG_EVIDENCE = {
    'create_structured_plan',
    'mark_task_complete',
    'episodic_remember'
}

NEVER_LOG_EVIDENCE = {
    'update_task_status',
    'get_current_task_info',
    'get_completion_analysis'
}

def should_log_evidence(tool_name: str, result: Any) -> bool:
    """Determine if tool result warrants evidence logging.

    Philosophy: Only log evidence for significant events and insights,
    not routine status updates or simple successes.

    Args:
        tool_name: Name of executed tool
        result: Tool result

    Returns:
        True if evidence should be logged
    """
    # Always log these important events
    if tool_name in ALWAYS_LOG_EVIDENCE:
        return True

    # Never log routine task management
    if tool_name in NEVER_LOG_EVIDENCE:
        return False

    # For analytical tools, only log if result has substance
    if isinstance(result, dict):
        # Log if there's actual data (not just success=True)
        if 'data' in result or 'results' in result:
            return True
        # Log if there are warnings or errors
        if result.get('success') is False or 'error' in result or 'warning' in result:
            return True

    # Default: don't log
    return False
```

2. **Modify evidence collection** (Find `collect_evidence_from_tool_result`, Line ~80):

**Current:**
```python
def collect_evidence_from_tool_result(self, tool_name: str, result: Any) -> List[str]:
    """Collect evidence from tool execution result."""
    evidence = []

    evidence.append(f"Successfully executed tool '{tool_name}'")

    # Parse result
    parsed = parse_tool_result(result, verbose=False)

    if parsed.get('success'):
        evidence.append(f"Tool {tool_name} returned success=True")

    # ... more evidence collection ...

    return evidence
```

**Change to:**
```python
def collect_evidence_from_tool_result(self, tool_name: str, result: Any) -> List[str]:
    """Collect evidence from tool execution result.

    Only collects evidence for significant events to reduce overhead.
    """
    # Check if we should log evidence for this tool
    if not should_log_evidence(tool_name, result):
        return []  # Return empty list, no evidence

    evidence = []

    # Only add high-value evidence
    evidence.append(f"Executed '{tool_name}'")

    # Parse result
    parsed = parse_tool_result(result, verbose=False)

    # Log failure prominently
    if parsed.get('success') is False:
        evidence.append(f"⚠️ Tool {tool_name} FAILED: {parsed.get('error', 'Unknown error')}")
        return evidence

    # For successful analytical tools, log key insights only
    if 'data' in parsed:
        data = parsed['data']
        if isinstance(data, dict):
            evidence.append(f"Retrieved data with {len(data)} fields")
        elif isinstance(data, list):
            evidence.append(f"Retrieved {len(data)} items")

    return evidence
```

**Testing:**
1. Run OptimizerAgent
2. Inspect task_state.json size
3. Expected: ~70KB → ~15KB
4. Count evidence entries: ~148 → ~30
5. Verify: Critical evidence (failures, completions) still logged

**Success Criteria:**
- ✅ task_state.json size reduced by >70%
- ✅ Evidence entries reduced by >80%
- ✅ Plan creation and task completions still have evidence
- ✅ Tool failures prominently logged

**Rollback:** Revert tool_integration.py changes

---

### Change 1.4: Remove Redundant update_task_status Tool (Priority: MEDIUM)

**Why Fourth?**
- Highest individual impact (~25 fewer tool calls)
- But requires verifying auto-advancement works correctly
- Need to ensure agent can still manually complete tasks when needed

**Files to Modify:**
1. `app/core/agentic_framework/base_agent/tool_registry.py` (remove tool registration)
2. `app/core/agentic_framework/base_agent/execution/tool_call_handler.py` (verify auto-advancement)

**Implementation:**

1. **First, verify auto-advancement is working** (tool_call_handler.py, Lines 84-93):

Check this code exists and is active:
```python
# Check if current task should be completed and advance automatically
if self.agent.execution_engine.plan_loaded:
    should_complete, reason = self.agent.execution_engine.check_task_completion_conditions()
    if should_complete:
        self.agent.execution_engine.advancement.advance_task_progression()
```

✅ If this code is present and active, we can safely remove manual status updates

2. **Comment out update_task_status tool** (tool_registry.py):

Find where `update_task_status` is registered (likely in `register_task_management_tools`):

```python
# COMMENT OUT:
# agent.add_tool(
#     name="update_task_status",
#     description="...",
#     parameters={...},
#     function=update_task_status_impl
# )

# ADD COMMENT:
# NOTE: update_task_status removed in Phase 1.4 of reasoning enhancement
# System now auto-advances tasks via check_task_completion_conditions()
# Agent can still use mark_task_complete for explicit completion with summary
```

3. **Keep mark_task_complete** - This is still valuable for explicit task completion with summaries

**Testing Plan:**
1. Run OptimizerAgent with update_task_status commented out
2. Monitor verbose output for task advancement messages
3. Verify system auto-advances through subtasks
4. Check agent doesn't get stuck or confused
5. Inspect tool calls: Should see ~25 fewer calls

**Success Criteria:**
- ✅ Agent completes all tasks without calling update_task_status
- ✅ System auto-advances subtasks correctly
- ✅ Tool call count reduced by ~20-30
- ✅ Agent uses mark_task_complete appropriately

**Rollback Plan:**
- Uncomment update_task_status registration
- Agent will resume using it

**Risk Mitigation:**
If agent gets stuck without manual status updates:
1. Re-enable update_task_status
2. Investigate check_task_completion_conditions logic
3. May need to make completion detection more robust before removing

---

## Phase 1 Validation (End of Week 1)

**Comprehensive Testing:**
1. Run full OptimizerAgent test
2. Collect metrics:
   - Tool call distribution (expect: ~40% task mgmt, 60% analytical)
   - Total iterations (expect: similar or fewer)
   - Context window usage (expect: improved signal ratio)
   - Task_state.json size (expect: ~15KB)
   - Agent_messages.json line count (expect: reduced)
3. Qualitative assessment:
   - Does plan look more reasonable? (15-18 subtasks vs 30)
   - Does agent complete successfully?
   - Are outputs still high quality?

**Go/No-Go Decision:**
- ✅ If metrics improved and quality maintained → Proceed to Phase 2
- ⚠️ If quality degraded → Tune thresholds, iterate
- ❌ If major issues → Rollback problematic changes

---

## Phase 2: Enable Reasoning (Week 1-2: Days 4-7)

**Goal:** Give agent explicit tools and prompts for reasoning
**Target:** Enable synthesis, hypothesis formation, iterative thinking
**Risk Level:** Low-Medium (additive changes)
**Expected Effort:** 3-4 days

### Change 2.1: Add Reasoning-Focused Tools (Priority: CRITICAL)

**Why First?**
- Additive (doesn't break existing)
- High impact (enables new reasoning patterns)
- Low risk (agent can choose to use or not)

**File:** `app/core/agentic_framework/tool_lib/base_tools/reasoning_tools.py` (NEW FILE)

**Create new reasoning tools module:**

```python
"""Reasoning tools for metacognitive analysis and synthesis.

These tools don't call external APIs—they prompt the agent to think deeply
about data it has already gathered.
"""

from typing import List, Dict, Any


def synthesize_observations(
    observations: List[str],
    context: str,
    goal: str = "Identify key patterns and form actionable insights"
) -> Dict[str, Any]:
    """Analyze multiple observations together to form insights.

    This is a "reflection tool"—it doesn't fetch new data. Instead, it prompts
    you to synthesize information you've already gathered.

    Use this when:
    - You've run multiple analytical tools and need to connect the dots
    - You have conflicting data points to reconcile
    - You need to form a strategic decision from disparate evidence

    Args:
        observations: List of key observations to synthesize (2-10 items)
        context: What domain/problem these observations relate to
        goal: What you're trying to achieve with this synthesis

    Returns:
        Prompt guiding you to synthesize the observations

    Example:
        synthesize_observations(
            observations=[
                "Portfolio Sharpe ratio is 1.41 (good)",
                "Volatility is 23.6% (elevated)",
                "Correlation matrix shows 0.96 between QQQ-VUG",
                "Top 5 positions represent 53% of portfolio"
            ],
            context="Portfolio risk analysis",
            goal="Identify primary risk drivers and mitigation strategy"
        )
    """
    return {
        "instruction": "Synthesize the following observations",
        "context": context,
        "goal": goal,
        "observations": observations,
        "your_task": (
            "Based on these observations, provide:\n"
            "1. Key Insights: What are the 2-3 most important patterns or findings?\n"
            "2. Causal Relationships: How do these observations connect? What explains what?\n"
            "3. Strategic Implications: What do these findings mean for your goal?\n"
            "4. Recommended Next Steps: What actions or analyses follow from this synthesis?"
        ),
        "success": True
    }


def form_hypothesis(
    hypothesis: str,
    supporting_evidence: List[str],
    test_plan: str
) -> Dict[str, Any]:
    """Form a testable hypothesis and plan how to validate it.

    Use this when:
    - You have a theory about why something is happening
    - You want to test an approach before fully committing
    - You're in an iterative refinement phase

    Args:
        hypothesis: Your hypothesis statement (be specific)
        supporting_evidence: Evidence that led you to this hypothesis
        test_plan: How you'll test this hypothesis

    Returns:
        Confirmation that hypothesis is recorded and test plan is clear

    Example:
        form_hypothesis(
            hypothesis="Removing high-correlation tech stocks will reduce volatility without sacrificing Sharpe ratio",
            supporting_evidence=[
                "QQQ-VUG correlation 0.96 drives portfolio vol",
                "Non-tech defensive stocks have Sharpe >1.2",
                "Portfolio is overweight tech at 45%"
            ],
            test_plan="Build portfolio variant removing VUG, adding defensive stocks; compare metrics"
        )
    """
    return {
        "hypothesis_recorded": hypothesis,
        "supporting_evidence": supporting_evidence,
        "test_plan": test_plan,
        "next_action": "Execute your test plan and evaluate if hypothesis is validated",
        "reminder": (
            "After testing:\n"
            "1. Compare results to your prediction\n"
            "2. If validated: Proceed with confidence\n"
            "3. If rejected: Form a new hypothesis based on what you learned\n"
            "4. If partially validated: Refine hypothesis and test again"
        ),
        "success": True
    }


def reflect_on_strategy(
    current_approach: str,
    results_so_far: List[str],
    remaining_goals: List[str],
    challenges_encountered: List[str] = None
) -> Dict[str, Any]:
    """Reflect on your current strategy and decide if adjustment is needed.

    Use this when:
    - You're midway through a multi-step process
    - Results aren't matching expectations
    - You need to decide whether to persist or pivot

    Args:
        current_approach: Description of your current strategy
        results_so_far: What you've accomplished/learned
        remaining_goals: What you still need to achieve
        challenges_encountered: Any obstacles or unexpected findings

    Returns:
        Prompt guiding strategic reflection

    Example:
        reflect_on_strategy(
            current_approach="Removing tech stocks to reduce correlation",
            results_so_far=["Correlation reduced from 0.49 to 0.27", "But Sharpe dropped from 1.41 to 1.02"],
            remaining_goals=["Achieve Sharpe >1.3 while maintaining low correlation"],
            challenges_encountered=["Defensive replacements have lower returns than expected"]
        )
    """
    return {
        "reflection_prompt": "Evaluate your strategy",
        "current_approach": current_approach,
        "results_so_far": results_so_far,
        "remaining_goals": remaining_goals,
        "challenges": challenges_encountered or [],
        "your_task": (
            "Reflect on your progress and answer:\n"
            "1. Is this approach working? Are you making progress toward goals?\n"
            "2. What's working well? What patterns are emerging?\n"
            "3. What's not working? What obstacles exist?\n"
            "4. Should you persist with current approach, or pivot to a different strategy?\n"
            "5. If pivoting: What alternative approach would you try? Why?\n"
            "6. Next immediate action: What's the next step?"
        ),
        "success": True
    }


def compare_alternatives(
    alternatives: List[Dict[str, Any]],
    criteria: List[str],
    context: str
) -> Dict[str, Any]:
    """Compare multiple alternatives against evaluation criteria.

    Use this when:
    - You have multiple candidate solutions
    - Need to make a selection decision
    - Want to explicitly evaluate trade-offs

    Args:
        alternatives: List of alternatives, each with name and description
        criteria: List of criteria to evaluate against
        context: What decision you're making

    Returns:
        Structured comparison framework

    Example:
        compare_alternatives(
            alternatives=[
                {"name": "Portfolio A", "description": "High Sharpe (1.4) but high correlation (0.45)"},
                {"name": "Portfolio B", "description": "Lower Sharpe (1.1) but low correlation (0.25)"},
                {"name": "Portfolio C", "description": "Moderate Sharpe (1.25) and moderate correlation (0.32)"}
            ],
            criteria=["Sharpe ratio", "Correlation", "Sector diversification", "Constraint compliance"],
            context="Selecting optimized portfolio for final output"
        )
    """
    return {
        "decision_context": context,
        "alternatives": alternatives,
        "evaluation_criteria": criteria,
        "your_task": (
            "For each alternative, evaluate against each criterion:\n"
            "1. Score each alternative on each criterion (1-10 scale)\n"
            "2. Identify trade-offs: What does each alternative optimize? What does it sacrifice?\n"
            "3. Consider user constraints and goals\n"
            "4. Make a recommendation with clear justification\n"
            "5. Explain why you chose this alternative over others"
        ),
        "success": True
    }
```

**Register these tools:**

**File:** `app/core/agentic_framework/base_agent/tool_registry.py`

Add new function:
```python
def register_reasoning_tools(agent: 'BaseAgent') -> None:
    """Register metacognitive reasoning tools."""
    from app.core.agentic_framework.tool_lib.base_tools.reasoning_tools import (
        synthesize_observations,
        form_hypothesis,
        reflect_on_strategy,
        compare_alternatives
    )

    agent.add_tool(
        name="synthesize_observations",
        description=(
            "Analyze multiple observations together to identify patterns and form insights. "
            "Use this after gathering data from multiple tools to connect the dots and form strategy."
        ),
        parameters={
            "type": "object",
            "properties": {
                "observations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of 2-10 key observations to synthesize"
                },
                "context": {
                    "type": "string",
                    "description": "Domain/problem context (e.g., 'portfolio risk analysis')"
                },
                "goal": {
                    "type": "string",
                    "description": "What you want to achieve with this synthesis"
                }
            },
            "required": ["observations", "context"]
        },
        function=synthesize_observations
    )

    agent.add_tool(
        name="form_hypothesis",
        description=(
            "Form a testable hypothesis and plan validation. "
            "Use when you have a theory to test or in iterative refinement phases."
        ),
        parameters={
            "type": "object",
            "properties": {
                "hypothesis": {
                    "type": "string",
                    "description": "Your hypothesis statement (specific and testable)"
                },
                "supporting_evidence": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Evidence that led to this hypothesis"
                },
                "test_plan": {
                    "type": "string",
                    "description": "How you'll test this hypothesis"
                }
            },
            "required": ["hypothesis", "supporting_evidence", "test_plan"]
        },
        function=form_hypothesis
    )

    agent.add_tool(
        name="reflect_on_strategy",
        description=(
            "Reflect on current strategy and decide if adjustment is needed. "
            "Use midway through multi-step processes to evaluate progress."
        ),
        parameters={
            "type": "object",
            "properties": {
                "current_approach": {
                    "type": "string",
                    "description": "Your current strategy description"
                },
                "results_so_far": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What you've accomplished/learned"
                },
                "remaining_goals": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "What you still need to achieve"
                },
                "challenges_encountered": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Obstacles or unexpected findings"
                }
            },
            "required": ["current_approach", "results_so_far", "remaining_goals"]
        },
        function=reflect_on_strategy
    )

    agent.add_tool(
        name="compare_alternatives",
        description=(
            "Compare multiple alternatives against criteria to make selection. "
            "Use when you have multiple candidate solutions and need to pick the best."
        ),
        parameters={
            "type": "object",
            "properties": {
                "alternatives": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"}
                        }
                    },
                    "description": "List of alternatives with name and description"
                },
                "criteria": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Criteria to evaluate against"
                },
                "context": {
                    "type": "string",
                    "description": "What decision you're making"
                }
            },
            "required": ["alternatives", "criteria", "context"]
        },
        function=compare_alternatives
    )
```

**Call in agent.py** (Line ~148, after `register_base_tools`):
```python
register_base_tools(self)
register_reasoning_tools(self)  # Add this line
```

**Testing:**
1. Verify tools are registered (check agent.tools list)
2. Manually call each tool to verify functionality
3. Run OptimizerAgent—agent should be able to use these tools
4. Don't expect agent to use them immediately (need Phase 2.2 prompts to encourage use)

**Success Criteria:**
- ✅ All 4 reasoning tools registered
- ✅ Tools return appropriate prompts/guidance
- ✅ No errors during registration
- ✅ Tools appear in agent's tool list

---

### Change 2.2: Inject Reasoning Prompts at Key Phases (Priority: CRITICAL)

**Why Second?**
- Cues agent to actually USE the reasoning tools we just added
- High impact on execution quality
- Low risk (just adds prompts)

**File:** `app/core/agentic_framework/base_agent/prompting/context_builder.py`

**Implementation:**

1. **Add reasoning prompt builder method** (after existing methods):

```python
def build_reasoning_checkpoint(self, checkpoint_type: str, context: Dict[str, Any] = None) -> str:
    """Build phase-specific reasoning checkpoint prompts.

    These prompts explicitly cue the agent to engage reasoning circuits
    at critical decision points.

    Args:
        checkpoint_type: Type of checkpoint (post_analytics, post_screening, refinement, etc.)
        context: Additional context for the prompt

    Returns:
        Reasoning checkpoint prompt, or empty string if not applicable
    """
    context = context or {}

    checkpoints = {
        "post_analytics": (
            "\n\n💭 REASONING CHECKPOINT: Analysis Complete\n"
            "═══════════════════════════════════════════\n"
            "You've gathered extensive analytical data across multiple tools.\n\n"
            "BEFORE proceeding to next phase:\n"
            "1. Use 'synthesize_observations' to connect insights across all metrics\n"
            "2. Identify the 2-3 most critical issues or opportunities\n"
            "3. Form a hypothesis about optimal strategy (use 'form_hypothesis')\n"
            "4. Let your synthesis guide the next phase—don't just execute the next subtask mechanically\n\n"
            "Remember: The goal is INSIGHT, not just completing subtasks.\n"
            "═══════════════════════════════════════════"
        ),

        "post_screening": (
            "\n\n💭 REASONING CHECKPOINT: Candidate Selection\n"
            "═══════════════════════════════════════════\n"
            "You've run stock screens and have candidate replacements.\n\n"
            "BEFORE finalizing selections:\n"
            "1. Use 'compare_alternatives' to systematically evaluate candidates\n"
            "2. Don't just pick the first N results—think strategically:\n"
            "   - How do these fit with portfolio goals?\n"
            "   - What correlations do they have with existing holdings?\n"
            "   - Do they address the weaknesses you identified?\n"
            "3. Consider portfolio-level effects, not just individual ticker metrics\n"
            "4. Justify why these SPECIFIC tickers are optimal\n\n"
            "Quality over quantity—better to have high-conviction picks than fill a quota.\n"
            "═══════════════════════════════════════════"
        ),

        "refinement_start": (
            "\n\n💭 DEEP REFINEMENT MODE ACTIVATED\n"
            "═══════════════════════════════════════════\n"
            "You now enter the most critical phase: ITERATIVE REFINEMENT.\n\n"
            "You have UP TO 3 refinement attempts. Use them wisely:\n\n"
            "REFINEMENT CYCLE:\n"
            "1. ANALYZE: Why did metrics change? Don't just observe—EXPLAIN the cause\n"
            "2. HYPOTHESIZE: Use 'form_hypothesis' to predict what adjustment would improve metrics\n"
            "3. TEST: Make the adjustment and measure impact\n"
            "4. EVALUATE: Did hypothesis validate? If not, why? What did you learn?\n"
            "5. ITERATE: Form new hypothesis based on learnings, test again\n\n"
            "STOP CONDITIONS:\n"
            "- You've exhausted improvement ideas (genuinely tried multiple approaches)\n"
            "- You're seeing diminishing returns (changes aren't improving metrics)\n"
            "- You've used all 3 attempts\n\n"
            "AVOID:\n"
            "❌ Making 1 superficial change and accepting result\n"
            "❌ Not analyzing WHY changes had their effect\n"
            "❌ Giving up after first attempt\n\n"
            "Aim for GENUINE optimization through hypothesis-driven iteration.\n"
            "═══════════════════════════════════════════"
        ),

        "refinement_iteration": (
            "\n\n💭 REFINEMENT CHECKPOINT: Attempt {attempt_num}\n"
            "═══════════════════════════════════════════\n"
            "You've completed refinement attempt {attempt_num}.\n\n"
            "Use 'reflect_on_strategy' to evaluate:\n"
            "1. What changed? Why?\n"
            "2. Did your hypothesis validate?\n"
            "3. What did you LEARN from this iteration?\n"
            "4. Should you try a different approach? Or refine current approach?\n"
            "5. What's your hypothesis for next iteration?\n\n"
            "Attempts remaining: {attempts_remaining}\n"
            "═══════════════════════════════════════════"
        ).format(
            attempt_num=context.get('attempt_num', '?'),
            attempts_remaining=context.get('attempts_remaining', '?')
        ),

        "pre_construction": (
            "\n\n💭 REASONING CHECKPOINT: Portfolio Construction\n"
            "═══════════════════════════════════════════\n"
            "You're about to construct the new portfolio.\n\n"
            "Use 'synthesize_observations' to review:\n"
            "1. What are the key weaknesses you identified?\n"
            "2. What replacements did you select and WHY?\n"
            "3. How will the new portfolio address weaknesses?\n"
            "4. What trade-offs are you making?\n\n"
            "Construct the portfolio with clear intent, not just mechanical assembly.\n"
            "═══════════════════════════════════════════"
        )
    }

    return checkpoints.get(checkpoint_type, "")
```

2. **Add method to detect task completion for checkpoint injection:**

```python
def should_inject_checkpoint(self, iteration: int) -> Optional[str]:
    """Determine if a reasoning checkpoint should be injected.

    Checks task completion state to identify phase transitions.

    Args:
        iteration: Current iteration number

    Returns:
        Checkpoint type to inject, or None
    """
    if not self.agent.execution_engine.plan_loaded:
        return None

    # Get plan and current task
    plan = self.agent.execution_engine.task_store.get_current_structured_plan()
    if not plan:
        return None

    # Check for task transitions
    # This is heuristic-based; adjust task IDs based on actual plan structure

    current_task = self.agent.execution_engine.get_current_task()
    if not current_task:
        return None

    # Just completed analytics phase (tasks 3-4 typically)
    if current_task.id == 4 and current_task.status.value == "completed":
        return "post_analytics"

    # Just completed screening phase (task 5 typically)
    if current_task.id == 5 and current_task.status.value == "completed":
        return "post_screening"

    # Entering construction phase (task 6 typically)
    if current_task.id == 6 and current_task.status.value == "in_progress":
        # Check if this is first iteration of task 6
        if not current_task.observations:  # No observations yet = just started
            return "pre_construction"

    # Entering refinement phase (task 7 typically)
    if current_task.id == 7 and current_task.status.value == "in_progress":
        if not current_task.observations:  # Just started
            return "refinement_start"
        else:
            # Check iteration count for task 7
            # If we're N iterations into task 7, inject refinement_iteration
            # This is approximate; you may need to track this more precisely
            pass

    return None
```

3. **Integrate into execution loop:**

**File:** `app/core/agentic_framework/base_agent/execution/agent_execution_loop.py`

**Modify `_inject_periodic_context` method** (Lines 168-193):

```python
def _inject_periodic_context(self, messages: List[Dict], iteration: int) -> None:
    """Inject periodic plan context and memory refresh using ContextBuilder.

    ENHANCED: Also injects reasoning checkpoints at key phase transitions.
    """
    # Inject plan status update every 6 iterations (reduced from 3)
    if iteration > 1 and iteration % 6 == 0:
        plan_context = self.context_builder.build_plan_context(iteration)
        if plan_context:
            messages.append({"role": "user", "content": plan_context})

    # Inject memory refresh at configured interval
    memory_msg = self.context_builder.build_memory_refresh(
        iteration,
        self.agent.memory_refresh_interval
    )
    if memory_msg:
        messages.append({"role": "user", "content": memory_msg})

    # NEW: Inject reasoning checkpoints at phase transitions
    checkpoint_type = self.context_builder.should_inject_checkpoint(iteration)
    if checkpoint_type:
        checkpoint_msg = self.context_builder.build_reasoning_checkpoint(checkpoint_type)
        if checkpoint_msg:
            messages.append({"role": "user", "content": checkpoint_msg})
            if self.agent.verbose:
                print(f"  💭 Reasoning checkpoint injected: {checkpoint_type}")
```

**Testing:**
1. Run OptimizerAgent
2. Monitor verbose output for checkpoint injections
3. Inspect agent_messages.json for reasoning checkpoint prompts
4. Observe if agent uses reasoning tools (synthesize_observations, etc.)
5. Qualitative: Does agent show deeper reasoning after checkpoints?

**Success Criteria:**
- ✅ Checkpoints injected at appropriate phases (task 3→4, task 5, task 7 start)
- ✅ Agent uses at least 1-2 reasoning tools during run
- ✅ Reasoning depth improves (visible in message content)

---

### Change 2.3: Summarize Lengthy Tool Results (Priority: MEDIUM)

**Why Third?**
- Reduces message history bloat
- More complex to implement correctly
- Need to ensure summaries preserve key information

**File:** `app/core/agentic_framework/base_agent/core/utilities.py`

**Implementation:**

1. **Add result summarization logic:**

```python
def summarize_tool_result(self, tool_name: str, result: Any, max_chars: int = 2000) -> str:
    """Summarize lengthy tool results to reduce context bloat.

    Args:
        tool_name: Name of the tool that produced this result
        result: The result to summarize
        max_chars: Maximum characters for summary

    Returns:
        Summarized result string
    """
    result_str = self.stringify(result)

    # If result is short, return as-is
    if len(result_str) <= max_chars:
        return result_str

    # Parse structured result
    parsed = parse_tool_result(result, verbose=False)

    # Build summary based on tool type
    if tool_name == "calculate_portfolio_correlation_matrix":
        return self._summarize_correlation_matrix(parsed, max_chars)
    elif tool_name == "calculate_ticker_performances":
        return self._summarize_ticker_performances(parsed, max_chars)
    elif tool_name == "portfolio_stress_test":
        return self._summarize_stress_test(parsed, max_chars)
    elif tool_name == "stock_screener":
        return self._summarize_stock_screener(parsed, max_chars)
    else:
        # Generic summarization: truncate with summary stats
        return self._summarize_generic(result_str, parsed, max_chars)

def _summarize_correlation_matrix(self, parsed: Dict, max_chars: int) -> str:
    """Summarize correlation matrix output."""
    if 'data' not in parsed or 'correlations' not in parsed['data']:
        return str(parsed)

    correlations = parsed['data']['correlations']

    # Extract high correlations (>0.7)
    high_corr = [c for c in correlations if c['corr'] > 0.7]

    # Calculate average
    avg_corr = sum(c['corr'] for c in correlations) / len(correlations) if correlations else 0

    summary = (
        f"Correlation Matrix Analysis:\n"
        f"  - Total pairs: {len(correlations)}\n"
        f"  - Average correlation: {avg_corr:.3f}\n"
        f"  - High correlation pairs (>0.7): {len(high_corr)}\n"
    )

    if high_corr:
        summary += "  - Top correlated pairs:\n"
        for c in sorted(high_corr, key=lambda x: x['corr'], reverse=True)[:5]:
            summary += f"    • {c['pair']}: {c['corr']:.3f}\n"

    summary += "\n[Full correlation matrix available in trace]"

    return summary

def _summarize_ticker_performances(self, parsed: Dict, max_chars: int) -> str:
    """Summarize ticker performances output."""
    if 'data' not in parsed:
        return str(parsed)

    tickers = parsed['data']
    if not isinstance(tickers, list):
        return str(parsed)

    # Sort by Sharpe ratio
    sorted_tickers = sorted(tickers, key=lambda x: x.get('sharpe', 0), reverse=True)

    summary = (
        f"Ticker Performance Analysis ({len(tickers)} tickers):\n\n"
        f"Top Performers (by Sharpe):\n"
    )

    for t in sorted_tickers[:3]:
        summary += (
            f"  • {t.get('ticker', 'N/A')}: "
            f"Sharpe={t.get('sharpe', 0):.2f}, "
            f"Return={t.get('ann_total_return', 0):.1%}, "
            f"Vol={t.get('ann_volatility', 0):.1%}\n"
        )

    summary += "\nBottom Performers:\n"
    for t in sorted_tickers[-3:]:
        summary += (
            f"  • {t.get('ticker', 'N/A')}: "
            f"Sharpe={t.get('sharpe', 0):.2f}, "
            f"Return={t.get('ann_total_return', 0):.1%}\n"
        )

    summary += "\n[Full ticker details available in trace]"

    return summary

def _summarize_generic(self, result_str: str, parsed: Dict, max_chars: int) -> str:
    """Generic summarization for unknown tool types."""
    # Truncate with ellipsis
    if len(result_str) <= max_chars:
        return result_str

    truncated = result_str[:max_chars]

    # Add summary line
    summary = f"{truncated}...\n\n[Result truncated. Full output: {len(result_str)} chars]"

    return summary
```

2. **Integrate into tool call handler:**

**File:** `app/core/agentic_framework/base_agent/execution/tool_call_handler.py`

**Modify message appending** (Line ~104):

```python
# CURRENT:
observation_content = self.agent.utilities.stringify(observation)

# CHANGE TO:
# Summarize if result is lengthy
observation_content = self.agent.utilities.summarize_tool_result(name, observation, max_chars=2000)
```

**Testing:**
1. Run OptimizerAgent
2. Check message lengths in agent_messages.json
3. Verify correlation matrix is summarized (should be ~10 lines vs. 100)
4. Verify ticker performances summarized (top 3 + bottom 3 only)
5. Ensure agent still has enough information to reason

**Success Criteria:**
- ✅ Correlation matrix messages reduced from ~100 lines → ~10 lines
- ✅ Ticker performance messages show top/bottom performers only
- ✅ Agent successfully completes task with summarized data
- ✅ Total message history size reduced by ~30-40%

**Risk Mitigation:**
- Full results still available in trace for debugging
- Summaries preserve key information (high correlations, outliers)
- If agent struggles, can adjust max_chars or summarization logic

---

## Phase 2 Validation (End of Week 2)

**Comprehensive Testing:**
1. Run full OptimizerAgent test
2. Compare to Phase 1 baseline:
   - Tool call distribution (expect: ~25% task mgmt, 75% analytical)
   - Reasoning tool usage (expect: 3-8 calls to synthesis/hypothesis tools)
   - Message history quality (expect: higher signal-to-noise ratio)
   - Execution depth (qualitative: more synthesis, hypothesis testing)

**Qualitative Assessment:**
- Read through agent_messages.json
- Look for evidence of synthesis ("Based on these metrics...")
- Look for hypothesis formation ("I hypothesize that...")
- Look for strategic reflection ("Reviewing my approach...")

**Go/No-Go Decision:**
- ✅ If agent shows reasoning behaviors → Proceed to Phase 3
- ⚠️ If reasoning tools unused → Strengthen prompts, iterate
- ❌ If quality degraded → Investigate, tune

---

## Phase 3: Adaptive Execution (Week 2-3: Days 8-12)

**Goal:** Enable agent to modify plans dynamically based on data
**Target:** Transform from rigid deterministic → adaptive reasoning
**Risk Level:** Medium-High (complex changes)
**Expected Effort:** 4-5 days

### Change 3.1: Implement Plan Modification Tool (Priority: MEDIUM)

**Why First in Phase 3?**
- Enables true adaptability
- Complex but high-value
- Requires careful validation

**File:** `app/core/agentic_framework/tool_lib/base_tools/plan_modification_tool.py` (NEW)

**Implementation:**

```python
"""Tool for dynamically modifying execution plans."""

from typing import Dict, Any, Optional
from app.core.agentic_framework.base_agent.tasks.models import SubTask, TaskStatus


def modify_plan(
    modification_type: str,
    task_id: int,
    details: Dict[str, Any],
    reason: str
) -> Dict[str, Any]:
    """Modify the execution plan dynamically based on intermediate results.

    Use this when:
    - You discover you need an additional step not in the original plan
    - A planned step is no longer necessary
    - You need to adjust task ordering based on findings

    IMPORTANT: Use sparingly. Plan modifications should be justified by data,
    not used to avoid completing current tasks.

    Args:
        modification_type: Type of modification:
            - 'add_subtask': Add a new subtask to existing task
            - 'skip_subtask': Mark a subtask as no longer needed
            - 'adjust_task_priority': Suggest working on a different task first
        task_id: ID of task to modify
        details: Specific modification details (varies by type)
        reason: Clear justification for why this modification is needed

    Returns:
        Confirmation of plan modification

    Examples:
        # Add subtask when screener returns insufficient results
        modify_plan(
            modification_type='add_subtask',
            task_id=5,
            details={
                'subtask_id': '5d',
                'description': 'Re-run screener with relaxed constraints',
                'position': 'after_5c'
            },
            reason='Screener 3 returned 0 results; need to relax constraints and retry'
        )

        # Skip unnecessary subtask
        modify_plan(
            modification_type='skip_subtask',
            task_id=6,
            details={'subtask_id': '6e'},
            reason='Allocation normalization already handled in previous step'
        )
    """
    # This would integrate with PlanExecutor to actually modify the plan
    # For now, we return a structured response that agents can use

    result = {
        "modification_type": modification_type,
        "task_id": task_id,
        "details": details,
        "reason": reason,
        "status": "pending_approval",
        "message": None,
        "success": True
    }

    if modification_type == "add_subtask":
        result["message"] = (
            f"Plan modification requested: Add subtask '{details.get('description')}' to Task {task_id}.\n"
            f"Reason: {reason}\n\n"
            f"You may proceed with this new subtask. The system will track it as part of your plan.\n"
            f"Remember to mark it complete when finished."
        )

    elif modification_type == "skip_subtask":
        result["message"] = (
            f"Plan modification requested: Skip subtask {details.get('subtask_id')} in Task {task_id}.\n"
            f"Reason: {reason}\n\n"
            f"You may proceed to the next subtask. Skipped subtask will be marked as such."
        )

    elif modification_type == "adjust_task_priority":
        result["message"] = (
            f"Plan modification requested: Adjust task priority for Task {task_id}.\n"
            f"Reason: {reason}\n\n"
            f"Note: Current system executes tasks sequentially. "
            f"If you have a strong reason to work out of order, document it clearly."
        )

    else:
        result["success"] = False
        result["message"] = f"Unknown modification type: {modification_type}"

    return result
```

**Register the tool:**

Add to `tool_registry.py`:
```python
def register_adaptive_execution_tools(agent: 'BaseAgent') -> None:
    """Register tools for adaptive execution."""
    from app.core.agentic_framework.tool_lib.base_tools.plan_modification_tool import modify_plan

    agent.add_tool(
        name="modify_plan",
        description=(
            "Modify execution plan dynamically based on intermediate results. "
            "Use when you need to add steps, skip unnecessary steps, or adjust priorities. "
            "Requires clear justification."
        ),
        parameters={
            "type": "object",
            "properties": {
                "modification_type": {
                    "type": "string",
                    "enum": ["add_subtask", "skip_subtask", "adjust_task_priority"],
                    "description": "Type of modification to make"
                },
                "task_id": {
                    "type": "integer",
                    "description": "ID of task to modify"
                },
                "details": {
                    "type": "object",
                    "description": "Modification details (structure varies by type)"
                },
                "reason": {
                    "type": "string",
                    "description": "Clear justification for this modification"
                }
            },
            "required": ["modification_type", "task_id", "details", "reason"]
        },
        function=modify_plan
    )
```

Call in `agent.py`:
```python
register_reasoning_tools(self)
register_adaptive_execution_tools(self)  # Add this line
```

**Testing:**
1. Test tool registration
2. Manually invoke modify_plan to verify functionality
3. Run OptimizerAgent—observe if agent tries to modify plan
4. Initially, agent may not use this tool (need prompting/examples)

**Success Criteria:**
- ✅ Tool registered successfully
- ✅ Returns appropriate guidance for each modification type
- ✅ Agent can call tool without errors

**Note:** Full plan modification (actually altering PlanExecutor state) would require deeper integration. For Phase 3.1, we're providing the interface; agent can document modifications even if system doesn't automatically execute them.

---

### Change 3.2: Enhanced Refinement Prompts (Priority: HIGH)

**Why Second?**
- Addresses the most critical weakness (shallow refinement)
- Simpler than full plan modification
- High impact on output quality

**File:** `app/core/agentic_framework/base_agent/prompting/context_builder.py`

**Implementation:**

Already partially done in Change 2.2 with `refinement_start` checkpoint.

**Additional enhancement:**

Add refinement tracking to execution loop:

**File:** `app/core/agentic_framework/base_agent/execution/agent_execution_loop.py`

Add to class:
```python
def __init__(self, agent: 'BaseAgent'):
    # ... existing code ...

    # Track refinement iterations for enhanced prompting
    self.refinement_iteration_count = 0
    self.refinement_task_id = None  # Which task is the refinement task
```

In `_inject_periodic_context`:
```python
# NEW: Track refinement iterations and inject iteration-specific prompts
if self.agent.execution_engine.plan_loaded:
    current_task = self.agent.execution_engine.get_current_task()

    # Detect refinement task (heuristic: task with "refinement" in description or task ID 7)
    if current_task and (
        "refinement" in current_task.description.lower() or
        "refine" in current_task.description.lower() or
        current_task.id == 7  # Common refinement task ID
    ):
        if self.refinement_task_id != current_task.id:
            # Just entered refinement task
            self.refinement_task_id = current_task.id
            self.refinement_iteration_count = 0

        self.refinement_iteration_count += 1

        # Inject iteration-specific refinement checkpoint every 5 iterations within refinement
        if self.refinement_iteration_count % 5 == 0 and self.refinement_iteration_count > 0:
            attempt_num = self.refinement_iteration_count // 5
            refinement_checkpoint = self.context_builder.build_reasoning_checkpoint(
                "refinement_iteration",
                context={
                    "attempt_num": attempt_num,
                    "attempts_remaining": max(0, 3 - attempt_num)
                }
            )
            if refinement_checkpoint:
                messages.append({"role": "user", "content": refinement_checkpoint})
                if self.agent.verbose:
                    print(f"  🔄 Refinement checkpoint: Attempt {attempt_num}")
```

**Testing:**
1. Run OptimizerAgent
2. Observe refinement phase (Task 7)
3. Check for refinement checkpoint injections
4. Count refinement iterations: expect >1 attempt
5. Qualitative: Does agent show hypothesis testing, strategy adjustments?

**Success Criteria:**
- ✅ Refinement checkpoints injected (attempt 1, attempt 2, etc.)
- ✅ Agent makes multiple refinement attempts (>1)
- ✅ Agent uses reasoning tools during refinement (reflect_on_strategy, form_hypothesis)
- ✅ Final output shows iterative improvement

---

## Phase 3 Validation (End of Week 3)

**Comprehensive Testing:**
1. Run multiple OptimizerAgent tests
2. Compare to Phase 2 baseline:
   - Refinement attempts (expect: 2-3 vs. 1)
   - Plan modification usage (optional, may be zero)
   - Reasoning depth in refinement phase (qualitative)

**Qualitative Assessment:**
- Does agent iterate multiple times in refinement?
- Does agent form hypotheses and test them?
- Does agent show strategic thinking vs. mechanical execution?

**Success Indicators:**
- Agent makes 2-3 refinement attempts with distinct strategies
- Agent uses reflect_on_strategy between attempts
- Final portfolio quality improved (or maintained if already optimal)

---

## Phase 4: Validation & Tuning (Week 3: Days 13-15)

**Goal:** Validate improvements, tune parameters, document results
**Expected Effort:** 2-3 days

### Comprehensive Benchmark Suite

**Create benchmark script:** `tests/agent_reasoning_benchmark.py`

```python
"""Benchmark script to compare agent reasoning improvements."""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


def run_optimizer_benchmark(
    portfolio_id: str,
    output_dir: Path,
    run_name: str
) -> Dict:
    """Run single optimizer benchmark."""
    # Import and run agent
    from app.domain.portfolio_operations.optimizer.agent import OptimizerAgent

    agent = OptimizerAgent(
        portfolio_id=portfolio_id,
        # ... other params ...
    )

    result = agent.run()

    # Collect metrics
    metrics = {
        "run_name": run_name,
        "timestamp": datetime.now().isoformat(),
        "total_iterations": result["iterations"],
        "total_tokens": result["total_tokens"],
        "stop_reason": result["stop_reason"],
        # Tool call analysis
        "tool_calls": analyze_tool_calls(agent.output_dir),
        # Reasoning analysis
        "reasoning_depth": analyze_reasoning_depth(agent.output_dir),
        # Output quality
        "portfolio_quality": analyze_portfolio_quality(result),
    }

    return metrics


def analyze_tool_calls(output_dir: Path) -> Dict:
    """Analyze tool call distribution."""
    messages_file = output_dir / "agent_messages.json"
    with open(messages_file) as f:
        data = json.load(f)

    messages = data["messages"]

    # Count tool calls by category
    task_mgmt_tools = {
        'create_structured_plan', 'get_current_task_info',
        'update_task_status', 'mark_task_complete'
    }

    reasoning_tools = {
        'synthesize_observations', 'form_hypothesis',
        'reflect_on_strategy', 'compare_alternatives'
    }

    task_mgmt_count = 0
    reasoning_count = 0
    analytical_count = 0

    for msg in messages:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                tool_name = tc["function"]["name"]
                if tool_name in task_mgmt_tools:
                    task_mgmt_count += 1
                elif tool_name in reasoning_tools:
                    reasoning_count += 1
                else:
                    analytical_count += 1

    total = task_mgmt_count + reasoning_count + analytical_count

    return {
        "task_management": task_mgmt_count,
        "reasoning": reasoning_count,
        "analytical": analytical_count,
        "total": total,
        "task_mgmt_pct": task_mgmt_count / total if total > 0 else 0,
        "reasoning_pct": reasoning_count / total if total > 0 else 0,
        "analytical_pct": analytical_count / total if total > 0 else 0
    }


def analyze_reasoning_depth(output_dir: Path) -> Dict:
    """Analyze qualitative reasoning depth."""
    messages_file = output_dir / "agent_messages.json"
    with open(messages_file) as f:
        data = json.load(f)

    messages = data["messages"]

    # Count reasoning indicators
    synthesis_count = 0
    hypothesis_count = 0
    reflection_count = 0

    for msg in messages:
        if msg.get("role") == "assistant":
            content = msg.get("content", "")
            content_lower = content.lower()

            # Look for synthesis language
            if any(phrase in content_lower for phrase in [
                "synthesize", "across all", "combining these", "overall pattern"
            ]):
                synthesis_count += 1

            # Look for hypothesis language
            if any(phrase in content_lower for phrase in [
                "hypothesis", "i predict", "i expect", "this should"
            ]):
                hypothesis_count += 1

            # Look for reflection language
            if any(phrase in content_lower for phrase in [
                "reflecting", "looking back", "reviewing", "evaluating"
            ]):
                reflection_count += 1

    return {
        "synthesis_instances": synthesis_count,
        "hypothesis_instances": hypothesis_count,
        "reflection_instances": reflection_count,
        "total_reasoning_indicators": synthesis_count + hypothesis_count + reflection_count
    }


def analyze_portfolio_quality(result: Dict) -> Dict:
    """Analyze final portfolio quality."""
    # Extract portfolio metrics from result
    # This is domain-specific

    final_answer = result.get("final_answer", "{}")
    try:
        portfolio_data = json.loads(final_answer)
        improvements = portfolio_data.get("improvements", {})

        return {
            "sharpe_change": improvements.get("sharpe_ratio", ""),
            "volatility_change": improvements.get("annualized_volatility", ""),
            "beta_change": improvements.get("beta", ""),
            "constraints_met": True,  # Would need to validate
        }
    except:
        return {"error": "Could not parse portfolio data"}


def compare_benchmarks(baseline_metrics: Dict, improved_metrics: Dict) -> Dict:
    """Compare baseline vs improved agent."""
    comparison = {
        "tool_call_improvement": {
            "task_mgmt_reduction": (
                baseline_metrics["tool_calls"]["task_mgmt_pct"] -
                improved_metrics["tool_calls"]["task_mgmt_pct"]
            ),
            "reasoning_increase": (
                improved_metrics["tool_calls"]["reasoning_pct"] -
                baseline_metrics["tool_calls"]["reasoning_pct"]
            )
        },
        "reasoning_improvement": {
            "synthesis_increase": (
                improved_metrics["reasoning_depth"]["synthesis_instances"] -
                baseline_metrics["reasoning_depth"]["synthesis_instances"]
            ),
            "hypothesis_increase": (
                improved_metrics["reasoning_depth"]["hypothesis_instances"] -
                baseline_metrics["reasoning_depth"]["hypothesis_instances"]
            )
        },
        "efficiency_improvement": {
            "iteration_change": (
                improved_metrics["total_iterations"] -
                baseline_metrics["total_iterations"]
            ),
            "token_change": (
                improved_metrics["total_tokens"] -
                baseline_metrics["total_tokens"]
            )
        }
    }

    return comparison


if __name__ == "__main__":
    # Run benchmarks
    portfolio_id = "26da638b-5602-4e07-aeba-08dc1052bd86"

    print("Running improved agent benchmark...")
    improved_metrics = run_optimizer_benchmark(
        portfolio_id=portfolio_id,
        output_dir=Path("./benchmark_output/improved"),
        run_name="improved"
    )

    print("\nImproved Agent Metrics:")
    print(json.dumps(improved_metrics, indent=2))

    # Load baseline metrics (from pre-improvement run)
    # You would run this once before starting improvements
    baseline_file = Path("./benchmark_output/baseline/metrics.json")
    if baseline_file.exists():
        with open(baseline_file) as f:
            baseline_metrics = json.load(f)

        print("\nComparison:")
        comparison = compare_benchmarks(baseline_metrics, improved_metrics)
        print(json.dumps(comparison, indent=2))
```

### Testing Procedure

1. **Baseline (Before improvements):**
   - Run OptimizerAgent, save metrics
   - Document: tool call ratio, reasoning instances, output quality

2. **After Phase 1:**
   - Run benchmark
   - Expected: Task mgmt 56% → 35%
   - Validate: Agent still works

3. **After Phase 2:**
   - Run benchmark
   - Expected: Task mgmt 35% → 25%, reasoning tools used 3-8 times
   - Validate: Deeper reasoning visible

4. **After Phase 3:**
   - Run benchmark
   - Expected: Multiple refinement iterations, adaptive behavior
   - Validate: Output quality maintained or improved

### Tuning Parameters

Based on benchmark results, tune:

1. **Reasoning checkpoint frequency:**
   - If agent uses reasoning tools excessively: reduce checkpoint frequency
   - If agent ignores reasoning tools: strengthen checkpoint language

2. **Evidence logging threshold:**
   - If debugging is harder: increase evidence logging
   - If task_state.json still too large: further reduce

3. **Context injection frequency:**
   - If agent loses task context: increase from 6 → 5 iterations
   - If context bloat still high: reduce to 7-8 iterations

4. **Plan granularity:**
   - If agent struggles with vague subtasks: allow slightly more granularity
   - If agent still too mechanical: consolidate further

---

## Risk Management

### Rollback Strategy

Each phase has clear rollback:
- **Git commits after each change:** Can revert to any prior state
- **Feature flags:** Could add flags to enable/disable reasoning prompts
- **Preserve old tools:** Keep deprecated tools in codebase (commented out)

### Backward Compatibility

- Other agents using base_agent should be unaffected
- Changes are primarily additive (new tools, new prompts)
- Removals (update_task_status) are graceful (system auto-advances anyway)

### Testing Gates

Must pass before advancing:
- ✅ Phase 1 → Phase 2: Tool overhead reduced, agent completes task
- ✅ Phase 2 → Phase 3: Reasoning tools used, synthesis visible
- ✅ Phase 3 → Phase 4: Multiple refinement attempts, adaptive behavior
- ✅ Phase 4 completion: Benchmark shows improvements, output quality maintained

---

## Success Metrics

### Quantitative Targets

| Metric | Baseline | Phase 1 | Phase 2 | Phase 3 | Phase 4 (Target) |
|--------|----------|---------|---------|---------|------------------|
| **Task Mgmt %** | 56% | 35% | 25% | 20% | 20% |
| **Analytical %** | 44% | 65% | 65% | 70% | 70% |
| **Reasoning %** | 0% | 0% | 10% | 10% | 10% |
| **Plan Subtasks** | 30 | 18 | 15 | 15 | 15 |
| **Context Injections** | 28 | 14 | 14 | 14 | 14 |
| **Evidence Entries** | 148 | 30 | 30 | 30 | 30 |
| **Reasoning Tool Calls** | 0 | 0 | 3-8 | 5-10 | 5-10 |
| **Refinement Iterations** | 1 | 1 | 1-2 | 2-3 | 2-3 |

### Qualitative Indicators

**Baseline (Mechanical Execution):**
- ❌ Linear task execution
- ❌ Minimal synthesis
- ❌ Superficial refinement

**Target (Intelligent Analysis):**
- ✅ Synthesis across tool results
- ✅ Hypothesis formation and testing
- ✅ Strategic reflection and adjustment
- ✅ Multiple refinement iterations
- ✅ Adaptive plan modification (when needed)

---

## Documentation and Handoff

### Code Documentation

Each change should include:
- Inline comments explaining rationale
- Docstrings for new functions
- Update to relevant README sections

### Change Log

Maintain `.claude/CHANGELOG_reasoning_improvements.md`:
```markdown
# Agent Reasoning Improvements Changelog

## Phase 1: Reduce Overhead (2025-10-25 to 2025-10-27)

### Change 1.1: Modified PlanningTool Prompt
- File: `planning_tool.py`
- Change: Removed prohibition on thinking subtasks
- Impact: Plans now include synthesis/reflection subtasks
- Commit: abc123

### Change 1.2: Reduced Context Injection
...
```

### Lessons Learned

Document:
- What worked well
- What didn't work
- Unexpected findings
- Recommendations for future improvements

---

## Conclusion

This implementation plan transforms base_agent from a **task executor** to an **intelligent analyst** through:

1. **Reduced Overhead** (Phase 1): Free up 35% of tool calls
2. **Reasoning Tools** (Phase 2): Enable synthesis, hypothesis testing
3. **Adaptive Execution** (Phase 3): Allow plan modification, deep refinement
4. **Validation** (Phase 4): Measure and tune improvements

**Key Principles:**
- ✅ Incremental changes with validation
- ✅ Backward compatible
- ✅ Low-risk first, high-impact priority
- ✅ Continuous testing

**Timeline:** 2-3 weeks
**Risk:** Low-Medium (incremental approach minimizes risk)
**Impact:** HIGH (transformation from mechanical to intelligent execution)

---

**Next Steps:**
1. Review this plan with team
2. Create git branch: `feature/agent-reasoning-enhancement`
3. Begin Phase 1, Change 1.1
4. Follow plan systematically with validation at each step

**Let's build an agent that thinks, not just executes.**
