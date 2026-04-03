# Anthropic Python SDK: Structured Output / `.parse()` Method

## Summary

**Yes, the Anthropic Python SDK has a `.parse()` method** that works nearly identically to OpenAI's `client.beta.chat.completions.parse()`. It is available on the **stable** `client.messages` resource (not beta).

- **Installed version in this project:** `anthropic==0.86.0`
- **Method location:** `client.messages.parse(...)`
- **Status:** Stable (not behind a beta namespace)

## How It Works

### Basic Usage

```python
from anthropic import Anthropic
from pydantic import BaseModel

client = Anthropic()

class CalendarEvent(BaseModel):
    name: str
    date: str
    participants: list[str]

response = client.messages.parse(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Extract: Alice and Bob meet Tuesday for lunch"}],
    output_format=CalendarEvent,
)

# Typed access to the parsed Pydantic model
event: CalendarEvent = response.parsed_output
print(event.name)          # "Lunch"
print(event.participants)  # ["Alice", "Bob"]
```

### Key Details

1. **`output_format` parameter** accepts any type that works with `pydantic.TypeAdapter` (Pydantic BaseModel, dataclass, etc.)

2. Under the hood, `.parse()`:
   - Generates a JSON schema from the Pydantic model via `TypeAdapter.json_schema()`
   - Transforms it with `transform_schema()` and wraps it in a `JSONOutputFormatParam`
   - Merges it into the `output_config` parameter sent to the API as `{"format": {"type": "json_schema", "schema": ...}}`
   - Post-processes the response: validates the text output against the Pydantic model using `TypeAdapter.validate_json()`
   - Returns a `ParsedMessage[T]` object

3. **`ParsedMessage[T]`** extends `Message` with:
   - `.parsed_output` property that returns `Optional[T]` - the validated Pydantic model
   - Each `TextBlock` in content becomes a `ParsedTextBlock` with its own `.parsed_output`

4. **Async version** also available: `await client.messages.parse(...)`

5. **All standard `create()` parameters are supported**: `system`, `temperature`, `tools`, `thinking`, `tool_choice`, `top_k`, `top_p`, etc.

## Comparison with OpenAI

| Feature | OpenAI | Anthropic |
|---------|--------|-----------|
| Method | `client.beta.chat.completions.parse()` | `client.messages.parse()` |
| Namespace | Beta | Stable |
| Schema param | `response_format=CalendarEvent` | `output_format=CalendarEvent` |
| Result access | `response.choices[0].message.parsed` | `response.parsed_output` |
| Schema source | Pydantic model | Pydantic model (via TypeAdapter) |

## Impact on This Project

The current `AnthropicBackend.call_llm_structured()` method at `packages/shared/src/prophitai_shared/llm_backends/anthropic_provider.py` uses a manual approach: it serializes the Pydantic schema to JSON, appends it as a system instruction asking the LLM to return JSON, then manually validates the response. This works but is fragile (relies on prompt compliance and text stripping).

The SDK's native `.parse()` method would be a direct replacement that uses the API's built-in JSON schema enforcement, providing guaranteed schema-compliant output without prompt engineering.

### Potential Upgrade

```python
# Current approach (manual prompt + validation)
def call_llm_structured(self, *, messages, target_model, temperature=None):
    schema_json = json.dumps(target_model.model_json_schema())
    json_text = self._create_json_with_instruction(
        messages=messages,
        instruction=f"Return only valid JSON matching this schema exactly...\n{schema_json}",
        temperature=temperature,
    )
    return target_model.model_validate_json(json_text)

# Potential upgrade using SDK .parse()
def call_llm_structured(self, *, messages, target_model, temperature=None):
    system_blocks, anthropic_messages = _to_anthropic_messages(messages)
    response = self.raw_client.messages.parse(
        model=self.model,
        max_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
        system=system_blocks or None,
        messages=anthropic_messages,
        output_format=target_model,
        temperature=temperature,
    )
    return response.parsed_output
```
