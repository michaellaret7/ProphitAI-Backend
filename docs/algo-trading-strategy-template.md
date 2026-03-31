# Algo Trading Strategy Template

The canonical strategy scaffold lives in the `prophitai-strategies` repo at `strategies/templates/`.

Purpose:

- Keep one source of truth for how agent-authored strategies should be structured.
- Give the coding agent a stable folder shape to generate new strategies from.
- Separate strategy logic from engine, sizing, and risk-control plumbing.

Package shape:

- `config.py`: strategy, sizing, risk, backtest, and live runner defaults
- `strategy.py`: concrete `BaseComposableStrategy` implementation
- `wiring.py`: factories for strategy, engines, broker, sizer, risk controls, and backtest data loading
- `run_event_backtest.py`: real-data event-driven runner
- `run_vectorized_backtest.py`: real-data vectorized runner
- `run_live.py`: live/paper runner
- `indicators/`: shared indicator specs, custom indicator example, and derived feature enrichment
- `signals/`: signal model with entry/exit logic
- `risk_controls/`: shared and custom execution-layer controls
- `sizing/`: strategy-local sizing policy

Usage rule:

- Treat `templates/` as scaffold-only — never run it as a production strategy.
- New strategies go into `strategies/development/` or `strategies/production/`.
- Copy the template folder, rename `Template` to the strategy name, and customize the logic.
