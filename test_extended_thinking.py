"""
Simple test script to demonstrate Extended Thinking feature using Anthropic's native client.

This shows how thinking blocks appear in the API response and how to handle them.
IMPORTANT: Using Anthropic's native client is required to properly access thinking blocks.
"""

import os
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_extended_thinking():
    """Test extended thinking with a simple problem using Anthropic's native client."""

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    # Simple problem that benefits from thinking
    prompt = """
    You are a financial analyst. I have a portfolio with the following stocks:
    - AAPL: 40%
    - MSFT: 35%
    - NVDA: 25%

    Please analyze if this portfolio is well-diversified or if there are concentration risks.
    Think through the sector exposure carefully.
    """

    print("=" * 80)
    print("EXTENDED THINKING TEST (Anthropic Native Client)")
    print("=" * 80)
    print("\nPrompt:")
    print(prompt)
    print("\n" + "=" * 80)

    # Make API call with extended thinking enabled
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        thinking={
            "type": "enabled",
            "budget_tokens": 2000  # How many tokens to allocate for thinking
        },
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print("\n🧠 EXTENDED THINKING ENABLED - Response Structure:\n")

    # Iterate through content blocks
    for i, block in enumerate(response.content):
        print(f"\n--- Content Block {i + 1} ---")
        print(f"Type: {block.type}")

        if block.type == "thinking":
            print("\n💭 THINKING BLOCK (Internal Reasoning):")
            print("-" * 80)
            print(block.thinking)
            print("-" * 80)

        elif block.type == "text":
            print("\n💬 TEXT BLOCK (Final Response):")
            print("-" * 80)
            print(block.text)
            print("-" * 80)

    # Show full response metadata
    print("\n" + "=" * 80)
    print("RESPONSE METADATA")
    print("=" * 80)
    print(f"Model: {response.model}")
    print(f"Stop Reason: {response.stop_reason}")
    print(f"Usage:")
    print(f"  - Input tokens: {response.usage.input_tokens}")
    print(f"  - Output tokens: {response.usage.output_tokens}")
    print("=" * 80)

    # Print raw response for debugging
    print("\n📋 RAW RESPONSE OBJECT:")
    print("-" * 80)
    print(response)
    print("-" * 80)

    return response


def test_without_extended_thinking():
    """Same test but WITHOUT extended thinking for comparison."""

    client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = """
    You are a financial analyst. I have a portfolio with the following stocks:
    - AAPL: 40%
    - MSFT: 35%
    - NVDA: 25%

    Please analyze if this portfolio is well-diversified or if there are concentration risks.
    Think through the sector exposure carefully.
    """

    print("\n\n" + "=" * 80)
    print("NORMAL MODE (NO EXTENDED THINKING) - For Comparison")
    print("=" * 80)

    # Make API call WITHOUT extended thinking
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    print("\n📝 Response (No Thinking Block):")
    print("-" * 80)
    for block in response.content:
        if block.type == "text":
            print(block.text)
    print("-" * 80)

    print(f"\nUsage:")
    print(f"  - Input tokens: {response.usage.input_tokens}")
    print(f"  - Output tokens: {response.usage.output_tokens}")

    # Print raw response for debugging
    print("\n📋 RAW RESPONSE OBJECT:")
    print("-" * 80)
    print(response)
    print("-" * 80)

    return response


if __name__ == "__main__":
    # Test with extended thinking
    response_with_thinking = test_extended_thinking()

    # Test without extended thinking for comparison
    response_without_thinking = test_without_extended_thinking()

    print("\n\n" + "=" * 80)
    print("KEY OBSERVATIONS")
    print("=" * 80)
    print("\n1. WITH Extended Thinking:")
    print("   - Response includes a 'thinking' block showing internal reasoning")
    print("   - Followed by a 'text' block with the final answer")
    print("   - The thinking is NOT shown to end users by default")
    print("   - Uses more tokens but potentially higher quality reasoning")

    print("\n2. WITHOUT Extended Thinking:")
    print("   - Response only includes 'text' block")
    print("   - No visible internal reasoning process")
    print("   - Fewer tokens used")

    print("\n3. Message History Format:")
    print("   - When using extended thinking in multi-turn conversations:")
    print("   - Assistant messages MUST include the thinking block")
    print("   - Format: [{type: 'thinking', thinking: '...'}, {type: 'text', text: '...'}]")
    print("   - If you omit thinking blocks, subsequent API calls will fail!")
    print("=" * 80)