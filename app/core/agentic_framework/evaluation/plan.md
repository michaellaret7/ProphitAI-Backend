# Braintrust Integration Plan for ProphitAI Agentic Framework

## Executive Summary

This document outlines a comprehensive strategy for integrating Braintrust (LLM evaluation & observability platform) into the ProphitAI agentic framework. The integration will enable systematic agent performance evaluation, real-time production monitoring, data-driven optimization, and regression testing.

---

## What is Braintrust?

Braintrust is an end-to-end platform for building AI applications that provides:

- **Evaluations**: Systematic testing with datasets, scoring functions, and experiments
- **Tracing**: Nested span tracking for complex workflows (LLM calls, tool executions, agent chains)
- **Prompt Management**: Versioned prompts with A/B testing capabilities
- **Logging**: Production monitoring with real-time insights
- **Datasets**: Versioned test cases for reproducible experiments
- **Scoring**: Built-in and custom scorers, including LLM-as-judge patterns

### Installation
```bash
pip install braintrust
```

### Authentication
```bash
export BRAINTRUST_API_KEY="YOUR_API_KEY"
```

---

## Current State of ProphitAI Agentic Framework

### Strengths
-  Sophisticated planning system (TodoList, MainTask, SubTask)
-  Rich execution traces (iterations, tool calls, observations)
-  Memory systems (domain, episodic, error)
-  Comprehensive logging (MessageLogger ’ agent_messages.json)
-  Multi-LLM support (OpenAI, Claude, Grok)
-  Token accounting and stagnation detection

### Gaps Braintrust Could Fill
- L No systematic evaluation framework
- L No model/prompt comparison mechanism
- L Limited production observability and alerting
- L Tool performance not tracked systematically
- L Agent optimization is manual/ad-hoc
- L No regression testing for agent behavior

---

## Integration Ideas (Ranked by Impact)

### 1. Agent Execution Tracing & Observability PPPPP

**Problem:** Currently, agent runs are logged to JSON files locally. There's no centralized observability, real-time monitoring, or ability to drill into specific tool executions across multiple runs.

**Solution:**
- Wrap the entire `BaseAgent.run()` method in a Braintrust trace
- Create a span for each iteration
- Create child spans for each tool execution
- Log system/user prompts, assistant responses, and tool results
- Track metadata: model, iteration count, task progress, token usage

**Benefits:**
- Visualize entire agent execution flow in Braintrust UI
- Identify bottlenecks (which tools are slow)
- Debug failures by drilling into specific iterations
- Compare different agent runs side-by-side
- Real-time production monitoring

**Implementation Points:**
- `agent.py:447-1061` - Main execution loop
- `logger.py:35-101` - Extend MessageLogger with Braintrust logging

**Example Code:**
```python
from braintrust import traced

@traced
def run_agent_with_tracing(agent):
    with braintrust.start_span(name="agent_execution",
                               input={"user_prompt": agent.user_prompt},
                               metadata={"model": agent.model}):
        result = agent.run()
        return result
```

---

### 2. Systematic Agent Evaluation Framework PPPPP

**Problem:** No way to systematically test agent performance. When you change prompts, models, or max_iterations, you can't measure the impact objectively.

**Solution:**
- Create evaluation datasets for common agent tasks:
  - Portfolio construction scenarios (bearish, bullish, mixed market)
  - Risk analysis tasks
  - Stock screening challenges
- Define scoring functions:
  - Task completion rate
  - Portfolio quality metrics (diversification, expected return)
  - Token efficiency (cost per task)
  - Iteration count to completion
  - Plan adherence (% of tasks completed)
- Run `Eval()` experiments comparing:
  - OpenAI vs Claude vs Grok
  - Different system prompts
  - plan_first=True vs False
  - Different max_iterations settings

**Benefits:**
- Data-driven agent optimization
- Regression testing (detect when changes break agent behavior)
- Confidence in production deployments
- Quantifiable improvements over time

**Implementation Points:**
- Create `app/core/agentic_framework/evaluation/` directory
- Build `eval_cio_agent.py` with portfolio construction test cases
- Define custom scorers in `scorers.py` (portfolio quality, task completion)

**Example Code:**
```python
from braintrust import Eval

Eval(
    name="CIO Agent Portfolio Construction",
    data=lambda: [
        {
            "input": "Build a defensive portfolio for recession scenario",
            "expected": {"diversification": ">0.8", "task_completion": 1.0}
        },
        # More test cases...
    ],
    task=lambda input: run_cio_agent(input),
    scores=[TaskCompletionScorer, PortfolioQualityScorer, TokenEfficiencyScorer]
)
```

---

### 3. Tool Performance Analytics PPPP

**Problem:** No visibility into which tools are working well vs poorly. Tool errors are tracked in `ToolErrorMemory` but not analyzed systematically.

**Solution:**
- Log every tool call as a Braintrust span with:
  - Tool name, arguments, result
  - Success/failure status
  - Latency
  - Error messages (if any)
- Build dashboards showing:
  - Tool success rates over time
  - Average latency per tool
  - Most/least used tools
  - Tools causing most failures
- Use this data to:
  - Optimize slow tools
  - Improve error handling for problematic tools
  - Identify underutilized tools (maybe remove them)

**Benefits:**
- Data-driven tool library optimization
- Proactive error detection
- Better resource allocation (optimize hot paths)

**Implementation Points:**
- `agent.py:600-686` - Tool execution in main loop
- Wrap `self.utilities.execute_tool_safe()` with Braintrust span logging

**Example Code:**
```python
import braintrust
import time

def execute_tool_with_logging(tool_name, args):
    start_time = time.time()
    with braintrust.start_span(
        name=f"tool_{tool_name}",
        input={"tool": tool_name, "args": args}
    ) as span:
        try:
            result = execute_tool(tool_name, args)
            span.log(
                output=result,
                metadata={
                    "success": True,
                    "latency_ms": (time.time() - start_time) * 1000
                }
            )
            return result
        except Exception as e:
            span.log(
                output={"error": str(e)},
                metadata={
                    "success": False,
                    "error_type": type(e).__name__,
                    "latency_ms": (time.time() - start_time) * 1000
                }
            )
            raise
```

---

### 4. Prompt Management & Versioning PPPP

**Problem:** Prompts are hardcoded in Python files. No version control, no A/B testing, no ability to roll back bad prompts.

**Solution:**
- Store all agent prompts in Braintrust:
  - System prompts (from `prompts.py`)
  - Domain memory patterns
  - Task-specific instructions
- Use Braintrust prompt versioning:
  - Load prompts dynamically at runtime
  - Pin production to specific versions
  - Test new prompt versions in staging
- A/B test prompts:
  - 50% of CIO agent runs use prompt v1
  - 50% use prompt v2
  - Compare performance metrics

**Benefits:**
- Rapid prompt iteration without code deploys
- Safe experimentation (easy rollback)
- A/B testing for prompt optimization
- Audit trail of prompt changes

**Implementation Points:**
- `agent.py:32-45` - Agent initialization
- Replace `self.system_prompt = system_prompt` with Braintrust prompt loading

**Example Code:**
```python
import braintrust

# Load prompt from Braintrust
prompt = braintrust.load_prompt("cio_system_prompt")

# Use in agent
agent = BaseAgent(
    system_prompt=prompt.format(),
    user_prompt=user_query,
    model="gpt-4"
)
```

---

### 5. Plan Execution Analytics PPPP

**Problem:** Rich plan execution data exists (TodoList, task progression, completion evidence) but isn't analyzed systematically across runs.

**Solution:**
- Log plan execution metadata to Braintrust:
  - Plan structure (number of main tasks, subtasks)
  - Task completion order and timing
  - Tools used per task
  - Completion confidence scores
  - Task failures and recovery strategies
- Build analytics:
  - Which task patterns complete fastest
  - Which tasks fail most often
  - Optimal task granularity (few big tasks vs many small)
  - Correlation between plan complexity and success rate

**Benefits:**
- Optimize planning strategies
- Identify common failure patterns
- Improve PlanExecutionEngine heuristics

**Implementation Points:**
- `agent.py:619-664` - Plan loading and execution
- `execution_engine.py` - Log plan analytics to Braintrust

**Example Code:**
```python
def log_plan_execution(plan, execution_result):
    braintrust.log(
        input={"plan_structure": plan.model_dump()},
        output=execution_result,
        metadata={
            "total_main_tasks": len(plan.tasks),
            "total_subtasks": sum(len(t.subtasks) for t in plan.tasks),
            "completed_tasks": execution_result["completed_count"],
            "failed_tasks": execution_result["failed_count"],
            "total_iterations": execution_result["iterations"]
        }
    )
```

---

### 6. Memory System Optimization PPP

**Problem:** Three memory systems (domain, episodic, error) exist but their impact on agent performance isn't measured.

**Solution:**
- Create evaluation experiments:
  - Agent with domain memory vs without
  - Different episodic memory recall strategies
  - Error memory effectiveness (does it prevent repeat errors?)
- Log memory interactions to Braintrust:
  - When memories are injected
  - Which memories were used
  - Impact on tool selection and success
- A/B test memory refresh intervals

**Benefits:**
- Quantify ROI of memory systems
- Optimize memory refresh timing
- Identify most/least valuable memories

**Implementation Points:**
- `agent.py:499-519` - Memory refresh logic
- `episodic_memory.py` - Add Braintrust logging

---

### 7. Production Monitoring & Alerting PPPP

**Problem:** No real-time monitoring of production agent runs. Failures are discovered reactively.

**Solution:**
- Stream all production agent runs to Braintrust
- Set up alerts:
  - Agent stagnation detected
  - Task failure rate > threshold
  - Token usage spike
  - Iteration count exceeds expected
  - Tool error rate spike
- Build dashboards:
  - Active agent runs (real-time)
  - Daily success/failure rates
  - Cost tracking (tokens * model pricing)
  - P50/P95/P99 latency

**Benefits:**
- Proactive issue detection
- Reduced downtime
- Cost optimization
- Better user experience

**Implementation Points:**
- `agent.py:534-539` - LLM API calls
- `websocket_router.py` - Stream live updates to Braintrust

---

### 8. Model Comparison & Selection PPPP

**Problem:** Support for OpenAI, Claude, and Grok exists but no data on which performs best for different tasks.

**Solution:**
- Run evaluation suites on all three models:
  - Portfolio construction accuracy
  - Risk analysis quality
  - Token efficiency
  - Speed (latency)
  - Cost per task
- Build model selection logic:
  - Simple tasks ’ cheaper model
  - Complex analysis ’ most capable model
  - Time-sensitive ’ fastest model
- Track model drift over time (do new versions perform differently?)

**Benefits:**
- Optimal cost/performance tradeoff
- Intelligent model routing
- Vendor negotiation leverage (usage data)

**Implementation Points:**
- `agent.py:47-51` - Model selection
- Create `app/core/agentic_framework/evaluation/model_comparison.py`

---

### 9. Dataset Generation from Production PPP

**Problem:** No automated way to capture production agent runs as test cases.

**Solution:**
- Flag high-quality agent runs in production
- Automatically convert to Braintrust datasets:
  - Input: user_prompt, system_prompt, market context
  - Expected output: final portfolio, task completion status
- Use these for:
  - Regression testing
  - Model fine-tuning (future)
  - Evaluation benchmarks

**Benefits:**
- Continuously improving test coverage
- Real-world test cases (not synthetic)
- Capture edge cases automatically

**Implementation Points:**
- `agent.py:1082-1110` - Result generation
- Add Braintrust dataset append logic for successful runs

---

### 10. Scoring Functions for Portfolio Quality PPPP

**Problem:** Agent produces portfolios but quality is assessed manually.

**Solution:**
- Define custom Braintrust scorers:
  - **DiversificationScore**: Measures concentration risk
  - **RiskAdjustedReturnScore**: Sharpe ratio
  - **AlignmentScore**: LLM-as-judge checks if portfolio matches user thesis
  - **ComplianceScore**: Validates constraints (position limits, etc.)
  - **AnalysisQualityScore**: LLM-as-judge rates research depth
- Use in evaluations to compare agent versions

**Benefits:**
- Objective portfolio quality metrics
- Automated quality assurance
- Confidence in agent outputs

**Implementation Points:**
- Create `app/core/agentic_framework/evaluation/scorers.py`
- Integrate with portfolio result models

**Example Code:**
```python
from braintrust import Scorer

class DiversificationScorer(Scorer):
    def score(self, output, expected=None):
        portfolio = output.get("portfolio", [])
        if not portfolio:
            return 0.0

        # Calculate Herfindahl index
        weights = [p.get("allocation", 0) for p in portfolio]
        herfindahl = sum(w**2 for w in weights)
        diversification = 1 - herfindahl

        return {
            "name": "diversification",
            "score": diversification,
            "metadata": {"portfolio_size": len(portfolio)}
        }
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)

**Goal:** Set up basic Braintrust integration with tracing and logging

**Tasks:**
1. Install Braintrust SDK: `pip install braintrust`
2. Create API key and configure environment variable
3. Create `app/core/agentic_framework/integrations/braintrust/` directory structure:
   - `__init__.py`
   - `tracer.py` - Wrapper for agent tracing
   - `logger.py` - Braintrust logging utilities
   - `config.py` - Configuration management
4. Implement basic tracing wrapper for `BaseAgent.run()`
5. Log iterations as spans with metadata
6. Log tool calls as child spans
7. Verify traces appear in Braintrust UI
8. Test with CIO agent on sample portfolio construction task

**Success Criteria:**
-  Agent execution traces visible in Braintrust dashboard
-  Can drill down into individual iterations and tool calls
-  Metadata (model, tokens, task progress) captured correctly

---

### Phase 2: Evaluation Framework (Week 3-4)

**Goal:** Build systematic evaluation infrastructure for agent performance testing

**Tasks:**
1. Create evaluation directory structure:
   - `app/core/agentic_framework/evaluation/`
   - `datasets/` - Test case collections
   - `scorers/` - Custom scoring functions
   - `experiments/` - Evaluation scripts
2. Build initial evaluation dataset (5-10 portfolio construction scenarios):
   - Bullish market scenario
   - Bearish/recession scenario
   - Mixed signals scenario
   - High volatility scenario
   - Sector rotation scenario
3. Implement custom scorers:
   - `TaskCompletionScorer` - Did agent complete all planned tasks?
   - `TokenEfficiencyScorer` - Tokens used per task completed
   - `PortfolioQualityScorer` - Diversification, risk metrics
   - `PlanAdherenceScorer` - % of plan completed successfully
4. Create `eval_cio_agent.py` - First evaluation script
5. Run baseline evaluation on current agent (OpenAI GPT-4)
6. Document baseline metrics
7. Run comparison evaluation: OpenAI vs Claude vs Grok

**Success Criteria:**
-  5+ test cases covering major scenarios
-  4+ custom scorers implemented and validated
-  Baseline metrics documented
-  Model comparison data available

---

### Phase 3: Optimization & Analytics (Week 5-6)

**Goal:** Use Braintrust data to optimize agent performance

**Tasks:**
1. Migrate system prompts to Braintrust prompt management:
   - Upload CIO system prompt
   - Upload domain memory patterns
   - Set up versioning workflow
2. Implement tool performance analytics:
   - Extend tool execution logging with detailed metadata
   - Create dashboard queries for tool metrics
   - Identify top 3 slowest/most error-prone tools
3. Set up A/B testing infrastructure:
   - Implement prompt variant loading
   - Add experiment assignment logic
   - Create comparison reports
4. Build plan execution analytics:
   - Log plan structure and execution flow
   - Analyze task completion patterns
   - Identify failure modes
5. Add memory system effectiveness tracking:
   - Log memory injections and usage
   - Compare runs with/without memory systems
   - Optimize refresh intervals
6. Run optimization experiments:
   - Test different max_iterations values
   - Compare plan_first=True vs False
   - Optimize memory refresh timing

**Success Criteria:**
-  Prompts managed in Braintrust with versioning
-  Tool performance dashboard operational
-  A/B testing framework functional
-  At least 2 optimization insights documented

---

### Phase 4: Production Monitoring (Week 7-8)

**Goal:** Deploy Braintrust to production with monitoring and alerting

**Tasks:**
1. Deploy Braintrust logging to production API endpoints:
   - Wrap production agent calls with tracing
   - Ensure no performance degradation
   - Test with gradual rollout (10% ’ 50% ’ 100%)
2. Configure production alerts:
   - Agent stagnation detected (stuck_count >= threshold)
   - Task failure rate > 20%
   - Token usage > 150k per run
   - Iteration count > 60
   - Tool error rate > 15%
3. Build monitoring dashboards:
   - Real-time active agent runs
   - Daily/weekly success rates
   - Cost tracking (tokens × model pricing)
   - Latency percentiles (P50, P95, P99)
4. Set up automated dataset generation:
   - Flag successful runs with high quality scores
   - Automatically append to evaluation datasets
   - Review and curate monthly
5. Implement continuous evaluation pipeline:
   - Run nightly evaluation suite
   - Compare against baseline
   - Alert on regressions
6. Train team on Braintrust usage:
   - How to use UI for debugging
   - How to interpret evaluation results
   - How to run custom experiments

**Success Criteria:**
-  Production logging deployed with <5% overhead
-  5+ alerts configured and tested
-  Monitoring dashboards accessible to team
-  Automated dataset generation working
-  Continuous evaluation running nightly

---

## Quick Wins (1-3 Days)

If you want to see immediate value without full implementation:

### Quick Win #1: Basic Agent Tracing (1 day)

```python
# In agent.py
import braintrust

def run(self):
    with braintrust.start_span(
        name="agent_execution",
        input={"user_prompt": self.user_prompt},
        metadata={"model": self.model, "max_iterations": self.max_iterations}
    ) as trace:
        # Existing run() logic
        result = self._run_agent_loop()
        trace.log(output=result)
        return result
```

**Impact:** Visualize agent flow in Braintrust UI immediately

---

### Quick Win #2: First Evaluation (2 days)

```python
# In evaluation/eval_cio_agent.py
from braintrust import Eval
from app.domain.prophit_alts.consumer_staples_fund.build_portfolio.cio.agent import CIOAgent

def run_cio_agent(input_data):
    agent = CIOAgent(
        user_prompt=input_data["prompt"],
        model=input_data.get("model", "gpt-4")
    )
    result = agent.run()
    return {
        "portfolio": result.get("portfolio"),
        "iterations": result.get("iterations"),
        "task_completion": result.get("plan_execution", {}).get("progress_summary", {}).get("overall_progress_percentage", 0) / 100
    }

def task_completion_scorer(output, expected=None):
    return output.get("task_completion", 0)

Eval(
    name="CIO Agent - Model Comparison",
    data=lambda: [
        {"input": {"prompt": "Build defensive portfolio for recession", "model": "gpt-4"}},
        {"input": {"prompt": "Build defensive portfolio for recession", "model": "claude-3-opus"}},
        {"input": {"prompt": "Build defensive portfolio for recession", "model": "grok-beta"}},
    ],
    task=run_cio_agent,
    scores=[task_completion_scorer]
)
```

**Impact:** First objective comparison of models

---

### Quick Win #3: Tool Performance Dashboard (1 day)

```python
# In agent.py, wrap tool execution
def execute_tool_with_metrics(self, name, args):
    import time
    start = time.time()

    with braintrust.start_span(name=f"tool_{name}", input={"args": args}) as span:
        try:
            result = self.utilities.execute_tool_safe(name, args)
            success = not (isinstance(result, str) and result.startswith("Error"))
            span.log(
                output=result,
                metadata={
                    "success": success,
                    "latency_ms": (time.time() - start) * 1000,
                    "tool_name": name
                }
            )
            return result
        except Exception as e:
            span.log(
                output={"error": str(e)},
                metadata={
                    "success": False,
                    "latency_ms": (time.time() - start) * 1000,
                    "tool_name": name,
                    "error_type": type(e).__name__
                }
            )
            raise
```

**Impact:** Identify slow/problematic tools immediately

---

## Success Metrics

### Agent Performance
- **Task Completion Rate**: % of agent runs that complete all planned tasks
- **Token Efficiency**: Average tokens per completed task
- **Iteration Count**: Average iterations to completion
- **Plan Adherence**: % of plan tasks completed successfully

### Tool Performance
- **Tool Success Rate**: % of tool calls that succeed (by tool)
- **Tool Latency**: P50/P95/P99 latency per tool
- **Tool Usage**: Count of tool invocations over time
- **Tool Error Rate**: % of tool calls that error (by tool)

### Production Health
- **Agent Success Rate**: % of production runs that complete successfully
- **Average Run Time**: P50/P95/P99 latency for full agent runs
- **Cost per Run**: Average tokens × model pricing
- **Stagnation Rate**: % of runs that hit stagnation detection

### Model Comparison
- **Model Accuracy**: Portfolio quality scores by model
- **Model Cost**: Average cost per task by model
- **Model Speed**: Average latency by model
- **Model Reliability**: Success rate by model

---

## Technical Architecture

### Directory Structure

```
app/core/agentic_framework/
   integrations/
      braintrust/
          __init__.py
          tracer.py           # Agent tracing wrapper
          logger.py            # Logging utilities
          config.py            # Configuration
          spans.py             # Custom span helpers
   evaluation/
      __init__.py
      plan.md                  # This document
      datasets/
         __init__.py
         cio_portfolio.py    # CIO agent test cases
         risk_analysis.py    # Risk analysis test cases
      scorers/
         __init__.py
         task_completion.py
         token_efficiency.py
         portfolio_quality.py
         plan_adherence.py
      experiments/
         __init__.py
         eval_cio_agent.py
         eval_model_comparison.py
         eval_prompt_variants.py
      reports/
          baseline_metrics.md
```

---

## Best Practices

### Tracing
- Create a span for each major operation (iteration, tool call, LLM call)
- Log inputs and outputs for reproducibility
- Include rich metadata (model, tokens, timestamps)
- Use consistent naming conventions (`agent_execution`, `tool_{name}`, `iteration_{i}`)

### Evaluation
- Start with 5-10 high-quality test cases
- Cover diverse scenarios (bullish, bearish, mixed, volatile)
- Use real market data when possible
- Document expected outputs clearly
- Run evaluations before merging major changes

### Scoring
- Define clear, objective metrics
- Use LLM-as-judge for subjective quality assessment
- Normalize scores to 0-1 range
- Document scoring methodology
- Validate scorers with manual reviews

### Production Monitoring
- Log all production runs (but sample if volume is high)
- Set alert thresholds based on baseline + 2 std devs
- Review dashboards daily
- Investigate failures immediately
- Use Braintrust UI for debugging

### Dataset Management
- Version control test cases
- Curate production runs for test coverage
- Remove outdated/invalid test cases
- Balance diversity and representativeness
- Document data sources and creation dates

---

## Cost Considerations

### Braintrust Pricing
- Free tier: 1M traces/month
- Pro tier: $50/month for 10M traces
- Enterprise: Custom pricing

### Additional LLM Costs
- Evaluations will increase LLM API usage
- Budget for nightly eval runs (~$5-20/day depending on test count)
- A/B testing doubles traffic temporarily
- LLM-as-judge scorers add evaluation cost

### Optimization Opportunities
- Use cheaper models for evaluations when appropriate
- Cache evaluation results for unchanged code
- Sample production logging if volume is extremely high
- Use Braintrust's built-in scorers when possible

---

## Risk Mitigation

### Performance Overhead
- **Risk**: Braintrust logging adds latency
- **Mitigation**: Async logging, sampling in production, benchmark before deployment

### Data Privacy
- **Risk**: Sensitive data in traces
- **Mitigation**: Redact PII, use self-hosted Braintrust for sensitive data

### False Alerts
- **Risk**: Alert fatigue from noisy thresholds
- **Mitigation**: Tune thresholds based on baseline, use composite alerts

### Evaluation Validity
- **Risk**: Test cases don't reflect production
- **Mitigation**: Generate datasets from production, periodic manual review

---

## Next Steps

1. **Review and approve this plan** with stakeholders
2. **Set up Braintrust account** and create API key
3. **Assign Phase 1 tasks** to engineering team
4. **Schedule weekly check-ins** to review progress
5. **Document learnings** in this plan as work progresses

---

## Resources

- **Braintrust Documentation**: https://www.braintrust.dev/docs
- **Python SDK Reference**: https://www.braintrust.dev/docs/reference/libs/python
- **Evaluation Guide**: https://www.braintrust.dev/docs/guides/evals
- **Tracing Guide**: https://www.braintrust.dev/docs/guides/tracing
- **Prompt Management**: https://www.braintrust.dev/docs/guides/prompts

---

## Changelog

- **2025-09-30**: Initial plan created based on Braintrust research and ProphitAI framework analysis
