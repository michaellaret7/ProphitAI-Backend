"""Shared test utilities for prophitai_tools testing."""

import time

import yaml


def parse_result(yaml_str: str) -> dict:
    """Parse a YAML response string from an agent tool."""
    return yaml.safe_load(yaml_str)


def assert_success(result: dict, label: str) -> dict:
    """Assert the tool returned success and print a data preview."""
    assert result["success"] is True, f"{label}: expected success=True, got {result}"
    data = result.get("data")
    preview = str(data)[:200] if data else "<empty>"
    print(f"  [OK] {label} — preview: {preview}")
    return data


def assert_error(result: dict, label: str) -> str:
    """Assert the tool returned an error."""
    assert result["success"] is False, f"{label}: expected success=False, got {result}"
    error = result.get("error", "")
    print(f"  [OK] {label} — error: {error[:150]}")
    return error


def run_test(name: str, fn):
    """Run a test function, track timing, return (name, status, message)."""
    print(f"\n--- {name} ---")
    t0 = time.time()
    try:
        fn()
        elapsed = time.time() - t0
        print(f"  PASS ({elapsed:.2f}s)")
        return (name, "PASS", f"{elapsed:.2f}s")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  FAIL ({elapsed:.2f}s): {e}")
        return (name, "FAIL", str(e))


def print_summary(results: list[tuple]):
    """Print final pass/fail/skip summary."""
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    passes = sum(1 for _, s, _ in results if s == "PASS")
    fails = sum(1 for _, s, _ in results if s == "FAIL")
    skips = sum(1 for _, s, _ in results if s == "SKIP")
    for name, status, msg in results:
        icon = {"PASS": "[OK]", "FAIL": "[X]", "SKIP": "[~]"}.get(status, "[?]")
        print(f"  {icon} {name}: {msg}")
    print(f"\nTotal: {passes} passed, {fails} failed, {skips} skipped")
    print("=" * 60)
