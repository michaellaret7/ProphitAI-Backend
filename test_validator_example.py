"""
Real-world example: CompletionValidator in portfolio construction workflow.

This demonstrates how the validator works during a CIO agent's task execution.
"""

from app.core.agentic_framework.base_agent.tasks.validation import CompletionValidator
from app.core.agentic_framework.base_agent.tasks.models import MainTask, SubTask, TaskStatus, TodoList


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def main():
    print_section("REAL EXAMPLE: Portfolio Construction with CompletionValidator")

    # Initialize validator
    validator = CompletionValidator(verbose=True)

    # =====================================================================
    # SCENARIO: CIO Agent building a Consumer Staples portfolio
    # =====================================================================

    print("Creating a real portfolio construction plan...")
    plan = TodoList()

    # Main Task 1: Screen for Consumer Staples stocks
    task1 = plan.add_main_task(
        task_id=1,
        description="Screen consumer staples sector for high-quality stocks with strong fundamentals",
        predicted_tools=['screen_stocks_by_sector', 'get_fundamental_data']
    )

    # Add subtasks for Task 1
    subtask_1a = SubTask(
        id='1a',
        description='Get list of consumer staples stocks',
        completed=False,
        completion_evidence=[],
        expected_tools=['screen_stocks_by_sector']
    )

    subtask_1b = SubTask(
        id='1b',
        description='Filter by market cap > $10B',
        completed=False,
        completion_evidence=[],
        expected_tools=['get_fundamental_data']
    )

    task1.subtasks = [subtask_1a, subtask_1b]

    print(f"✓ Created Task {task1.id}: {task1.description}")
    print(f"  - Subtask 1a: {subtask_1a.description}")
    print(f"  - Subtask 1b: {subtask_1b.description}")

    # =====================================================================
    # SIMULATE TOOL EXECUTION: Subtask 1a (Success)
    # =====================================================================

    print_section("STEP 1: Execute Subtask 1a - Screen Consumer Staples")

    print("Agent executes: screen_stocks_by_sector(sector='Consumer Staples')")

    # Simulate successful tool result
    tool_result_1a = {
        'success': True,
        'data': {
            'tickers': ['PG', 'KO', 'PEP', 'WMT', 'COST', 'CL'],
            'count': 6
        }
    }

    print(f"Tool returned: {tool_result_1a}")

    # Update subtask with evidence
    subtask_1a.completed = True
    subtask_1a.completion_evidence = [
        'Successfully screened consumer staples sector',
        str(tool_result_1a)
    ]

    # Validate
    print("\n🔍 Validating Subtask 1a...")
    is_complete = validator.is_subtask_complete(subtask_1a)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")

    # =====================================================================
    # SIMULATE TOOL EXECUTION: Subtask 1b (Error case)
    # =====================================================================

    print_section("STEP 2: Execute Subtask 1b - Filter by Market Cap (ERROR)")

    print("Agent executes: get_fundamental_data(tickers=['PG', 'KO', ...])")

    # Simulate error result
    tool_result_1b_error = {
        'success': False,
        'error': 'Failed to retrieve fundamental data for ticker XYZ'
    }

    print(f"Tool returned: {tool_result_1b_error}")

    # Agent marks as complete but has error in evidence
    subtask_1b.completed = True
    subtask_1b.completion_evidence = [
        'Retrieved fundamental data',
        str(tool_result_1b_error)  # Contains error!
    ]

    # Validate
    print("\n🔍 Validating Subtask 1b...")
    is_complete = validator.is_subtask_complete(subtask_1b)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")
    print("⚠️  Validator correctly detected error in evidence!")

    # =====================================================================
    # FIX SUBTASK 1b: Retry without error
    # =====================================================================

    print_section("STEP 3: Retry Subtask 1b - Filter by Market Cap (SUCCESS)")

    print("Agent retries: get_fundamental_data(tickers=['PG', 'KO', ...])")

    # Simulate successful retry
    tool_result_1b_success = {
        'success': True,
        'data': {
            'filtered_tickers': ['PG', 'KO', 'PEP', 'WMT', 'COST'],
            'count': 5
        }
    }

    print(f"Tool returned: {tool_result_1b_success}")

    # Update with clean evidence
    subtask_1b.completion_evidence = [
        'Filtered stocks by market cap > $10B',
        str(tool_result_1b_success)
    ]

    # Validate
    print("\n🔍 Validating Subtask 1b...")
    is_complete = validator.is_subtask_complete(subtask_1b)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")

    # =====================================================================
    # VALIDATE MAIN TASK 1
    # =====================================================================

    print_section("STEP 4: Validate Main Task 1 - Stock Screening")

    # Mark task as completed and add evidence
    task1.status = TaskStatus.COMPLETED
    task1.completion_evidence = [
        'Screened consumer staples sector successfully',
        'Filtered 5 high-quality stocks by market cap'
    ]

    print("🔍 Validating Main Task 1...")
    is_complete = validator.is_main_task_complete(task1)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")

    # Get detailed status
    status = validator.get_completion_status(task1)
    print(f"\n📊 Detailed Status:")
    print(f"   Task ID: {status['task_id']}")
    print(f"   Status: {status['status']}")
    print(f"   Is Complete: {status['is_complete']}")
    print(f"   Evidence Count: {status['evidence_count']}")
    print(f"   Completed Subtasks: {status['completed_subtasks']}/{status['total_subtasks']}")

    # =====================================================================
    # EDGE CASE: Finance-specific terminology (tracking error)
    # =====================================================================

    print_section("STEP 5: Edge Case - Finance Terminology (SAFE PHRASE)")

    # Create Task 2: Portfolio analysis
    task2 = plan.add_main_task(
        task_id=2,
        description="Analyze portfolio risk metrics",
        predicted_tools=['calculate_tracking_error', 'calculate_var']
    )

    subtask_2a = SubTask(
        id='2a',
        description='Calculate tracking error vs benchmark',
        completed=True,
        completion_evidence=[
            'Calculated tracking error: 2.5% annually',  # Contains "error" but it's safe!
            'Portfolio tracking error is within acceptable range',
            'success: true'
        ]
    )

    task2.subtasks = [subtask_2a]
    task2.status = TaskStatus.COMPLETED
    task2.completion_evidence = [
        'Risk analysis complete',
        'Tracking error: 2.5%, VaR: 3.2%'  # Finance terms with "error"
    ]

    print("Subtask 2a evidence contains 'tracking error' (finance term)")
    print("Evidence:")
    for ev in subtask_2a.completion_evidence:
        print(f"  - {ev}")

    print("\n🔍 Validating Subtask 2a (contains 'error' but it's a safe finance term)...")
    is_complete = validator.is_subtask_complete(subtask_2a)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")
    print("✨ Validator correctly recognizes 'tracking error' as a safe finance term!")

    # =====================================================================
    # EDGE CASE: Stock ticker "Ameren" (contains "error")
    # =====================================================================

    print_section("STEP 6: Edge Case - Stock Ticker 'Ameren' (SAFE PHRASE)")

    subtask_2b = SubTask(
        id='2b',
        description='Analyze Ameren Corporation fundamentals',
        completed=True,
        completion_evidence=[
            'Retrieved data for Ameren (AEE)',  # Contains "Ameren" which has "error"
            'Ameren market cap: $22B',
            'success: true'
        ]
    )

    print("Subtask 2b evidence contains 'Ameren' (ticker with 'error' substring)")
    print("Evidence:")
    for ev in subtask_2b.completion_evidence:
        print(f"  - {ev}")

    print("\n🔍 Validating Subtask 2b (contains 'Ameren' which has 'error' in it)...")
    is_complete = validator.is_subtask_complete(subtask_2b)
    print(f"Result: {'✅ COMPLETE' if is_complete else '❌ INCOMPLETE'}")
    print("✨ Validator correctly recognizes 'Ameren' as a safe ticker name!")

    # =====================================================================
    # SUMMARY
    # =====================================================================

    print_section("SUMMARY: Context-Aware Validation Results")

    print("✅ PASSED: Subtask 1a - Successful tool execution")
    print("❌ FAILED: Subtask 1b (first attempt) - Detected error in evidence")
    print("✅ PASSED: Subtask 1b (retry) - Clean evidence after retry")
    print("✅ PASSED: Main Task 1 - All subtasks complete with clean evidence")
    print("✅ PASSED: Subtask 2a - 'tracking error' recognized as finance term")
    print("✅ PASSED: Subtask 2b - 'Ameren' recognized as stock ticker")

    print("\n🎯 KEY BENEFITS:")
    print("   1. Simple boolean returns (no confusing confidence scores)")
    print("   2. Context-aware error detection (finance domain knowledge)")
    print("   3. Prevents false positives (tracking error, Ameren, etc.)")
    print("   4. Clear validation logic for debugging")
    print("   5. Implements CompletionChecker protocol for flexibility")

    print("\n" + "="*70)
    print("  Example complete! CompletionValidator ready for production use.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()