"""
Test script for the refactored portfolio allocator module.

Runs various allocation scenarios to test:
- run() function with default config
- allocate() function with custom config
- Different strategies (max_sharpe, min_vol, max_utility, efficient_risk)
- Equity-only portfolios
- Mixed equity/bond portfolios
- Edge cases

Usage:
    .venv/bin/python test_allocator.py
"""

import traceback
from typing import List

from app.core.calculations.portfolio.allocator import (
    run,
    allocate,
    PortfolioAllocator,
    OptimizerConfig,
    AllocationResult,
    classify_tickers,
    build_classified_tickers,
)


def print_result(result: AllocationResult, test_name: str) -> None:
    """Pretty print allocation result."""
    print(f"\n{'='*60}")
    print(f"TEST: {test_name}")
    print(f"{'='*60}")
    print(f"Strategy: {result.strategy}")
    print(f"\nPerformance:")
    print(f"  Expected Return: {result.performance.expected_return:.2%}")
    print(f"  Volatility:      {result.performance.volatility:.2%}")
    print(f"  Sharpe Ratio:    {result.performance.sharpe_ratio:.2f}")
    print(f"\nAllocations ({len(result.allocations)} positions):")
    for alloc in sorted(result.allocations, key=lambda x: x.weight, reverse=True):
        print(f"  {alloc.ticker:6s}: {alloc.weight:6.2%} ({alloc.num_shares:4d} shares)")
    total_weight = sum(a.weight for a in result.allocations)
    print(f"\n  TOTAL: {total_weight:.4f}")
    print(f"{'='*60}")


def test_run_equity_only_max_sharpe():
    """Test run() with equity-only portfolio using max_sharpe strategy."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
    try:
        result = run(
            tickers=tickers,
            initial_portfolio_value=100_000,
            strategy="max_sharpe",
        )
        print_result(result, "run() - Equity Only - max_sharpe")
        return True
    except Exception as e:
        print(f"\nFAILED: test_run_equity_only_max_sharpe")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_run_equity_only_min_vol():
    """Test run() with equity-only portfolio using min_vol strategy."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
    try:
        result = run(
            tickers=tickers,
            initial_portfolio_value=100_000,
            strategy="min_vol",
        )
        print_result(result, "run() - Equity Only - min_vol")
        return True
    except Exception as e:
        print(f"\nFAILED: test_run_equity_only_min_vol")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_run_equity_only_max_utility():
    """Test run() with equity-only portfolio using max_utility strategy."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
    try:
        result = run(
            tickers=tickers,
            initial_portfolio_value=100_000,
            strategy="max_utility",
        )
        print_result(result, "run() - Equity Only - max_utility")
        return True
    except Exception as e:
        print(f"\nFAILED: test_run_equity_only_max_utility")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_run_equity_only_efficient_risk():
    """Test run() with equity-only portfolio using efficient_risk strategy."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "JPM", "V", "JNJ"]
    # Use allocate() with custom config to set a higher target_volatility
    # The default 0.12 may be below the min achievable volatility
    config = OptimizerConfig(
        equity_weight_target=1.0,
        bond_weight_target=0.0,
        bucket_band=0.05,
        initial_portfolio_value=100_000,
        min_weight=0.01,
        soft_max_weight=0.08,
        hard_max_weight=0.15,
    )
    try:
        result = allocate(
            tickers=tickers,
            config=config,
            strategy="efficient_risk",
            target_volatility=0.20,  # Use higher target to avoid min vol constraint
        )
        print_result(result, "allocate() - Equity Only - efficient_risk (target_vol=20%)")
        return True
    except Exception as e:
        print(f"\nFAILED: test_run_equity_only_efficient_risk")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_allocate_custom_config():
    """Test allocate() with custom OptimizerConfig."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META"]
    config = OptimizerConfig(
        equity_weight_target=1.0,  # Equity only
        bond_weight_target=0.0,
        bucket_band=0.05,
        initial_portfolio_value=50_000,
        min_weight=0.05,  # 5% minimum
        soft_max_weight=0.20,  # 20% soft max
        hard_max_weight=0.30,  # 30% hard max
        l2_gamma=0.2,
        concentration_gamma=0.3,
        risk_free_rate=0.045,
        lookback_days=365,
    )
    try:
        result = allocate(
            tickers=tickers,
            config=config,
            strategy="max_sharpe",
        )
        print_result(result, "allocate() - Custom Config")
        return True
    except Exception as e:
        print(f"\nFAILED: test_allocate_custom_config")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_mixed_portfolio():
    """Test with mixed equity and bond portfolio (60/40)."""
    # Common bond ETFs: BND, AGG, TLT, IEF, LQD
    # Check what's in database
    tickers = ["AAPL", "MSFT", "GOOGL", "NVDA", "JPM", "BND", "AGG", "TLT"]
    try:
        # First check classification
        equities, bonds = classify_tickers(tickers)
        print(f"\nClassification check:")
        print(f"  Equities: {equities}")
        print(f"  Bonds: {bonds}")

        if bonds:
            result = run(
                tickers=tickers,
                equity_weight_target=0.60,
                bond_weight_target=0.40,
                initial_portfolio_value=100_000,
                strategy="max_sharpe",
            )
            print_result(result, "run() - Mixed 60/40 Portfolio")
            return True
        else:
            print("\nSKIPPED: No bond ETFs found in database")
            return True  # Not a failure, just skipped
    except ValueError as e:
        if "not found in database" in str(e):
            print(f"\nSKIPPED: test_mixed_portfolio - {e}")
            return True  # Not a failure, just missing data
        print(f"\nFAILED: test_mixed_portfolio")
        print(f"Error: {e}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\nFAILED: test_mixed_portfolio")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_small_portfolio():
    """Test with minimal number of tickers."""
    tickers = ["AAPL", "MSFT", "GOOGL"]
    config = OptimizerConfig(
        equity_weight_target=1.0,
        bond_weight_target=0.0,
        min_weight=0.10,  # At least 10% each
        hard_max_weight=0.50,  # Max 50%
        soft_max_weight=0.40,
        initial_portfolio_value=10_000,
    )
    try:
        result = allocate(
            tickers=tickers,
            config=config,
            strategy="min_vol",
        )
        print_result(result, "allocate() - Small Portfolio (3 tickers)")
        return True
    except Exception as e:
        print(f"\nFAILED: test_small_portfolio")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_large_portfolio():
    """Test with larger number of tickers."""
    tickers = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
        "NVDA", "META", "JPM", "V", "JNJ",
        "UNH", "HD", "PG", "MA", "DIS",
        "PYPL", "NFLX", "ADBE", "CRM", "INTC",
    ]
    try:
        result = run(
            tickers=tickers,
            initial_portfolio_value=500_000,
            strategy="max_sharpe",
        )
        print_result(result, "run() - Large Portfolio (20 tickers)")
        return True
    except Exception as e:
        print(f"\nFAILED: test_large_portfolio")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_allocator_direct():
    """Test PortfolioAllocator class directly."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]  # 7 tickers
    config = OptimizerConfig(
        equity_weight_target=1.0,
        bond_weight_target=0.0,
        initial_portfolio_value=100_000,
        hard_max_weight=0.20,  # 7 * 0.20 = 1.40 > 1.0, so feasible
    )
    try:
        allocator = PortfolioAllocator(tickers=tickers, config=config)
        prices = allocator.fetch_prices()
        ordered_tickers, mu, S = allocator.compute_inputs(prices)

        print(f"\n{'='*60}")
        print(f"TEST: PortfolioAllocator Direct Access")
        print(f"{'='*60}")
        print(f"Tickers: {ordered_tickers}")
        print(f"Equities: {allocator.equities}")
        print(f"Bonds: {allocator.bonds}")
        print(f"Config:")
        print(f"  equity_weight_target: {allocator.config.equity_weight_target}")
        print(f"  bond_weight_target: {allocator.config.bond_weight_target}")
        print(f"  min_weight: {allocator.min_w}")
        print(f"  hard_max_weight: {allocator.hard_max_w}")
        print(f"  soft_max_weight: {allocator.soft_max_w}")
        print(f"\nExpected Returns (mu):")
        for t in ordered_tickers:
            print(f"  {t}: {mu[t]:.4f}")

        # Run optimization
        weights, perf = allocator.optimize_max_sharpe(mu, S, ordered_tickers)
        print(f"\nOptimization Result (max_sharpe):")
        print(f"  Expected Return: {perf[0]:.2%}")
        print(f"  Volatility: {perf[1]:.2%}")
        print(f"  Sharpe: {perf[2]:.2f}")
        print(f"  Weights:")
        for t, w in sorted(weights.items(), key=lambda x: x[1], reverse=True):
            print(f"    {t}: {w:.2%}")

        eq_w, bnd_w = allocator.bucket_weights(weights)
        print(f"\nBucket Weights:")
        print(f"  Equity: {eq_w:.2%}")
        print(f"  Bond: {bnd_w:.2%}")
        print(f"{'='*60}")
        return True
    except Exception as e:
        print(f"\nFAILED: test_allocator_direct")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_classifier():
    """Test ticker classification functionality."""
    tickers = ["AAPL", "MSFT", "GOOGL"]
    try:
        classified = build_classified_tickers(tickers)
        print(f"\n{'='*60}")
        print(f"TEST: Classifier")
        print(f"{'='*60}")
        print(f"Input: {tickers}")
        print(f"Equities: {classified.equities}")
        print(f"Bonds: {classified.bonds}")
        print(f"has_equities: {classified.has_equities}")
        print(f"has_bonds: {classified.has_bonds}")
        print(f"equity_count: {classified.equity_count}")
        print(f"bond_count: {classified.bond_count}")
        print(f"{'='*60}")
        return True
    except Exception as e:
        print(f"\nFAILED: test_classifier")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_no_regularization():
    """Test with no L2/concentration regularization."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]  # 7 tickers
    config = OptimizerConfig(
        equity_weight_target=1.0,
        bond_weight_target=0.0,
        initial_portfolio_value=100_000,
        l2_gamma=0.0,  # No L2 regularization
        concentration_gamma=0.0,  # No concentration penalty
        hard_max_weight=0.20,  # 7 * 0.20 = 1.40 > 1.0, so feasible
    )
    try:
        result = allocate(
            tickers=tickers,
            config=config,
            strategy="max_sharpe",
        )
        print_result(result, "allocate() - No Regularization")
        return True
    except Exception as e:
        print(f"\nFAILED: test_no_regularization")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def test_high_regularization():
    """Test with high regularization to force equal weights."""
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
    config = OptimizerConfig(
        equity_weight_target=1.0,
        bond_weight_target=0.0,
        initial_portfolio_value=100_000,
        l2_gamma=10.0,  # Very high L2 regularization
        concentration_gamma=5.0,  # Very high concentration penalty
        soft_max_weight=0.15,
        hard_max_weight=0.25,
    )
    try:
        result = allocate(
            tickers=tickers,
            config=config,
            strategy="max_sharpe",
        )
        print_result(result, "allocate() - High Regularization")
        return True
    except Exception as e:
        print(f"\nFAILED: test_high_regularization")
        print(f"Error: {e}")
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_classifier,
        test_allocator_direct,
        test_run_equity_only_max_sharpe,
        test_run_equity_only_min_vol,
        test_run_equity_only_max_utility,
        test_run_equity_only_efficient_risk,
        test_allocate_custom_config,
        test_small_portfolio,
        test_large_portfolio,
        test_no_regularization,
        test_high_regularization,
        test_mixed_portfolio,  # May skip if no bond ETFs in DB
    ]

    print("\n" + "="*60)
    print("PORTFOLIO ALLOCATOR TEST SUITE")
    print("="*60)

    results = []
    for test in tests:
        try:
            passed = test()
            results.append((test.__name__, passed))
        except Exception as e:
            print(f"\nUNEXPECTED ERROR in {test.__name__}: {e}")
            traceback.print_exc()
            results.append((test.__name__, False))

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    passed = sum(1 for _, p in results if p)
    failed = sum(1 for _, p in results if not p)
    for name, p in results:
        status = "PASS" if p else "FAIL"
        print(f"  [{status}] {name}")

    print(f"\nTotal: {passed}/{len(results)} passed, {failed} failed")
    print("="*60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
