"""Skill loading tool for fund agents.

Reads markdown skill files from the agent's skills directory and returns
the content. The directory path is pre-bound via functools.partial.
"""

from pathlib import Path
from typing import Annotated, Optional

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response


# ================================
# --> Tools
# ================================

@agent_tool(name="load_skill")
def load_skill(
    _skills_dir: Path,
    skill_name: Annotated[Optional[str], Param(
        description="Name of a specific skill to load (without .md extension). "
                    "Omit to list all available skills."
    )] = None,
) -> str:
    """
    Load a skill from the skills directory. Skills are structured guides that
    define how to perform a specific task — e.g., writing strategy specs or
    synthesizing research into a thesis.

    Call with no arguments to list available skills. Call with a skill_name
    to load a specific skill's full content.

    Args:
        _skills_dir: Absolute path to the agent's skills directory (pre-bound).
        skill_name: Name of the skill to load (without .md extension).

    Returns:
        List of available skills, or the full content of a specific skill.

    Examples:
        load_skill()
        >>> {"success": True, "data": {"available_skills": ["create_spec", "research_synthesis"]}}

        load_skill(skill_name="create_spec")
        >>> {"success": True, "data": {"skill": "create_spec", "content": "..."}}
    """
    try:
        if not _skills_dir.exists():
            return error_response("Skills directory not found.")

        if skill_name is None:
            available = [
                f.stem for f in sorted(_skills_dir.glob("*.md"))
                if f.read_text().strip()
            ]

            return success_response({"available_skills": available})

        skill_file = _skills_dir / f"{skill_name}.md"

        if not skill_file.exists():
            available = [f.stem for f in sorted(_skills_dir.glob("*.md"))]

            return error_response(
                f"Skill '{skill_name}' not found. Available: {available}"
            )

        content = skill_file.read_text(encoding="utf-8").strip()

        if not content:
            return error_response(f"Skill '{skill_name}' is empty.")

        return success_response({"skill": skill_name, "content": content})

    except Exception as e:
        return error_response(f"Failed to load skill: {e}")
