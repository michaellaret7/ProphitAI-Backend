"""Test final answer detection with various formats."""

# Simulate the detection logic
def test_is_final_answer(content: str) -> bool:
    """Test version of _is_final_answer."""
    content = content.strip()
    if not content:
        return False

    content_lower = content.lower()
    first_part = content_lower[:100]

    return (
        first_part.startswith('final answer') or
        'final answer:' in first_part or
        'final answer —' in first_part or
        'final answer-' in first_part or
        'final answer–' in first_part
    )


def test_extract_final_answer(content: str) -> str:
    """Test version of _extract_final_answer."""
    content = content.strip()
    content_lower = content.lower()

    if 'final answer' in content_lower:
        marker_pos = content_lower.index('final answer')
        start_pos = marker_pos + len('final answer')

        while start_pos < len(content) and content[start_pos] in ':—-–— \t\n':
            start_pos += 1

        return content[start_pos:].strip()

    return content


# Test cases
test_cases = [
    "Final Answer: The sky is blue",
    "FINAL ANSWER: The sky is blue",
    "Final answer: The sky is blue",
    "Final answer — The sky is blue",  # Actual from agent
    "Final answer- The sky is blue",
    "Final answer– The sky is blue",
    "Final answer —exactly 2 automobile‑sector stock picks",  # Actual from log
]

print("Testing Final Answer Detection\n" + "=" * 60)

for i, test in enumerate(test_cases, 1):
    detected = test_is_final_answer(test)
    extracted = test_extract_final_answer(test) if detected else "N/A"

    print(f"\nTest {i}:")
    print(f"  Input: {test[:70]}...")
    print(f"  Detected: {detected}")
    print(f"  Extracted: {extracted[:50]}...")

print("\n" + "=" * 60)
print("All tests should show Detected: True")
print("Extracted text should start with 'The sky' or 'exactly'")
