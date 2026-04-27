"""Multi-factor 50-ticker long/short strategy — structured strategy template.

Module layout:

    universe.py          Tickers, sector pairs, data loader.
    alphas/              Custom alpha signals (one file per alpha).
    algorithm.py         Composes alphas + PCM + risk + execution.
    grading.py           Prints metrics + sanity-asserts the backtest.
    run.py               Entry point — ``python ... run.py``.

Every alpha in ``alphas/`` subclasses a base from
``prophitai_algo_trading.alpha_signals.base``. Every concern (universe, signal,
composition, grading) lives in its own file so future agents can drop
new alphas in without touching unrelated code.
"""
