# Algo Trading Strategy Template

The canonical strategy scaffold lives at `packages/algo_trading/src/prophitai_algo_trading/strategies/template/`.

Purpose:

- Keep one package-owned source of truth for how agent-authored strategies should be structured.
- Give downstream strategy repos a stable folder shape to generate into.
- Separate strategy logic from engine, sizing, and risk-control plumbing.

Package shape:

- `config.py`: strategy, sizing, risk, backtest, and live runner defaults
- `strategy.py`: concrete `BaseComposableStrategy` implementation
- `wiring.py`: factories for strategy, engines, broker, sizer, risk controls, and backtest data loading
- `run_event_backtest.py`: real-data event-driven runner
- `run_vectorized_backtest.py`: real-data vectorized runner
- `run_live.py`: live/paper runner
- `indicators/`: shared indicator specs and derived feature enrichment
- `signals/`: signal predicates and the signal model
- `risk_controls/`: opt-in execution-layer controls
- `sizing/`: strategy-local sizing policy

Usage rule:

- Treat `template/` as scaffold-only.
- Do not maintain a second canonical template in another repo.
- Downstream strategy repos should copy or generate from this package-owned scaffold, then edit the generated strategy logic locally.
