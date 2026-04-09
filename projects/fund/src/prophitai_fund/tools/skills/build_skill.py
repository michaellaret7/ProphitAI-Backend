"""Skill creation tool for fund agents.

Writes a new markdown skill file to the agent's skills directory. The directory
path is pre-bound via functools.partial — the LLM sees only the skill metadata
and content parameters.
"""

from pathlib import Path

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_shared.time_utils import get_utc_date_str


# ================================
# --> Tools
# ================================


@agent_tool(name="build_skill")
def build_skill(
    _skills_dir: Path,
    skill_name: str,
    title: str,
    description: str,
    content: str,
) -> str:
    """
    Create a new skill file in your skills directory. Skills are structured
    markdown guides that define how to perform a specific repeatable task —
    step-by-step procedures, code templates, pitfalls, and confirmed patterns.

    Use this when you discover a procedure that required significant effort
    and would save time on future runs. The skill will be available via
    load_skill() on all subsequent runs.

    Fails if the skill already exists — use edit_skill() to update an existing skill.

    Args:
        _skills_dir: Absolute path to the agent's skills directory (pre-bound).
        skill_name: Filename for the skill (without .md extension). Use snake_case
            (e.g. 'custom_indicator_from_fundamentals', 'multi_output_indicator').
        title: Human-readable title for the skill.
        description: One-line description of when to use this skill. Include trigger
            keywords so you know when to load it on future runs.
        content: Full markdown body of the skill. Should include sections like
            When to Use, Procedure, Code Template, Pitfalls, Confirmed Patterns.

    Returns:
        Confirmation with the skill name and file path.

    Examples:
        build_skill(
            skill_name="custom_indicator_from_fundamentals",
            title="Building Custom Indicators from Fundamental Data",
            description="Use when manifest has a custom indicator that joins point-in-time fundamental data",
            content="# Building Custom Indicators from Fundamental Data\\n\\n## When to Use\\n..."
        )
    """
    try:
        _skills_dir.mkdir(parents=True, exist_ok=True)

        skill_file = _skills_dir / f"{skill_name}.md"

        if skill_file.exists():
            return error_response(
                f"Skill '{skill_name}' already exists. Use edit_skill() to update it."
            )

        date = get_utc_date_str()

        file_content = (
            f"---\n"
            f"name: {skill_name}\n"
            f"title: {title}\n"
            f"description: {description}\n"
            f"created: {date}\n"
            f"updated: {date}\n"
            f"---\n\n"
            f"{content}\n"
        )

        skill_file.write_text(file_content, encoding="utf-8")

        return success_response({
            "skill": skill_name,
            "title": title,
            "file": str(skill_file),
            "created": date,
        })

    except Exception as e:
        return error_response(f"Failed to build skill: {e}")
