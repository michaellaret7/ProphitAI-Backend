"""Build a summary of available skills from frontmatter metadata."""

from pathlib import Path


SKILLS_DIR = Path(__file__).parent


def build_skills_summary() -> str:
    """Parse skill frontmatter from the skills directory into a summary block.

    Reads all .md files, extracts name and description from YAML frontmatter,
    and returns a formatted summary for injection into the agent's system prompt.
    """
    entries = []

    for path in sorted(SKILLS_DIR.glob("*.md")):
        text = path.read_text()

        # Reason: extract YAML frontmatter between --- delimiters
        if not text.startswith("---"):
            continue

        end = text.index("---", 3)
        frontmatter = text[3:end].strip()

        name = ""
        description = ""

        for line in frontmatter.splitlines():
            if line.startswith("name:"):
                name = line.split(":", 1)[1].strip()
            elif line.startswith("description:"):
                description = line.split(":", 1)[1].strip()

        if name and description:
            entries.append(f"- **{name}**: {description}")

    if not entries:
        return ""

    return "## Available Skills\n\nLoad these via load_skill(name) for detailed guidance.\n\n" + "\n".join(entries)
