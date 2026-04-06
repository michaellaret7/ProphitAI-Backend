"""Past ideas tool for fund agents.

Reads from and writes to a shared past_ideas.md file that tracks
all strategy ideas attempted by the idea generator. The idea agent
writes new ideas; the research agent reads them and appends verdicts.

The file path is pre-bound via functools.partial at agent init time —
the LLM only sees ``operation`` and the relevant content parameters.
"""

from pathlib import Path
from typing import Literal, Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import success_response, error_response
from prophitai_shared.time_utils import get_utc_date_str


# ================================
# --> Helper funcs
# ================================

IDEA_TEMPLATE = """\
---
name: {title}
category: {category}
date: {date}
verdict: {verdict}
---

### Description
{description}

### Edge
{edge}

### Universe
{universe}

### Entry & Exit
{entry_exit}

### Risk Management
{risk_management}

### Research Backing
{research_backing}

"""

PENDING_VERDICT = "pending"


def _format_new_idea(
    title: str,
    category: str,
    description: str,
    edge: str,
    universe: str,
    entry_exit: str,
    risk_management: str,
    research_backing: str,
) -> str:
    """Build a formatted idea entry with YAML frontmatter and structured sections."""

    return IDEA_TEMPLATE.format(
        title=title,
        category=category,
        date=get_utc_date_str(),
        description=description,
        edge=edge,
        universe=universe,
        entry_exit=entry_exit,
        risk_management=risk_management,
        research_backing=research_backing,
        verdict=PENDING_VERDICT,
    )


def _update_verdict(
    content: str,
    title: str,
    verdict: Literal["passed", "failed"],
    research_summary: str,
) -> str:
    """Set the verdict and append research results for a specific idea.

    1. Flips ``verdict: pending`` → ``verdict: passed/failed`` in frontmatter.
    2. Appends a ``### Research Results`` section with the detailed summary.

    Raises:
        ValueError: If the idea or its pending verdict is not found.
    """
    search_marker = f"name: {title}"

    if search_marker not in content:
        raise ValueError(f"Idea '{title}' not found in past ideas file.")

    idea_start = content.index(search_marker)

    # Reason: Scope the replacement to just this idea's section
    # so we don't accidentally touch another idea.
    next_idea = content.find("\n---\nname:", idea_start + len(search_marker))
    idea_end = next_idea if next_idea != -1 else len(content)
    idea_section = content[idea_start:idea_end]

    old_verdict = "verdict: pending"

    if old_verdict not in idea_section:
        raise ValueError(
            f"Idea '{title}' already has a verdict or pending marker not found."
        )

    # Reason: Replace verdict in frontmatter.
    verdict_line = f"verdict: {verdict}"
    placeholder_pos = idea_section.index(old_verdict)
    abs_start = idea_start + placeholder_pos
    abs_end = abs_start + len(old_verdict)

    content = content[:abs_start] + verdict_line + content[abs_end:]

    # Reason: Recalculate idea_end after the content mutation since
    # the verdict string length may have changed.
    next_idea = content.find("\n---\nname:", idea_start + len(search_marker))
    idea_end = next_idea if next_idea != -1 else len(content)

    # Reason: Append research results section at the end of this idea's body.
    research_block = f"### Research Results\n**Evaluated:** {get_utc_date_str()}\n\n{research_summary}\n\n"
    content = content[:idea_end].rstrip("\n") + "\n\n" + research_block + content[idea_end:]

    return content


# ================================
# --> Tools
# ================================

@agent_tool(name="past_ideas")
def past_ideas(
    _ideas_file: Path,
    operation: Literal["read", "write", "update_verdict"],
    title: Optional[str] = None,
    category: Optional[str] = None,
    description: Optional[str] = None,
    edge: Optional[str] = None,
    universe: Optional[str] = None,
    entry_exit: Optional[str] = None,
    risk_management: Optional[str] = None,
    research_backing: Optional[str] = None,
    verdict: Optional[Literal["passed", "failed"]] = None,
    research_summary: Optional[str] = None,
) -> str:
    """
    Manage the shared past strategy ideas log.

    Use this to:
    - READ all past ideas (see what has been tried before and their outcomes)
    - WRITE a new strategy idea you've generated
    - UPDATE_VERDICT to record whether a researched idea passed or failed

    This prevents duplicate strategy generation and tracks research outcomes.

    Args:
        _ideas_file: Absolute path to past_ideas.md (pre-bound, hidden from schema).
        operation: "read" retrieves all past ideas, "write" submits a new idea,
            "update_verdict" records the research outcome on an existing idea.
        title: Title/name of the strategy idea. Required for write and update_verdict.
        category: Strategy category (e.g. momentum, mean-reversion, volatility,
            carry, macro, multi-factor). Required for write.
        description: In-depth description of the overall strategy — what it is,
            the core thesis, why it works, and what market conditions it exploits.
            Required for write.
        edge: The specific signal, anomaly, or factor that drives alpha generation.
            Required for write.
        universe: Target asset characteristics — asset class, market cap range,
            sector tilts, factor exposures, liquidity requirements. Required for write.
        entry_exit: Entry signals, exit signals, rebalancing frequency, and the
            data inputs required to trigger each. Required for write.
        risk_management: Position sizing philosophy, drawdown limits, hedging
            approach, and tail-risk mitigation. Required for write.
        research_backing: Academic citations, empirical evidence, and data supporting
            the thesis. Required for write.
        verdict: Either "passed" or "failed". Required for update_verdict.
        research_summary: Detailed description of all backtests run, ticker and
            risk combinations tried, performance metrics, and the reasoning behind
            the final verdict. Required for update_verdict.

    Returns:
        YAML success/error response with past ideas content or confirmation.

    Examples:
        past_ideas(operation="read")
        past_ideas(operation="write", title="Vol Risk Premium", category="volatility", description="...", edge="...", universe="...", entry_exit="...", risk_management="...", research_backing="...")
        past_ideas(operation="update_verdict", title="Vol Risk Premium", verdict="passed", research_summary="Backtested 2010-2024 across 3 ticker combos...")
    """
    try:
        _ideas_file.touch(exist_ok=True)

        # ---- Read ---- #
        if operation == "read":
            content = _ideas_file.read_text(encoding="utf-8").strip()

            if not content:
                return success_response({"past_ideas": "No past ideas recorded yet."})

            return success_response({"past_ideas": content})

        # ---- Write new idea ---- #
        if operation == "write":
            write_fields = [title, category, description, edge, universe, entry_exit, risk_management, research_backing]

            if not all(write_fields):
                return error_response(
                    "write requires all fields: title, category, description, "
                    "edge, universe, entry_exit, risk_management, research_backing."
                )

            entry = _format_new_idea(
                title, category, description,  # type: ignore[arg-type]
                edge, universe, entry_exit,  # type: ignore[arg-type]
                risk_management, research_backing,  # type: ignore[arg-type]
            )

            with open(_ideas_file, "a", encoding="utf-8") as f:
                f.write(entry)

            return success_response({
                "wrote_idea": title,
                "file": str(_ideas_file),
            })

        # ---- Update verdict on existing idea ---- #
        if operation == "update_verdict":
            if not title or not verdict or not research_summary:
                return error_response(
                    "update_verdict requires 'title', 'verdict', and 'research_summary' fields."
                )

            content = _ideas_file.read_text(encoding="utf-8")
            updated = _update_verdict(content, title, verdict, research_summary)
            _ideas_file.write_text(updated, encoding="utf-8")

            return success_response({
                "updated_idea": title,
                "verdict": verdict,
            })

        return error_response(f"Unknown operation: {operation}")

    except Exception as e:
        return error_response(f"past_ideas failed: {e}")


