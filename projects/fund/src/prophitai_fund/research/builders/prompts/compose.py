"""Prompt composer for builder agents.

Reads the agent-specific prompt, appends shared builder sections, then
formats runtime params. Keeps shared content in one file so all builders
stay consistent.
"""

from pathlib import Path


_SHARED_FILE = Path(__file__).parent / "builder_shared.md"


def compose_builder_prompt(
    agent_prompt_path: Path,
    *,
    date: str,
    sandbox_id: str,
) -> str:
    """Compose a builder agent system prompt.

    Appends shared builder sections to the agent-specific prompt,
    then formats runtime params ({date}, {sandbox_id}).
    """
    agent_prompt = agent_prompt_path.read_text()
    shared_sections = _SHARED_FILE.read_text()

    combined = agent_prompt + "\n\n<shared_builder_standards>\n" + shared_sections + "\n</shared_builder_standards>"

    return combined.format(date=date, sandbox_id=sandbox_id)
