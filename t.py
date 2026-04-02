"""Deferred tool loading pattern — only expose full schemas when the LLM discovers them."""

import json
from datetime import datetime, timezone


# ================================
# --> Tool functions
# ================================

def get_weather(city: str, units: str = "fahrenheit") -> dict:
    """Get the current weather for a city."""
    return {"city": city, "temperature": 72, "units": units, "condition": "sunny"}


def add_numbers(a: int, b: int) -> dict:
    """Add two numbers together."""
    return {"result": a + b}


def get_time() -> dict:
    """Return the current UTC time."""
    return {"time": datetime.now(timezone.utc).isoformat()}


# ================================
# --> Tool registry (full schemas, hidden from LLM at boot)
# ================================

TOOL_REGISTRY = {
    "get_weather": {
        "description": "Get the current weather for a city.",
        "function": get_weather,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "Get the current weather for a city.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "city": {
                            "type": "string",
                            "description": "The city to get weather for (e.g., 'New York')",
                        },
                        "units": {
                            "type": "string",
                            "enum": ["fahrenheit", "celsius"],
                            "description": "Temperature units",
                            "default": "fahrenheit",
                        },
                    },
                    "required": ["city"],
                },
            },
        },
    },
    "add_numbers": {
        "description": "Add two numbers together.",
        "function": add_numbers,
        "schema": {
            "type": "function",
            "function": {
                "name": "add_numbers",
                "description": "Add two numbers together.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "a": {"type": "integer", "description": "First number"},
                        "b": {"type": "integer", "description": "Second number"},
                    },
                    "required": ["a", "b"],
                },
            },
        },
    },
    "get_time": {
        "description": "Get the current UTC time.",
        "function": get_time,
        "schema": {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Get the current UTC time.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
    },
}


# ================================
# --> Build the catalogue string for the system prompt
# ================================

def build_catalogue() -> str:
    """Build a name: description catalogue for the system prompt."""
    lines = ["Available tools (call `discover_tools` to load one before using it):"]
    for name, entry in TOOL_REGISTRY.items():
        lines.append(f"  - {name}: {entry['description']}")
    return "\n".join(lines)


# ================================
# --> The only tool exposed at boot
# ================================

def discover_tools(tool_names: list[str]) -> str:
    """Load full schemas for the requested tools so you can call them."""
    found = []
    not_found = []
    for name in tool_names:
        if name in TOOL_REGISTRY:
            found.append(name)
        else:
            not_found.append(name)

    result = {"loaded": found}
    if not_found:
        result["not_found"] = not_found
    return json.dumps(result)


DISCOVER_TOOLS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "discover_tools",
        "description": "Load tool schemas by name so you can call them. You must discover a tool before you can use it.",
        "parameters": {
            "type": "object",
            "properties": {
                "tool_names": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of tool names to load (from the available tools catalogue).",
                },
            },
            "required": ["tool_names"],
        },
    },
}


# ================================
# --> Execution loop
# ================================

if __name__ == "__main__":
    from prophitai_shared.choose_model_and_client import get_model_and_client

    model, client = get_model_and_client(provider="anthropic", model="claude-sonnet-4-6")

    # State: tracks which tools are currently exposed to the LLM
    active_tools: list[dict] = [DISCOVER_TOOLS_SCHEMA]
    active_functions: dict = {"discover_tools": discover_tools}

    catalogue = build_catalogue()
    messages = [
        {"role": "system", "content": f"You are a helpful assistant.\n\n{catalogue}"},
        {"role": "user", "content": "What's the weather in New York?"},
    ]

    print(f"=== System prompt tool catalogue ===\n{catalogue}\n")
    print(f"=== Active tools at boot: {[t['function']['name'] for t in active_tools]} ===\n")

    # Reason: loop until we get a final text response (max 10 iterations for safety)
    for i in range(10):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=active_tools,
        )

        msg = response.choices[0].message
        messages.append(msg)

        # No tool calls — final answer
        if not msg.tool_calls:
            print(f"=== Final Answer (iteration {i + 1}) ===")
            print(msg.content)
            break

        # Process each tool call
        for tool_call in msg.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"[iter {i + 1}] Tool call: {func_name}({func_args})")

            if func_name == "discover_tools":
                # Inject the full schemas into active_tools
                result = discover_tools(**func_args)
                for name in func_args["tool_names"]:
                    if name in TOOL_REGISTRY and name not in active_functions:
                        active_tools.append(TOOL_REGISTRY[name]["schema"])
                        active_functions[name] = TOOL_REGISTRY[name]["function"]
                        print(f"  -> Loaded tool: {name}")

                print(f"  Active tools now: {[t['function']['name'] for t in active_tools]}")

            elif func_name in active_functions:
                result = json.dumps(active_functions[func_name](**func_args))
                print(f"  -> Result: {result}")

            else:
                result = json.dumps({"error": f"Tool '{func_name}' not loaded. Call discover_tools first."})
                print(f"  -> Error: tool not loaded")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result,
            })
