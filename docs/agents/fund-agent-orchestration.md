# Fund Agent Orchestration

## Current Reality

- The `fund` package in this repo is an orchestrator and research layer, not the place where strategy Python gets written.
- Today it has two implemented agents:
  - `IdeaGeneratorAgent`: researches and proposes the strategy idea.
  - `StrategyArchitectAgent`: translates that idea into a `StrategyManifest`.
- `Fund.run()` stops after manifest generation. There is no implemented code-writing stage yet.
- The architect prompt already assumes 3 downstream coding agents, but only at prompt level.
- The actual strategy code target is the separate strategies repo scaffold under:
  - `C:\Dev\prophitai-strategies\strategies\template`
  - `C:\Dev\prophitai-strategies\strategies\development`

## Agent Ownership

### IdeaGeneratorAgent

- Owns idea research, macro fit, past-idea avoidance, and strategy thesis.
- Files:
  - `projects/fund/src/prophitai_fund/idea_generation/agent.py`
  - `projects/fund/src/prophitai_fund/idea_generation/tool_registry.py`
  - `projects/fund/src/prophitai_fund/idea_generation/prompts/system.md`

### StrategyArchitectAgent

- Owns manifest generation only. It should not write strategy code.
- Files:
  - `projects/fund/src/prophitai_fund/construction/architect/agent.py`
  - `projects/fund/src/prophitai_fund/construction/architect/models.py`

### Indicator Builder

- Writes the indicator layer in the strategies repo.
- Files:
  - `strategies/<strategy_name>/indicators/suite.py`
  - `strategies/<strategy_name>/indicators/custom.py`
  - `strategies/<strategy_name>/indicators/custom_indicator.py`
- Owns output columns and derived features. This is the column contract for everything downstream.

### Signal + Strategy Builder

- Writes the signal logic and strategy wrapper.
- Files:
  - `strategies/<strategy_name>/signals/model.py`
  - `strategies/<strategy_name>/strategy.py`
  - `strategies/<strategy_name>/config.py` (strategy-facing fields)
- Owns `required_columns`, entry/exit rules, scoring, `min_bars_required`, and any `get_sizing_hints()` overrides.

### Execution Layer Builder

- Writes sizing, risk, and runnable wiring.
- Files:
  - `strategies/<strategy_name>/sizing/policy.py`
  - `strategies/<strategy_name>/risk_controls/defaults.py`
  - `strategies/<strategy_name>/risk_controls/custom_control.py`
  - `strategies/<strategy_name>/wiring.py`
  - `strategies/<strategy_name>/run_event_backtest.py`
  - `strategies/<strategy_name>/run_vectorized_backtest.py`
  - `strategies/<strategy_name>/run_live.py`
- Owns `EntryCandidate` consumption, sizer chain, risk controls, engine wiring, and runnable scripts.

## Dependency Graph

The clean handoff is:

`idea -> manifest -> indicators/features -> signals/strategy -> sizing/risk/wiring`

In practical terms:

1. `IdeaGeneratorAgent` must finish first.
2. `StrategyArchitectAgent` must finish second, because all downstream agents consume the manifest.
3. `Indicator Builder` should start first among the coding agents, because it defines the column contract.
4. `Signal + Strategy Builder` depends on the indicator outputs being real and stable.
5. `Execution Layer Builder` can start partly in parallel, but final sizing and risk wiring often depend on what the strategy publishes through `get_sizing_hints()` and `EntryCandidate`.

## What Can Run In Parallel

### Strictly Sequential

- `IdeaGeneratorAgent` -> `StrategyArchitectAgent`

These cannot be parallelized meaningfully because the architect consumes the idea generator's output.

### Partially Parallel

- `Indicator Builder`
- `Execution Layer Builder`

These can overlap to a point. The execution agent can scaffold config, runners, and base wiring while the indicator agent defines the feature layer.

### Usually Not Safe To Parallelize Early

- `Signal + Strategy Builder`

This agent should usually wait until indicator outputs are frozen, because `required_columns` and signal logic depend on exact column names.

## Hard Contracts

The two main dependency bottlenecks are:

1. Indicator column names
2. The `EntryCandidate` contract between strategy logic and execution

If multiple coding agents are used, one rule should be enforced:

- The indicator agent owns all column names.
- No other agent invents indicator columns independently.

## Recommended Orchestration

For maximum speed without creating merge churn:

1. Phase 1: `IdeaGeneratorAgent` -> `StrategyArchitectAgent`
2. Phase 2: `Indicator Builder` and `Execution Layer Builder` scaffold in parallel
3. Phase 3: `Signal + Strategy Builder` after indicator outputs are frozen
4. Phase 4: `Execution Layer Builder` finalizes sizing, risk, and wiring after the strategy contract is clear

## Current Gap

`projects/fund` does not yet implement the downstream coding agents. The repo currently stops at idea generation plus manifest generation. The screener, code-writing, backtest, testing, and deployment stages are still described conceptually rather than implemented as concrete agents.
