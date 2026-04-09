"""Skill editing tool for fund agents.

Updates an existing markdown skill file in the agent's skills directory.
Replaces the content body and optionally the description, while preserving
the skill name and updating the 'updated' timestamp.
"""

from pathlib import Path
from typing import Annotated, Optional

from prophitai_atlas.tools.decorator import agent_tool, Param
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_shared.time_utils import get_utc_date_str


# ================================
# --> Helper funcs
# ================================


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Split a skill file into frontmatter dict and body content."""

    if not text.startswith("---"):
        return {}, text

    parts = text.split("---", 2)

    if len(parts) < 3:
        return {}, text

    meta: dict[str, str] = {}

    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, val = line.split(":", 1)
            meta[key.strip()] = val.strip()

    body = parts[2].strip()

    return meta, body


# ================================
# --> Tools
# ================================


@agent_tool(name="edit_skill")
def edit_skill(
    _skills_dir: Path,
    skill_name: str,
    content: str,
    description: Annotated[Optional[str], Param(
        description="New description for the skill. Leave empty to keep the existing description."
    )] = None,
) -> str:
    """
    Update an existing skill with new content. Use this after a success or
    failure to add confirmed patterns, pitfalls, or improved procedures.

    Replaces the full markdown body while preserving the skill name and
    frontmatter metadata. Optionally updates the description.

    Fails if the skill doesn't exist — use build_skill() to create a new one.

    Args:
        _skills_dir: Absolute path to the agent's skills directory (pre-bound).
        skill_name: Name of the skill to edit (without .md extension).
        content: New full markdown body for the skill. This replaces the
            entire body — include all sections (Procedure, Pitfalls, etc.).
        description: Optional new description. If omitted, keeps the existing one.

    Returns:
        Confirmation with the updated skill metadata.

    Examples:
        edit_skill(
            skill_name="custom_indicator_from_fundamentals",
            content="# Updated content with new pitfall section...",
        )
    """
    try:
        skill_file = _skills_dir / f"{skill_name}.md"

        if not skill_file.exists():
            available = [f.stem for f in sorted(_skills_dir.glob("*.md"))]

            return error_response(
                f"Skill '{skill_name}' not found. Use build_skill() to create it. "
                f"Available: {available}"
            )

        existing_text = skill_file.read_text(encoding="utf-8")
        meta, _ = _parse_frontmatter(existing_text)

        date = get_utc_date_str()

        if description is not None:
            meta["description"] = description

        meta["updated"] = date

        frontmatter_lines = [f"{k}: {v}" for k, v in meta.items()]
        frontmatter = "\n".join(frontmatter_lines)

        file_content = f"---\n{frontmatter}\n---\n\n{content}\n"

        skill_file.write_text(file_content, encoding="utf-8")

        return success_response({
            "skill": skill_name,
            "description": meta.get("description", ""),
            "updated": date,
        })

    except Exception as e:
        return error_response(f"Failed to edit skill: {e}")
