# Agent Loop Fix - Final Answer Detection

## Problem

Agent gets stuck in loop outputting the same answer repeatedly because the final answer detection doesn't work.

**Agent Output:**
```
"Final answer — exactly 2 automobile‑sector stock picks..."
```

**Code Check:**
```python
return 'Final Answer:' in content or 'FINAL ANSWER:' in content.upper()
```

**Issue:** Case and punctuation mismatch
- Agent uses "Final answer" (lowercase 'a')
- Agent uses "—" (em dash) not ":" (colon)
- Check requires "Final Answer:" with capital A and colon

## Solution

Make final answer detection **case-insensitive** and **punctuation-flexible**.

### Updated Code

```python
def _is_final_answer(self, response: Dict[str, Any]) -> bool:
    """
    Check if response contains final answer.

    Now case-insensitive and punctuation-flexible.

    Args:
        response: LLM response

    Returns:
        True if contains final answer marker
    """
    content = response.get('content', '').strip()
    if not content:
        return False

    # Case-insensitive check for "final answer" at start of content
    content_lower = content.lower()

    # Check for various forms:
    # - "Final Answer:" or "Final answer:" or "FINAL ANSWER:"
    # - "Final answer —" (with em dash)
    # - Must be at/near start of message (first 50 chars)
    first_part = content_lower[:50]

    return (
        first_part.startswith('final answer') or
        'final answer:' in first_part or
        'final answer —' in first_part or
        'final answer-' in first_part
    )

def _extract_final_answer(self, response: Dict[str, Any]) -> str:
    """
    Extract final answer from response.

    Args:
        response: LLM response with final answer

    Returns:
        Final answer string
    """
    content = response.get('content', '').strip()
    content_lower = content.lower()

    # Find "final answer" marker (case-insensitive)
    if 'final answer' in content_lower:
        # Find the actual position in original content
        marker_pos = content_lower.index('final answer')

        # Skip past "final answer" and any following punctuation (:, —, -, etc.)
        start_pos = marker_pos + len('final answer')

        # Skip punctuation and whitespace
        while start_pos < len(content) and content[start_pos] in ':—-– \n':
            start_pos += 1

        return content[start_pos:].strip()

    # Fallback: return full content if no marker found
    return content
```

## Testing

After fix, verify:
1. Agent stops after outputting final answer (no repeat)
2. Final answer is correctly extracted
3. Works with various formats:
   - "Final Answer:"
   - "FINAL ANSWER:"
   - "Final answer —"
   - "Final answer:"
