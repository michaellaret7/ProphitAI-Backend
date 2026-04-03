# LLM API Reference: OpenAI, Anthropic, xAI (2025-2026)

Last updated: 2026-04-02

This document covers the concrete API details for the three LLM providers used in ProphitAI: OpenAI, Anthropic, and xAI/Grok. It focuses on wire formats, SDK patterns, and practical differences relevant to our `LLMBackend` abstraction layer.

---

## 1. OpenAI API

### 1.1 Current Model Lineup (as of April 2026)

| Model Family | Models | Notes |
|---|---|---|
| GPT-5.x | gpt-5.4, gpt-5.4-mini, gpt-5.4-nano, gpt-5.4-pro | Latest flagship. Pro is Responses API only. |
| GPT-5.2 | gpt-5.2 (thinking), gpt-5.2-chat-latest (instant), gpt-5.2-pro | Strong vision, agentic tool calling. |
| o-series | o3, o4-mini | Reasoning models. o4-mini is 128K context, faster than o3-mini. |
| GPT-4o | gpt-4o, gpt-4o-mini | Still available, widely used. |

Key developments:
- GPT-5.4 pro supports `reasoning.effort: medium | high | xhigh`.
- o3/o4-mini were trained with RL to reason about *when* to use tools, not just how.
- Starting with GPT-5.4, tool calling in Chat Completions requires `reasoning: none` to be absent -- the Responses API is preferred for reasoning models.

### 1.2 Two API Primitives: Chat Completions vs Responses API

OpenAI now has two endpoints:

**Chat Completions** (`POST /v1/chat/completions`) -- the one ProphitAI currently uses:
- Conversation state managed manually (you send full message history).
- Response is an array of `choices`, each containing a `message`.
- Still fully supported, no deprecation planned.

**Responses API** (`POST /v1/responses`) -- launched March 2025:
- Supports `previous_response_id` for chaining without resending history.
- Response is an array of `output` items (not `choices`).
- Built-in server-side tools: web search, file search, code interpreter, computer use, remote MCPs.
- Better reasoning model performance (~3% improvement on SWE-bench with same prompt).
- Future innovation lands here first.
- Assistants API will sunset in 2026; Responses API is the long-term replacement.

**Our current approach**: We use Chat Completions via `OpenAICompatibleBackend`. This remains correct for now since we manage our own tool execution loop in Atlas. If we adopt OpenAI's built-in tools or need Responses API features, we would need a new backend method.

### 1.3 Chat Completions Message Format

```python
# System message
{"role": "system", "content": "You are a helpful assistant."}

# User message
{"role": "user", "content": "What is AAPL's P/E ratio?"}

# Assistant message (text only)
{"role": "assistant", "content": "Apple's P/E ratio is..."}

# Assistant message (with tool calls)
{
    "role": "assistant",
    "content": "",  # can be empty or contain text
    "tool_calls": [
        {
            "id": "call_abc123",
            "type": "function",
            "function": {
                "name": "get_pe_ratio",
                "arguments": "{\"ticker\": \"AAPL\"}"  # JSON string, NOT dict
            }
        }
    ]
}

# Tool result message
{
    "role": "tool",
    "tool_call_id": "call_abc123",
    "content": "28.5"  # string content
}
```

Key points:
- `tool_calls[].function.arguments` is a **JSON string**, not a parsed dict.
- `tool_call_id` in the tool response must match the `id` from the assistant's tool call.
- Multiple tool calls can appear in a single assistant message (parallel tool calls).
- The `role` for tool results is `"tool"` (not `"function"` -- that's deprecated).

### 1.4 Tool Definition Format

```python
{
    "type": "function",
    "function": {
        "name": "get_stock_price",          # a-z, A-Z, 0-9, _, - (max 64 chars)
        "description": "Get current price",  # used by model to decide when to call
        "parameters": {                      # JSON Schema object
            "type": "object",
            "properties": {
                "ticker": {
                    "type": "string",
                    "description": "Stock ticker symbol"
                }
            },
            "required": ["ticker"],
            "additionalProperties": false    # required when strict=true
        },
        "strict": true                       # recommended: guarantees schema adherence
    }
}
```

`strict: true` (Structured Outputs for tools):
- Guarantees the model output conforms exactly to the schema.
- Requires `additionalProperties: false` at every object level.
- Requires all fields in `required` array.
- Recommended for all production use.

`tool_choice` parameter options:
- `"auto"` -- model decides (default when tools are provided)
- `"none"` -- model will not call tools
- `"required"` -- model must call at least one tool
- `{"type": "function", "function": {"name": "specific_tool"}}` -- force a specific tool

### 1.5 Structured Outputs / response_format

Three modes:

```python
# 1. JSON mode (unstructured JSON)
response_format={"type": "json_object"}

# 2. JSON Schema mode (structured, guaranteed conformance)
response_format={
    "type": "json_schema",
    "json_schema": {
        "name": "stock_analysis",
        "strict": true,
        "schema": {
            "type": "object",
            "properties": { ... },
            "required": [...],
            "additionalProperties": false
        }
    }
}

# 3. Pydantic via SDK helper (recommended)
from pydantic import BaseModel

class StockAnalysis(BaseModel):
    ticker: str
    recommendation: str
    confidence: float

completion = client.beta.chat.completions.parse(
    model="gpt-4o",
    messages=[...],
    response_format=StockAnalysis,  # SDK converts Pydantic -> JSON Schema
)
result: StockAnalysis = completion.choices[0].message.parsed
```

The SDK's `.parse()` method handles Pydantic-to-JSON-Schema conversion and automatic deserialization. This is what our `OpenAICompatibleBackend.call_llm_structured()` uses.

### 1.6 Streaming

**Chat Completions streaming** (`stream=True`):
- Returns SSE (Server-Sent Events) stream.
- Each chunk has `choices[0].delta` instead of `choices[0].message`.
- Delta contains incremental content: `delta.content` for text, `delta.tool_calls` for tool call chunks.
- Final chunk has `finish_reason` set (e.g., `"stop"`, `"tool_calls"`).

```python
# Basic streaming
stream = client.chat.completions.create(
    model="gpt-4o",
    messages=[...],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta
    if delta.content:
        print(delta.content, end="")

# Structured output streaming
with client.beta.chat.completions.stream(
    model="gpt-4o",
    messages=[...],
    response_format=StockAnalysis,
) as stream:
    for event in stream:
        # Partial parsed object available as stream builds
        pass
    final = stream.get_final_completion()
```

SSE wire format:
```
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":"Hello"},...}]}\n\n
data: {"id":"chatcmpl-xxx","choices":[{"delta":{"content":" world"},...}]}\n\n
data: [DONE]\n\n
```

### 1.7 OpenAI Python SDK Key Classes

```python
from openai import OpenAI, AsyncOpenAI

client = OpenAI(api_key="...", base_url="...")  # base_url for compatible APIs

# Core methods
client.chat.completions.create(...)    # standard completion
client.chat.completions.retrieve(...)  # fetch by ID (new)
client.chat.completions.list(...)      # list with pagination (new)
client.chat.completions.delete(...)    # delete by ID (new)

# Structured output
client.beta.chat.completions.parse(...)   # Pydantic structured output
client.beta.chat.completions.stream(...)  # streaming structured output

# Responses API (new endpoint)
client.responses.create(...)
client.responses.stream(...)

# Key response types
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall
```

---

## 2. Anthropic API

### 2.1 Current Model Lineup (as of April 2026)

| Model | ID | Context | Notes |
|---|---|---|---|
| Claude Opus 4.6 | claude-opus-4-6-20260401 | 1M tokens | Flagship reasoning, full 1M at standard pricing |
| Claude Sonnet 4.6 | claude-sonnet-4-6-20260401 | 1M tokens (beta) | Balanced speed/intelligence, extended thinking |
| Claude Haiku 4.5 | claude-haiku-4-5-20250215 | 200K tokens | Fastest, cost-efficient, strong reasoning |
| Claude Sonnet 4.5 | claude-sonnet-4-5-20250514 | 200K tokens | Previous gen, extended thinking support |

Key developments:
- Opus 4.6 and Sonnet 4.6 support "adaptive thinking" (newer extended thinking).
- Web search tool and programmatic tool calling are now GA (no beta header).
- Token-efficient tool use implementation released.
- Prompt caching switched to workspace-level isolation (Feb 2026).

### 2.2 Messages API Format

**Endpoint**: `POST /v1/messages`

The Anthropic API differs fundamentally from OpenAI in message structure:

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=4096,                    # REQUIRED (OpenAI defaults this)
    system=[                            # system is a TOP-LEVEL parameter, not a message
        {"type": "text", "text": "You are a financial analyst."},
    ],
    messages=[                          # only user and assistant roles
        {"role": "user", "content": "Analyze AAPL"},
        {
            "role": "assistant",
            "content": [                # content is ARRAY OF BLOCKS, not string
                {"type": "text", "text": "I'll analyze Apple..."},
                {
                    "type": "tool_use",
                    "id": "toolu_abc123",
                    "name": "get_stock_data",
                    "input": {"ticker": "AAPL"}  # PARSED DICT, not JSON string
                }
            ]
        },
        {
            "role": "user",             # tool results go in USER messages
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": "toolu_abc123",
                    "content": "Price: $185.50"
                }
            ]
        }
    ],
    tools=[...],
)
```

### 2.3 Critical Differences from OpenAI Message Format

| Aspect | OpenAI | Anthropic |
|---|---|---|
| System prompt | `{"role": "system", "content": "..."}` in messages array | Top-level `system` parameter (array of text blocks) |
| Content format | String | String OR array of typed content blocks |
| Tool call location | `tool_calls` array on assistant message | `tool_use` content blocks inside assistant `content` array |
| Tool call arguments | JSON string (`"arguments": "{\"x\": 1}"`) | Parsed dict (`"input": {"x": 1}`) |
| Tool results | `{"role": "tool", "tool_call_id": "...", "content": "..."}` | `{"role": "user", "content": [{"type": "tool_result", "tool_use_id": "...", "content": "..."}]}` |
| Tool result role | `"tool"` | `"user"` (with tool_result content blocks) |
| max_tokens | Optional (has defaults) | **Required** |
| Thinking blocks | N/A | `{"type": "thinking", "text": "..."}` content blocks |
| Stop reason | `finish_reason: "stop" \| "tool_calls"` | `stop_reason: "end_turn" \| "tool_use"` |

### 2.4 Tool Definition Format

```python
{
    "name": "get_stock_data",
    "description": "Retrieve stock market data for a ticker",
    "input_schema": {            # NOT "parameters" like OpenAI
        "type": "object",
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Stock ticker symbol"
            }
        },
        "required": ["ticker"]
    }
}
```

Note: Anthropic uses `input_schema` where OpenAI uses `parameters`. Our `format_tools()` methods handle this mapping.

Tool categories in Anthropic:
- **Client tools**: User-defined functions (what we use), plus Anthropic-schema tools (bash, text_editor).
- **Server tools**: Run on Anthropic's infrastructure (web_search, code_execution, web_fetch, tool_search). These are new built-in tools similar to OpenAI's Responses API built-ins.

### 2.5 Prompt Caching

Anthropic has explicit prompt caching, which is a major cost optimization:

```python
# Mark content blocks as cacheable with cache_control
{
    "type": "text",
    "text": "Long system prompt...",
    "cache_control": {"type": "ephemeral"}  # cached for 5 minutes
}

# Tools can also be cached (last tool gets cache_control)
tools[-1]["cache_control"] = {"type": "ephemeral"}

# Usage stats include cache info
response.usage.cache_creation_input_tokens  # tokens written to cache
response.usage.cache_read_input_tokens      # tokens read from cache
```

Our `AnthropicBackend` already handles this via `ANTHROPIC_CACHE_POLICY`. Cache breakpoints are set on the last system block and last tool automatically.

As of Feb 2026, caching is workspace-level isolated (not org-level).

### 2.6 Extended Thinking

Extended thinking allows Claude to show its reasoning process:

```python
response = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000,  # max tokens for thinking
    },
    messages=[...],
)

# Response content blocks include thinking
for block in response.content:
    if block.type == "thinking":
        print(f"Thinking: {block.text}")
    elif block.type == "text":
        print(f"Answer: {block.text}")
    elif block.type == "tool_use":
        print(f"Tool call: {block.name}")
```

For Claude Sonnet 4.6 and Opus 4.6, use "adaptive thinking" instead:
```python
thinking={"type": "enabled", "budget_tokens": 10000}  # adaptive by default on 4.6 models
```

Extended thinking works alongside tool use. Thinking blocks get cached when passing tool results back.

**Important**: When `thinking` is enabled, you cannot set `temperature` (must be default 1.0).

### 2.7 Streaming

**Two approaches in the Python SDK:**

```python
# Approach 1: MessageStream (recommended, accumulates final message)
with client.messages.stream(
    model="claude-sonnet-4-5-20250514",
    max_tokens=4096,
    messages=[...],
) as stream:
    for text in stream.text_stream:  # iterate text deltas only
        print(text, end="")
    final_message = stream.get_final_message()

# Approach 2: Raw SSE (lower memory, no accumulation)
stream = client.messages.create(
    model="claude-sonnet-4-5-20250514",
    max_tokens=4096,
    messages=[...],
    stream=True,
)
for event in stream:
    # handle event by type
    pass
```

**SSE Event Types:**
```
message_start          -- contains Message object with metadata, usage
content_block_start    -- new block starting (text, tool_use, or thinking)
content_block_delta    -- incremental content (text_delta, input_json_delta, thinking_delta)
content_block_stop     -- block complete
message_delta          -- stop_reason, final usage
message_stop           -- stream complete
ping                   -- keepalive
```

Fine-grained tool streaming (Sonnet 4.5+) requires header: `fine-grained-tool-streaming-2025-05-14`. Allows streaming tool use parameters without buffering.

### 2.8 Anthropic Python SDK Key Classes

```python
from anthropic import Anthropic, AsyncAnthropic

client = Anthropic(api_key="...")

# Core methods
client.messages.create(...)       # standard message
client.messages.stream(...)       # streaming (returns MessageStreamManager)
client.messages.count_tokens(...) # token counting

# Key response types
from anthropic.types import (
    Message,              # full response
    ContentBlock,         # union of TextBlock, ToolUseBlock, ThinkingBlock
    TextBlock,            # {"type": "text", "text": "..."}
    ToolUseBlock,         # {"type": "tool_use", "id": "...", "name": "...", "input": {...}}
    Usage,                # input_tokens, output_tokens, cache_*
)

# Streaming types
from anthropic.types import (
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockDeltaEvent,
    ContentBlockStopEvent,
    MessageDeltaEvent,
    MessageStopEvent,
)
```

---

## 3. xAI / Grok API

### 3.1 Current Model Lineup (as of April 2026)

| Model | Notes |
|---|---|
| Grok 4.20 | Latest flagship |
| Grok 4.1 Fast | Best agentic tool calling model, reasoning + non-reasoning variants |
| Grok 3 | Previous generation |
| Grok 2 Vision | Vision capabilities (grok-2-vision-1212) |

### 3.2 OpenAI Compatibility

Grok's API is **fully OpenAI-compatible**. You use the OpenAI SDK with a different base URL:

```python
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GROK_API_KEY"),
    base_url="https://api.x.ai/v1",
)

# Exact same API as OpenAI
response = client.chat.completions.create(
    model="grok-4.1-fast",
    messages=[...],
    tools=[...],
)
```

This is exactly how our `OpenAICompatibleBackend` handles it -- same code path as OpenAI, just different `base_url` and `api_key`.

### 3.3 Supported Features

- Chat Completions API (same format as OpenAI)
- Tool/function calling (same schema as OpenAI)
- Structured outputs (Pydantic/Zod, same as OpenAI)
- Streaming (same SSE format as OpenAI)
- Batch API (chat completions, image gen, video gen)
- Responses API support (newer)

### 3.4 Limitations vs OpenAI

1. **Some OpenAI parameters may not be compatible** -- not all parameters from the OpenAI spec are guaranteed to work.
2. **Vision limited to specific models** -- only grok-2-vision-1212 supports image input; multimodal lags behind GPT-4o.
3. **File search requires grok-4 family** and Responses API.
4. **Live Search API deprecated** (Dec 2025) -- replaced by Agent Tools API.
5. **No equivalent to OpenAI's `strict: true`** structured tool calling guarantee (as of last check).
6. **Context window**: Grok 4.1 Fast has 128K context, 8K output limit.

### 3.5 Our Integration

In `choose_model_and_client.py`:
```python
"grok": ProviderConfig("GROK_API_KEY", "GROK_MODEL", "https://api.x.ai/v1")
```

Grok uses `OpenAICompatibleBackend` -- no special handling needed. Everything flows through the same OpenAI wire format.

---

## 4. Key Differences Summary

### 4.1 Message Format

```
OpenAI: roles = system | user | assistant | tool
Anthropic: roles = user | assistant (system is top-level param, tool results are user role)
Grok: same as OpenAI
```

### 4.2 Tool Calling

```
OpenAI:    tool_calls array on message | arguments as JSON string | role "tool" for results
Anthropic: tool_use content blocks     | input as parsed dict    | role "user" with tool_result blocks
Grok:      same as OpenAI
```

### 4.3 Tool Schema

```
OpenAI:    {"type": "function", "function": {"name": ..., "parameters": {...}}}
Anthropic: {"name": ..., "input_schema": {...}}
Grok:      same as OpenAI
```

### 4.4 Streaming

```
OpenAI:    SSE with choices[0].delta | finish_reason in final chunk
Anthropic: SSE with typed events (message_start, content_block_start, *_delta, *_stop)
Grok:      same as OpenAI
```

### 4.5 System Prompts

```
OpenAI:    {"role": "system", "content": "..."} in messages array
Anthropic: system=[ {"type": "text", "text": "..."} ] as top-level parameter
Grok:      same as OpenAI
```

### 4.6 Response Structure

```
OpenAI:    response.choices[0].message.content | .tool_calls | .finish_reason
Anthropic: response.content (list of blocks) | response.stop_reason
Grok:      same as OpenAI
```

### 4.7 Unique Features by Provider

| Feature | OpenAI | Anthropic | Grok |
|---|---|---|---|
| Structured outputs (guaranteed schema) | Yes (`strict: true`, `response_format`) | No native (we use prompt engineering) | Yes (via OpenAI compat) |
| Prompt caching | Automatic (reported in usage) | Explicit (`cache_control` blocks) | Unknown |
| Extended thinking | No (reasoning is in o-series models) | Yes (`thinking` param) | No |
| Built-in web search | Responses API only | Server tool (GA) | Agent Tools API |
| Parallel tool calls | Yes (multiple tool_calls in one message) | Yes (multiple tool_use blocks) | Yes |
| Token-efficient tools | No | Yes (beta) | No |

---

## 5. How ProphitAI Handles These Differences

Our `LLMBackend` abstraction in `packages/shared/src/prophitai_shared/llm_backends/` normalizes all of this:

1. **`NormalizedToolCall`** stores `id`, `name`, `arguments_json` (always a JSON string). Has `.to_openai_dict()` and `.parsed_arguments()` methods.

2. **`NormalizedLLMResponse`** provides `assistant_text`, `tool_calls`, `stop_reason`, `usage` regardless of provider.

3. **`_to_openai_messages()`** converts our internal format to OpenAI wire format.

4. **`_to_anthropic_messages()`** converts our internal format to Anthropic wire format (splitting system blocks, converting tool results to user messages with tool_result blocks).

5. **`format_tools()`** converts canonical tool defs to provider-specific format (OpenAI wraps in `{"type": "function", "function": {...}}`, Anthropic uses `{"name": ..., "input_schema": ...}`).

6. **Prompt caching** is handled automatically by `AnthropicBackend` via `ANTHROPIC_CACHE_POLICY`.

### Internal Message Format (what Atlas uses)

```python
# Our internal format that both backends consume:
{"role": "system", "content": "..."}
{"role": "user", "content": "..."}
{"role": "assistant", "content": "...", "tool_calls": [NormalizedToolCall(...)]}
{"role": "tool", "tool_call_id": "...", "content": "..."}
```

This maps cleanly to OpenAI's format. The Anthropic backend does the heavy lifting of converting system messages to top-level params, tool messages to user-role tool_result blocks, and NormalizedToolCall objects to tool_use content blocks.
