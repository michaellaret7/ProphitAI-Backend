"""
Regex patterns and marker phrases for earnings call transcript parsing.

These patterns detect structural elements in earnings call transcripts such as:
- Speaker labels
- Operator question introductions
- Q&A session markers
- Media section markers
- Closing statements
- Safe harbor disclaimers
"""

from __future__ import annotations

import re


# Speaker label lines are usually: "Operator: ..." or "Robert Isom: ..."
# We intentionally allow punctuation and some symbols used in names.
SPEAKER_LINE_RE = re.compile(
    r"^(?P<speaker>[A-Za-z][-A-Za-z0-9 .,&'()/]{0,80}):[ \t]*(?P<body>.*)$",
    flags=re.MULTILINE,
)

# Operator question intro variants
OP_Q_INTRO_RE = re.compile(
    r"\b(our\s+(?:first|next)\s+question\s+comes\s+from|"
    r"the\s+(?:first|next)\s+question\s+comes\s+from|"
    r"our\s+next\s+question\s+today\s+will\s+be\s+coming\s+from)\b",
    flags=re.IGNORECASE,
)

# Transition into Q&A (sometimes said before the first question intro)
QNA_START_RE = re.compile(
    r"\b(question[- ]and[- ]answer\s+session|"
    r"we\s+will\s+now\s+(?:begin|open)\s+(?:the\s+)?q\s*&\s*a|"
    r"open\s+the\s+line\s+for\s+questions)\b",
    flags=re.IGNORECASE,
)

MEDIA_START_RE = re.compile(
    r"\b(media\s+questions)\b",
    flags=re.IGNORECASE,
)

CLOSING_RE = re.compile(
    r"\b(this\s+concludes|concludes\s+today['']s\s+conference\s+call|"
    r"thank\s+you\s+for\s+participating\b)\b",
    flags=re.IGNORECASE,
)

SAFE_HARBOR_RE = re.compile(
    r"\b(forward[- ]looking\s+statements|safe\s+harbor|non-?gaap)\b",
    flags=re.IGNORECASE,
)

# Extract questioner from operator intro lines like:
# "Our first question comes from the line of Scott Group of Wolfe Research."
QUESTIONER_RE = re.compile(
    r"from\s+the\s+line\s+of\s+(?P<name>[^\n]+?)(?:\.|$)",
    flags=re.IGNORECASE,
)
