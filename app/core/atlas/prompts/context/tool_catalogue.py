from app.core.atlas.tools.worker_agent.setup import AVAILABLE_TOOLS

def build_tool_catalog() -> str:
    """One-line description per tool for the orchestrator's system prompt."""
    lines = []
    for name in sorted(AVAILABLE_TOOLS):
        desc = AVAILABLE_TOOLS[name].get("description", "")
        short = desc.split(".")[0].strip()
        lines.append(f"- **{name}**: {short}")
    return "\n".join(lines)