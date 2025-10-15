# Tool Evaluation Strategy for ProphitAI Agent Framework

## Executive Summary

This document outlines a comprehensive strategy for evaluating tool effectiveness in ProphitAI's institutional-grade portfolio management agent framework. Based on Anthropic's best practices and adapted for financial domain complexity, this evaluation framework will measure tool performance, identify optimization opportunities, and ensure agents can reliably construct sophisticated portfolios.

---

## 1. Current State Analysis

### 1.1 Agent Architecture
Your framework implements a sophisticated multi-agent system with:
- **BaseAgent**: ReAct pattern with native tool-calling across multiple LLM providers
- **Specialized Agents**: CIO, CRO, Industry-specific agents with domain memories
- **Tool Categories**:
  - **Base Tools** (15+): Planning, task management, episodic memory, search, calculator
  - **Data Tools** (5+): Stock screener, fundamentals, industry factors, repository
  - **Portfolio Tools** (10+): Concentration, performance, returns, factor tilts, beta, correlations
  - **Risk Tools** (7+): VaR/ES, covariance, stress testing, drawdowns, pairwise correlation
  - **Agent-Specific Tools** (4): CIO, CRO, Industry, Optimizer tools

### 1.2 Tool Design Strengths
- **Structured Responses**: Consistent YAML output with success/error fields
- **Validation Decorators**: `@validate_required_args`, `@validate_portfolio_dict`, `@validate_enum_arg`
- **Simulation Support**: `_simulation_date` injection for backtesting
- **Rich Descriptions**: Comprehensive tool descriptions with examples and constraints
- **Pydantic Models**: Strong typing for complex inputs (ScreenerConstraints, TodoList)

### 1.3 Gaps & Challenges
- **No Systematic Evaluation**: No framework for measuring tool effectiveness
- **Complex Financial Domain**: Portfolio construction requires multi-step workflows with 20+ tools
- **Token Efficiency Unknown**: No metrics on tool response sizes vs. usefulness
- **Tool Confusion Risk**: Similar tools (e.g., 15+ task management tools) may cause selection errors
- **Error Pattern Tracking**: Limited visibility into repeated tool failures

---

## 2. Evaluation Framework Design

### 2.1 Core Principles (Adapted from Anthropic)

**Principle 1: Real-World Task Grounding**
- Evaluation tasks MUST reflect actual portfolio construction workflows
- Use realistic market data and multi-ticker portfolios (not toy examples)
- Test complex scenarios: sector rotation, risk rebalancing, drawdown management

**Principle 2: Comprehensive Coverage**
- Evaluate EVERY tool category: base, data, portfolio, risk, agent-specific
- Test tool combinations (e.g., screener → fundamentals → portfolio construction)
- Measure both individual tool performance AND workflow completion

**Principle 3: Quantitative + Qualitative Metrics**
- Track hard metrics: accuracy, token usage, latency, error rates
- Capture soft insights: tool clarity, parameter confusion, redundant calls

**Principle 4: Iterative Optimization**
- Use Claude/agents to analyze failures and suggest tool improvements
- Re-evaluate after each optimization cycle
- Maintain held-out test sets to prevent overfitting

---

### 2.2 Evaluation Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   EVALUATION SYSTEM                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. TASK GENERATION                                          │
│     ├─ Portfolio Construction Tasks (40%)                    │
│     ├─ Risk Analysis Tasks (30%)                            │
│     ├─ Stock Research Tasks (20%)                           │
│     └─ Task Management/Planning Tasks (10%)                 │
│                                                               │
│  2. EVALUATION RUNNER                                        │
│     ├─ Agent Loop (from notebook)                           │
│     ├─ Tool Execution Tracking                              │
│     ├─ Metrics Collection                                    │
│     └─ Transcript Logging                                    │
│                                                               │
│  3. ANALYSIS ENGINE                                          │
│     ├─ Accuracy Scoring                                      │
│     ├─ Tool Usage Analytics                                  │
│     ├─ Error Pattern Detection                               │
│     ├─ Token Efficiency Analysis                             │
│     └─ Agent-Assisted Feedback                               │
│                                                               │
│  4. OPTIMIZATION LOOP                                        │
│     ├─ Tool Description Refinement                           │
│     ├─ Parameter Schema Updates                              │
│     ├─ Tool Consolidation Recommendations                    │
│     └─ Re-evaluation & Validation                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Evaluation Task Design

### 3.1 Task Categories & Examples

#### A. Portfolio Construction Tasks (High Priority)

**Task 1: Defensive Sector Portfolio**
```xml
<task>
  <prompt>
    Build a 10-position long-only portfolio focused on defensive consumer staples stocks.
    Target: large-cap companies with ROE > 15%, dividend yield > 2%, and beta < 0.9.
    Ensure industry diversification across at least 3 sub-industries.
    Provide allocation percentages and investment thesis for each position.
  </prompt>
  <response>
    {
      "portfolio": [
        {"ticker": "PG", "allocation": 0.12, "thesis": "...", "sub_industry": "household_products"},
        {"ticker": "KO", "allocation": 0.11, "thesis": "...", "sub_industry": "beverages"},
        ...
      ],
      "total_allocation": 1.0,
      "sub_industries": ["household_products", "beverages", "packaged_foods"],
      "avg_beta": 0.82,
      "avg_roe": 0.18
    }
  </response>
</task>
```

**Task 2: Risk-Adjusted Rebalancing**
```xml
<task>
  <prompt>
    You manage a consumer staples portfolio with 8 positions. Current portfolio:
    {'PG': 0.15, 'KO': 0.15, 'WMT': 0.14, 'COST': 0.14, 'PEP': 0.13, 'MO': 0.12, 'PM': 0.10, 'MDLZ': 0.07}

    Portfolio VaR has increased to 0.08 (target: 0.05). Identify high-risk positions and rebalance
    to reduce portfolio VaR while maintaining sector focus. Provide before/after VaR comparison.
  </prompt>
  <response>
    {
      "high_risk_positions": ["MO", "PM"],
      "rebalanced_portfolio": {...},
      "initial_var": 0.08,
      "final_var": 0.049,
      "var_reduction": 0.031
    }
  </response>
</task>
```

**Task 3: Multi-Factor Stock Selection**
```xml
<task>
  <prompt>
    Find 3 consumer staples stocks with: (1) strong profitability (ROE > 20%, net margin > 12%),
    (2) reasonable valuation (PE < 25, PEG < 2), (3) low leverage (debt-to-equity < 0.6),
    and (4) positive analyst sentiment (rating score > 3.5).
    Compare their 1-year performance and select the best candidate.
  </prompt>
  <response>
    {
      "candidates": [
        {"ticker": "MNST", "roe": 0.23, "pe": 22.3, "debt_to_equity": 0.45, "rating": 4.1, "1y_return": 0.18},
        ...
      ],
      "selected": "MNST",
      "reasoning": "Highest ROE with strong growth momentum..."
    }
  </response>
</task>
```

#### B. Risk Analysis Tasks

**Task 4: Stress Testing**
```xml
<task>
  <prompt>
    Stress test this portfolio against market downturns:
    {'AAPL': 0.2, 'MSFT': 0.2, 'GOOGL': 0.2, 'AMZN': 0.2, 'TSLA': 0.2}
    Calculate portfolio VaR, identify the highest risk contributor, and analyze correlation structure.
  </prompt>
  <response>
    {
      "portfolio_var": 0.12,
      "top_risk_contributor": {"ticker": "TSLA", "risk_contribution": 0.045},
      "avg_correlation": 0.67,
      "diversification_benefit": 0.23
    }
  </response>
</task>
```

#### C. Stock Research Tasks

**Task 5: Fundamental Deep Dive**
```xml
<task>
  <prompt>
    Analyze COST (Costco). Pull fundamentals, check valuation metrics (PE, PB, PS),
    evaluate profitability (ROE, margins), and assess 1-year performance vs SPY benchmark.
    Provide investment recommendation.
  </prompt>
  <response>
    {
      "ticker": "COST",
      "valuation": {"pe": 45.2, "pb": 12.1, "ps": 1.2},
      "profitability": {"roe": 0.28, "gross_margin": 0.13, "net_margin": 0.03},
      "performance": {"1y_return": 0.32, "spy_return": 0.24, "alpha": 0.08},
      "recommendation": "BUY",
      "reasoning": "Premium valuation justified by exceptional ROE..."
    }
  </response>
</task>
```

#### D. Task Management & Planning

**Task 6: Structured Plan Execution**
```xml
<task>
  <prompt>
    Create a structured plan to build a 15-position long-short consumer staples portfolio
    with 10 longs and 5 shorts, targeting 1.3x gross exposure and 0.3x net exposure.
  </prompt>
  <response>
    {
      "plan_created": true,
      "main_tasks": 5,
      "subtasks": 12,
      "predicted_tools": ["stock_screener", "get_analyst_picks", "portfolio_exposure_calculator"],
      "plan_completed": true
    }
  </response>
</task>
```

### 3.2 Task Generation Strategy

**Volume**: Generate 80-120 evaluation tasks across categories
- 40 Portfolio Construction (complex, multi-step)
- 30 Risk Analysis (quantitative validation)
- 20 Stock Research (tool combination workflows)
- 10 Task Management (plan-driven execution)

**Difficulty Levels**:
- **Easy** (30%): Single-tool tasks with clear success criteria
- **Medium** (50%): 2-4 tool workflows requiring sequential reasoning
- **Hard** (20%): Complex multi-tool workflows with ambiguous requirements

**Data Realism**:
- Use ACTUAL tickers from your database (consumer staples, tech, healthcare)
- Reference realistic portfolio sizes (8-15 positions for funds)
- Include market context (defensive rotation, growth selloff, etc.)

---

## 4. Evaluation Metrics

### 4.1 Primary Metrics

**Accuracy (Top-Level Success Rate)**
```python
accuracy = correct_responses / total_tasks
```
- **Target**: >85% for production readiness
- **Measurement**: Ground truth comparison (portfolio structure, numeric thresholds, ticker lists)

**Tool Efficiency**
```python
tool_efficiency = successful_tasks / total_tool_calls
avg_tools_per_task = total_tool_calls / total_tasks
```
- **Target**: <8 tool calls per complex task
- **Detect**: Redundant calls, stagnation loops, trial-and-error patterns

**Token Consumption**
```python
tokens_per_task = (input_tokens + output_tokens) / total_tasks
tool_response_tokens = sum(len(tool_output) for tool in task_tools)
```
- **Target**: <50K tokens per portfolio construction task
- **Optimize**: Verbose tool responses (stock_screener debug output)

**Error Rates**
```python
tool_error_rate = failed_tool_calls / total_tool_calls
parameter_error_rate = invalid_parameter_calls / total_tool_calls
```
- **Target**: <5% tool error rate
- **Track**: Repeated failures with same tool/parameters

### 4.2 Secondary Metrics

**Tool Usage Patterns**
- Most/least used tools
- Tool call sequences (workflow patterns)
- Tool co-occurrence matrix (which tools used together)

**Task Completion Time**
- Average task duration (seconds)
- Tool execution latency breakdown

**Plan Execution Health** (for plan-driven tasks)
- Plan completion rate
- Task advancement patterns
- Stagnation incidents

---

## 5. Evaluation Infrastructure

### 5.1 Core Components (Based on notebook)

```python
# app/core/agentic_framework/evaluation/evaluator.py

class ToolEvaluator:
    """Comprehensive tool evaluation system for ProphitAI agents."""

    def __init__(self, agent_class, eval_tasks_path: str):
        self.agent_class = agent_class
        self.eval_tasks = self._load_tasks(eval_tasks_path)
        self.results = []

    def run_evaluation(self) -> EvaluationReport:
        """Run all evaluation tasks and collect metrics."""
        for task in self.eval_tasks:
            result = self._evaluate_single_task(task)
            self.results.append(result)

        return self._generate_report()

    def _evaluate_single_task(self, task: EvalTask) -> TaskResult:
        """Run agent on task with tool tracking."""
        agent = self.agent_class()

        # Wrap agent to track tool calls
        agent = ToolTrackingWrapper(agent)

        start_time = time.time()
        output = agent.run()  # Execute task
        duration = time.time() - start_time

        # Extract metrics
        tool_metrics = agent.get_tool_metrics()
        accuracy = self._score_accuracy(output, task.expected_response)

        return TaskResult(
            task_id=task.id,
            prompt=task.prompt,
            expected=task.expected_response,
            actual=output,
            accuracy=accuracy,
            tool_calls=tool_metrics,
            duration=duration,
            summary=output.get('summary'),
            feedback=output.get('feedback')
        )

    def _score_accuracy(self, actual, expected) -> float:
        """Score task accuracy using LLM-as-judge."""
        # For structured outputs (portfolios), use schema validation
        # For numeric outputs, use threshold comparison
        # For text outputs, use LLM-based similarity scoring
        pass

    def _generate_report(self) -> EvaluationReport:
        """Generate comprehensive evaluation report."""
        return EvaluationReport(
            overall_accuracy=self._calculate_accuracy(),
            tool_usage_stats=self._analyze_tool_usage(),
            error_patterns=self._detect_error_patterns(),
            token_efficiency=self._calculate_token_metrics(),
            recommendations=self._generate_recommendations()
        )
```

### 5.2 Tool Tracking Wrapper

```python
class ToolTrackingWrapper:
    """Wrap agent to track all tool executions."""

    def __init__(self, agent):
        self.agent = agent
        self.tool_calls = []
        self._wrap_tool_functions()

    def _wrap_tool_functions(self):
        """Intercept all tool calls for tracking."""
        for tool_name, tool_func in self.agent.tool_functions.items():
            self.agent.tool_functions[tool_name] = self._create_wrapper(tool_name, tool_func)

    def _create_wrapper(self, tool_name, tool_func):
        def wrapped(**kwargs):
            start_time = time.time()
            try:
                result = tool_func(**kwargs)
                success = self._parse_success(result)
                error = None
            except Exception as e:
                result = str(e)
                success = False
                error = str(e)

            duration = time.time() - start_time

            self.tool_calls.append({
                'tool_name': tool_name,
                'args': kwargs,
                'result': result,
                'success': success,
                'error': error,
                'duration': duration,
                'timestamp': time.time()
            })

            return result
        return wrapped

    def get_tool_metrics(self) -> Dict:
        """Return aggregated tool metrics."""
        return {
            'total_calls': len(self.tool_calls),
            'unique_tools': len(set(tc['tool_name'] for tc in self.tool_calls)),
            'success_rate': sum(tc['success'] for tc in self.tool_calls) / len(self.tool_calls),
            'avg_duration': sum(tc['duration'] for tc in self.tool_calls) / len(self.tool_calls),
            'tool_sequence': [tc['tool_name'] for tc in self.tool_calls],
            'failed_tools': [tc for tc in self.tool_calls if not tc['success']]
        }
```

---

## 6. Analysis & Optimization Loop

### 6.1 Automated Analysis (LLM-Assisted)

```python
def analyze_evaluation_results(results: List[TaskResult]) -> AnalysisReport:
    """Use Claude to analyze evaluation transcripts and identify issues."""

    # Group failures by error type
    failures = [r for r in results if r.accuracy < 0.7]

    # Extract patterns
    analysis_prompt = f"""
    Analyze these {len(failures)} failed agent executions:

    {format_failures(failures)}

    Identify:
    1. Tool description issues (ambiguous, misleading, incomplete)
    2. Parameter confusion (missing required args, type mismatches)
    3. Workflow inefficiencies (redundant calls, wrong tool selection)
    4. Response format problems (too verbose, missing key info)

    Provide specific, actionable recommendations for each issue.
    """

    analysis = call_claude(analysis_prompt)

    return AnalysisReport(
        tool_issues=analysis['tool_issues'],
        parameter_issues=analysis['parameter_issues'],
        workflow_issues=analysis['workflow_issues'],
        recommendations=analysis['recommendations']
    )
```

### 6.2 Tool Optimization Workflow

```
┌──────────────────────────────────────────────────┐
│         OPTIMIZATION CYCLE                       │
├──────────────────────────────────────────────────┤
│                                                   │
│  1. Run Evaluation (80-120 tasks)               │
│     ↓                                            │
│  2. Collect Metrics & Transcripts                │
│     ↓                                            │
│  3. Identify Failure Patterns                    │
│     ↓                                            │
│  4. LLM-Assisted Root Cause Analysis             │
│     ↓                                            │
│  5. Generate Tool Improvements                   │
│     ├─ Description Clarification                │
│     ├─ Parameter Schema Updates                 │
│     ├─ Response Format Optimization             │
│     └─ Tool Consolidation                       │
│     ↓                                            │
│  6. Implement Changes                            │
│     ↓                                            │
│  7. Re-evaluate (Held-Out Test Set)             │
│     ↓                                            │
│  8. Compare Metrics (Before/After)               │
│     ↓                                            │
│  9. Iterate Until Target Accuracy Reached        │
│                                                   │
└──────────────────────────────────────────────────┘
```

---

## 7. Specific Tool Improvement Recommendations

### 7.1 High-Priority Optimizations

**Issue 1: Task Management Tool Overload (15+ tools)**
- **Problem**: Agent may struggle to choose between get_current_task_info, get_execution_summary, get_task_progress_summary, get_completion_analysis
- **Solution**: Consolidate into 3 core tools:
  1. `get_plan_status` (combines current task + progress + completion confidence)
  2. `advance_task` (simplified progression)
  3. `handle_failure` (recovery strategies)

**Issue 2: Stock Screener Verbosity**
- **Problem**: Debug output consumes tokens (lines 617-728 in stock_screener.py)
- **Solution**: Add `verbose` parameter to tool, disable debug output in evaluation mode

**Issue 3: Portfolio Tool Parameter Confusion**
- **Problem**: All portfolio tools require `portfolio_dict`, but agents may forget to include it
- **Solution**: Tool descriptions already emphasize "MANDATORY", but add runtime validation to return helpful error: "Missing portfolio_dict - you must provide the full portfolio in every call"

**Issue 4: Ambiguous Tool Names**
- **Problem**: `VaR_calculator` vs `portfolio_VaR_calculator` (inconsistent naming)
- **Solution**: Standardize namespace prefixes:
  - `portfolio_*` for portfolio-level tools
  - `risk_*` for risk analysis tools
  - `ticker_*` for single-ticker tools
  - `screen_*` for search/filter tools

### 7.2 Tool Description Refinements

**Current Example** (exposure_calculator):
```python
"Calculate portfolio exposure metrics. Net exposure is long minus short..."
```

**Improved** (more explicit about when to use):
```python
"""Calculate portfolio exposure metrics for position sizing validation.

USE WHEN:
- Verifying gross/net exposure targets after portfolio construction
- Checking leverage constraints (gross exposure > 1.0)
- Validating long/short balance in market-neutral strategies

RETURNS: Single float value for specified exposure type

EXAMPLE WORKFLOW:
1. Build portfolio with stock_screener + fundamentals
2. Call exposure_calculator(portfolio_dict={...}, exposure_type='gross')
3. If gross > target, reduce position sizes proportionally

DO NOT USE FOR:
- Individual position sizing (use allocations directly)
- Risk contribution analysis (use VaR_calculator instead)
"""
```

---

## 8. Implementation Roadmap

### Phase 1: Infrastructure Setup (Week 1)
1. Create evaluation task dataset (80 tasks minimum)
   - 40 portfolio construction
   - 30 risk analysis
   - 20 stock research
   - 10 task management
2. Implement `ToolEvaluator` class with tracking wrapper
3. Set up metrics collection pipeline
4. Create evaluation report templates

### Phase 2: Baseline Evaluation (Week 2)
1. Run full evaluation suite on current tools
2. Collect baseline metrics (accuracy, token usage, tool patterns)
3. Generate evaluation transcripts
4. Perform manual review of top 20 failures

### Phase 3: Analysis & Optimization (Weeks 3-4)
1. Use Claude to analyze failure patterns
2. Identify top 10 tool improvement opportunities
3. Implement high-priority fixes:
   - Tool description refinements
   - Parameter schema updates
   - Response format optimization
   - Tool consolidation (task management)
4. Add validation decorators for common errors

### Phase 4: Re-Evaluation & Iteration (Week 5)
1. Re-run evaluation on held-out test set (20% of tasks)
2. Compare before/after metrics
3. Document improvements (target: +10% accuracy, -20% tokens)
4. Iterate on remaining issues

### Phase 5: Continuous Monitoring (Ongoing)
1. Add new evaluation tasks from production use cases
2. Run monthly evaluation benchmarks
3. Track tool usage patterns in production
4. Maintain evaluation dashboard

---

## 9. Success Criteria

### Quantitative Targets
- **Overall Accuracy**: >85% on evaluation suite
- **Tool Error Rate**: <5% failed tool calls
- **Token Efficiency**: <50K tokens per portfolio construction task
- **Task Completion**: >90% of tasks complete without stagnation

### Qualitative Goals
- Agent selects appropriate tools 95% of the time on first attempt
- Tool descriptions are clear enough that parameter errors are <3%
- Evaluation transcripts show logical workflows (not trial-and-error)
- Failed tasks have clear root causes (data issues, not tool confusion)

---

## 10. Conclusion

This evaluation framework provides a systematic approach to optimizing tool effectiveness for ProphitAI's agent system. By combining quantitative metrics, LLM-assisted analysis, and iterative refinement, you'll achieve:

1. **Higher Reliability**: Agents that consistently complete complex portfolio tasks
2. **Better Efficiency**: Reduced token usage and tool call counts
3. **Clearer Debugging**: Structured transcripts revealing failure root causes
4. **Continuous Improvement**: Evaluation pipeline for ongoing optimization

The key differentiator from the Anthropic approach is the **financial domain complexity** - your agents must orchestrate 20+ tools across multi-step workflows to construct institutional-grade portfolios. This requires:
- **Workflow-based evaluation** (not just individual tool testing)
- **Quantitative validation** (portfolio metrics, VaR calculations)
- **Domain-specific ground truth** (realistic market data, analyst picks)

By investing in this evaluation infrastructure now, you'll build confidence that your agents can handle production portfolio management tasks with institutional rigor.

---

## 11. Implementation Plan & File Structure

### 11.1 Proposed Directory Structure

```
app/core/agentic_framework/evaluation/
│
├── __init__.py                          # Package initialization
│
├── core/                                # Core evaluation infrastructure
│   ├── __init__.py
│   ├── evaluator.py                    # Main ToolEvaluator class
│   ├── task_runner.py                  # Individual task execution logic
│   ├── tracking_wrapper.py             # ToolTrackingWrapper for instrumenting agents
│   └── metrics_collector.py            # Metrics aggregation and calculation
│
├── tasks/                               # Evaluation task definitions
│   ├── __init__.py
│   ├── models.py                       # Pydantic models (EvalTask, TaskResult, etc.)
│   ├── task_loader.py                  # Load tasks from YAML/JSON files
│   ├── task_generator.py               # LLM-assisted task generation
│   └── datasets/                       # Task dataset files
│       ├── portfolio_construction.yaml  # 40 portfolio construction tasks
│       ├── risk_analysis.yaml          # 30 risk analysis tasks
│       ├── stock_research.yaml         # 20 stock research tasks
│       └── task_management.yaml        # 10 task management tasks
│
├── analysis/                            # Result analysis and optimization
│   ├── __init__.py
│   ├── accuracy_scorer.py              # LLM-as-judge accuracy scoring
│   ├── pattern_detector.py             # Error pattern detection
│   ├── tool_usage_analyzer.py          # Tool usage statistics and patterns
│   ├── token_analyzer.py               # Token efficiency analysis
│   └── llm_analyzer.py                 # Claude-assisted failure analysis
│
├── reporting/                           # Report generation
│   ├── __init__.py
│   ├── report_generator.py             # EvaluationReport generation
│   ├── visualizations.py               # Charts and graphs (optional)
│   └── templates/                      # Report templates
│       ├── summary_report.md           # Markdown report template
│       └── detailed_report.html        # HTML report template (optional)
│
├── optimization/                        # Tool optimization workflows
│   ├── __init__.py
│   ├── tool_improver.py                # LLM-assisted tool improvement suggestions
│   ├── description_optimizer.py        # Tool description refinement
│   └── consolidation_analyzer.py       # Tool consolidation recommendations
│
├── scripts/                             # Executable scripts
│   ├── run_evaluation.py               # CLI for running evaluations
│   ├── generate_tasks.py               # Generate evaluation tasks
│   ├── analyze_results.py              # Analyze evaluation results
│   └── compare_runs.py                 # Compare before/after metrics
│
├── config/                              # Configuration files
│   ├── evaluation_config.yaml          # Evaluation settings
│   └── metrics_config.yaml             # Metric thresholds and targets
│
└── results/                             # Evaluation outputs (gitignored)
    ├── runs/                           # Individual evaluation runs
    │   └── {timestamp}/
    │       ├── results.json            # Raw results
    │       ├── transcripts/            # Agent execution transcripts
    │       ├── metrics.json            # Computed metrics
    │       └── report.md               # Generated report
    └── comparisons/                    # Before/after comparisons
        └── {comparison_id}/
            ├── comparison.json
            └── comparison_report.md
```

### 11.2 Core Module Specifications

#### 11.2.1 `evaluation/tasks/models.py`

```python
"""Pydantic models for evaluation tasks and results."""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Literal
from datetime import datetime


class EvalTask(BaseModel):
    """Single evaluation task definition."""

    task_id: str = Field(..., description="Unique task identifier")
    category: Literal["portfolio_construction", "risk_analysis", "stock_research", "task_management"]
    difficulty: Literal["easy", "medium", "hard"]
    prompt: str = Field(..., description="Task prompt for the agent")
    expected_response: Dict[str, Any] = Field(..., description="Expected output structure")
    validation_criteria: Dict[str, Any] = Field(
        default_factory=dict,
        description="Specific validation rules (thresholds, required fields, etc.)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (tickers, market context, etc.)"
    )


class ToolCall(BaseModel):
    """Single tool execution record."""

    tool_name: str
    args: Dict[str, Any]
    result: Any
    success: bool
    error: Optional[str] = None
    duration: float  # seconds
    timestamp: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class TaskResult(BaseModel):
    """Result of a single evaluation task execution."""

    task_id: str
    category: str
    difficulty: str
    prompt: str
    expected: Dict[str, Any]
    actual: Dict[str, Any]
    accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy score 0-1")
    tool_calls: List[ToolCall]
    duration: float  # total task duration in seconds
    total_tokens: int
    success: bool
    error: Optional[str] = None
    transcript: Optional[str] = None  # Full agent conversation
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ToolUsageStats(BaseModel):
    """Aggregated tool usage statistics."""

    tool_name: str
    total_calls: int
    success_calls: int
    failed_calls: int
    avg_duration: float
    total_tokens: int
    usage_percentage: float  # percentage of tasks using this tool


class ErrorPattern(BaseModel):
    """Detected error pattern."""

    pattern_type: Literal["tool_selection", "parameter_error", "workflow_inefficiency", "response_format"]
    tool_name: Optional[str] = None
    frequency: int
    example_task_ids: List[str]
    description: str
    suggested_fix: Optional[str] = None


class EvaluationReport(BaseModel):
    """Comprehensive evaluation report."""

    run_id: str
    timestamp: datetime
    total_tasks: int
    overall_accuracy: float
    accuracy_by_category: Dict[str, float]
    accuracy_by_difficulty: Dict[str, float]
    tool_usage_stats: List[ToolUsageStats]
    error_patterns: List[ErrorPattern]
    avg_tokens_per_task: float
    avg_duration_per_task: float
    tool_error_rate: float
    recommendations: List[str]
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### 11.2.2 `evaluation/core/evaluator.py`

```python
"""Main evaluation orchestrator."""

from typing import List, Optional, Type
from pathlib import Path
import json
import time
from datetime import datetime

from app.core.agentic_framework.base_agent.agent import BaseAgent
from .task_runner import TaskRunner
from .metrics_collector import MetricsCollector
from ..tasks.models import EvalTask, TaskResult, EvaluationReport
from ..tasks.task_loader import TaskLoader
from ..analysis.report_generator import ReportGenerator


class ToolEvaluator:
    """Comprehensive tool evaluation system for ProphitAI agents."""

    def __init__(
        self,
        agent_class: Type[BaseAgent],
        tasks_path: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        config: Optional[Dict] = None
    ):
        """
        Initialize evaluator.

        Args:
            agent_class: Agent class to evaluate (e.g., CIOAgent)
            tasks_path: Path to evaluation tasks directory
            output_dir: Directory for evaluation outputs
            config: Evaluation configuration overrides
        """
        self.agent_class = agent_class
        self.tasks_path = tasks_path or Path("app/core/agentic_framework/evaluation/tasks/datasets")
        self.output_dir = output_dir or Path("app/core/agentic_framework/evaluation/results/runs")
        self.config = config or {}

        # Initialize components
        self.task_loader = TaskLoader(self.tasks_path)
        self.task_runner = TaskRunner(agent_class, self.config)
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator()

        # Results storage
        self.results: List[TaskResult] = []
        self.run_id = f"eval_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    def run_evaluation(
        self,
        categories: Optional[List[str]] = None,
        max_tasks: Optional[int] = None
    ) -> EvaluationReport:
        """
        Run full evaluation suite.

        Args:
            categories: Filter to specific task categories (default: all)
            max_tasks: Limit number of tasks (for testing)

        Returns:
            EvaluationReport with comprehensive metrics
        """
        # Load tasks
        tasks = self.task_loader.load_tasks(categories=categories, max_tasks=max_tasks)
        print(f"Loaded {len(tasks)} evaluation tasks")

        # Run tasks
        for i, task in enumerate(tasks, 1):
            print(f"\n[{i}/{len(tasks)}] Running task: {task.task_id}")
            result = self.task_runner.run_task(task)
            self.results.append(result)

            # Print immediate feedback
            status = "✓ PASS" if result.accuracy >= 0.7 else "✗ FAIL"
            print(f"  {status} | Accuracy: {result.accuracy:.2f} | Tools: {len(result.tool_calls)} | Tokens: {result.total_tokens}")

        # Generate report
        report = self._generate_report()

        # Save results
        self._save_results(report)

        return report

    def _generate_report(self) -> EvaluationReport:
        """Generate comprehensive evaluation report."""
        return self.metrics_collector.generate_report(
            results=self.results,
            run_id=self.run_id
        )

    def _save_results(self, report: EvaluationReport):
        """Save evaluation results and report to disk."""
        run_dir = self.output_dir / self.run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Save raw results
        results_file = run_dir / "results.json"
        with open(results_file, 'w') as f:
            json.dump([r.model_dump(mode='json') for r in self.results], f, indent=2)

        # Save metrics
        metrics_file = run_dir / "metrics.json"
        with open(metrics_file, 'w') as f:
            json.dump(report.model_dump(mode='json'), f, indent=2)

        # Save markdown report
        report_md = self.report_generator.generate_markdown(report)
        report_file = run_dir / "report.md"
        with open(report_file, 'w') as f:
            f.write(report_md)

        # Save transcripts
        transcripts_dir = run_dir / "transcripts"
        transcripts_dir.mkdir(exist_ok=True)
        for result in self.results:
            if result.transcript:
                transcript_file = transcripts_dir / f"{result.task_id}.txt"
                with open(transcript_file, 'w') as f:
                    f.write(result.transcript)

        print(f"\n✓ Results saved to: {run_dir}")
```

#### 11.2.3 `evaluation/core/tracking_wrapper.py`

```python
"""Tool tracking wrapper for instrumenting agent tool calls."""

import time
from typing import Dict, List, Callable, Any
from functools import wraps

from ..tasks.models import ToolCall


class ToolTrackingWrapper:
    """Wrap agent to track all tool executions."""

    def __init__(self, agent):
        """
        Initialize wrapper.

        Args:
            agent: BaseAgent instance to wrap
        """
        self.agent = agent
        self.tool_calls: List[ToolCall] = []
        self._wrap_tool_functions()

    def _wrap_tool_functions(self):
        """Intercept all tool calls for tracking."""
        for tool_name, tool_func in self.agent.tool_functions.items():
            self.agent.tool_functions[tool_name] = self._create_wrapper(tool_name, tool_func)

    def _create_wrapper(self, tool_name: str, tool_func: Callable) -> Callable:
        """Create tracking wrapper for individual tool."""

        @wraps(tool_func)
        def wrapped(**kwargs):
            start_time = time.time()

            try:
                result = tool_func(**kwargs)
                success = self._parse_success(result)
                error = None
            except Exception as e:
                result = {"success": False, "error": str(e)}
                success = False
                error = str(e)

            duration = time.time() - start_time

            # Record tool call
            tool_call = ToolCall(
                tool_name=tool_name,
                args=kwargs,
                result=result,
                success=success,
                error=error,
                duration=duration,
                timestamp=time.time()
            )
            self.tool_calls.append(tool_call)

            return result

        return wrapped

    def _parse_success(self, result: Any) -> bool:
        """Parse tool result to determine success."""
        if isinstance(result, dict):
            return result.get('success', True)
        return True

    def get_tool_metrics(self) -> Dict:
        """Return aggregated tool metrics."""
        if not self.tool_calls:
            return {
                'total_calls': 0,
                'unique_tools': 0,
                'success_rate': 0.0,
                'avg_duration': 0.0,
                'tool_sequence': [],
                'failed_tools': []
            }

        return {
            'total_calls': len(self.tool_calls),
            'unique_tools': len(set(tc.tool_name for tc in self.tool_calls)),
            'success_rate': sum(tc.success for tc in self.tool_calls) / len(self.tool_calls),
            'avg_duration': sum(tc.duration for tc in self.tool_calls) / len(self.tool_calls),
            'tool_sequence': [tc.tool_name for tc in self.tool_calls],
            'failed_tools': [tc for tc in self.tool_calls if not tc.success]
        }

    def reset(self):
        """Clear tracked tool calls."""
        self.tool_calls = []
```

### 11.3 Implementation Phases

#### Phase 1: Foundation (Week 1)
**Goal**: Set up evaluation infrastructure and task dataset

**Tasks**:
1. Create directory structure in `app/core/agentic_framework/evaluation/`
2. Implement Pydantic models (`tasks/models.py`)
3. Implement `ToolTrackingWrapper` (`core/tracking_wrapper.py`)
4. Implement `TaskRunner` (`core/task_runner.py`)
5. Create 20 initial evaluation tasks (portfolio_construction.yaml)
6. Write CLI script (`scripts/run_evaluation.py`)

**Deliverables**:
- Basic evaluation can run on CIO Agent with 20 tasks
- Results saved to JSON files
- Simple console output showing pass/fail rates

#### Phase 2: Metrics & Analysis (Week 2)
**Goal**: Build comprehensive metrics collection and reporting

**Tasks**:
1. Implement `MetricsCollector` (`core/metrics_collector.py`)
2. Implement `AccuracyScorer` with LLM-as-judge (`analysis/accuracy_scorer.py`)
3. Implement `ToolUsageAnalyzer` (`analysis/tool_usage_analyzer.py`)
4. Implement `PatternDetector` for error detection (`analysis/pattern_detector.py`)
5. Implement `ReportGenerator` (`reporting/report_generator.py`)
6. Expand task dataset to 60 tasks (add risk_analysis.yaml, stock_research.yaml)

**Deliverables**:
- Complete evaluation report with all metrics
- Markdown report generation
- 60-task evaluation dataset

#### Phase 3: LLM-Assisted Optimization (Week 3)
**Goal**: Implement automated tool improvement recommendations

**Tasks**:
1. Implement `LLMAnalyzer` for failure pattern analysis (`analysis/llm_analyzer.py`)
2. Implement `ToolImprover` for description optimization (`optimization/tool_improver.py`)
3. Implement `ConsolidationAnalyzer` (`optimization/consolidation_analyzer.py`)
4. Create comparison script (`scripts/compare_runs.py`)
5. Complete task dataset to 100+ tasks

**Deliverables**:
- Automated tool improvement suggestions
- Before/after comparison reports
- Full 100+ task evaluation suite

#### Phase 4: Iteration & Validation (Week 4-5)
**Goal**: Optimize tools and validate improvements

**Tasks**:
1. Run baseline evaluation on current tools
2. Apply top 10 tool improvements from LLM analysis
3. Re-run evaluation and compare metrics
4. Iterate on remaining issues
5. Document optimization results

**Deliverables**:
- Baseline metrics report
- Optimized tools with measurable improvements
- Documentation of optimization process and results

### 11.4 Quick Start Commands

```bash
# Generate initial evaluation tasks
python -m app.core.agentic_framework.evaluation.scripts.generate_tasks \
    --category portfolio_construction \
    --count 40 \
    --output tasks/datasets/portfolio_construction.yaml

# Run evaluation on CIO Agent
python -m app.core.agentic_framework.evaluation.scripts.run_evaluation \
    --agent CIOAgent \
    --categories portfolio_construction,risk_analysis \
    --max-tasks 20

# Analyze results and generate improvement suggestions
python -m app.core.agentic_framework.evaluation.scripts.analyze_results \
    --run-id eval_20241014_120000 \
    --suggest-improvements

# Compare two evaluation runs
python -m app.core.agentic_framework.evaluation.scripts.compare_runs \
    --baseline eval_20241014_120000 \
    --improved eval_20241015_120000
```

### 11.5 Configuration Example

```yaml
# config/evaluation_config.yaml

evaluation:
  max_iterations: 20              # Max agent iterations per task
  timeout_seconds: 300            # Task timeout
  save_transcripts: true          # Save full agent conversations
  parallel_tasks: false           # Run tasks in parallel (future)

metrics:
  accuracy_threshold: 0.85        # Target accuracy
  tool_error_threshold: 0.05      # Max acceptable tool error rate
  max_tokens_per_task: 50000      # Token efficiency target
  max_tools_per_task: 8           # Tool efficiency target

llm:
  model: "claude-sonnet-4"        # For LLM-as-judge scoring
  temperature: 0.0                # Deterministic evaluation
  max_tokens: 4000

output:
  results_dir: "results/runs"
  save_format: ["json", "markdown"]
  include_transcripts: true
```

---

## 12. Integration with Existing Codebase

### 12.1 Minimal Changes Required

The evaluation framework is designed as a **standalone module** that requires minimal changes to existing agent code:

1. **No Agent Modifications**: `BaseAgent` and specialized agents (CIO, CRO) remain unchanged
2. **Non-Invasive Tracking**: `ToolTrackingWrapper` intercepts tool calls via function wrapping
3. **Isolated Directory**: All evaluation code lives in `evaluation/` subdirectory
4. **Optional Dependency**: Evaluation can be excluded from production deployments

### 12.2 Reusable Components

The evaluation framework leverages existing ProphitAI infrastructure:

- **Task Models**: Reuses Pydantic pattern from `base_agent/tasks/models.py`
- **Agent Execution**: Uses standard `agent.run()` method
- **Tool Registration**: Works with existing tool registration system
- **Configuration**: Follows YAML config pattern used elsewhere

### 12.3 Future Extensions

Once core evaluation is working:

1. **Continuous Monitoring**: Add production agent monitoring
2. **A/B Testing**: Compare different prompt strategies or tool configurations
3. **Regression Testing**: Prevent tool performance degradation
4. **Multi-Agent Evaluation**: Evaluate agent collaboration workflows
5. **Backtesting Integration**: Evaluate agents on historical market scenarios
