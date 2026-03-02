"""Clarification logic for the portfolio builder intake workflow.

Two pure functions:
- generate_clarifying_questions: LLM call to produce context-aware questions
- compose_enriched_brief: deterministic string composition (no LLM)
"""

from typing import List

from app.domain.builder.models import ClarificationResponse, ClarifyAnswer
from app.utils.gpt_parser import parse_with_gpt


# ================================
# --> Helper funcs
# ================================

CLARIFY_SYSTEM_PROMPT = """\
You are a senior portfolio manager conducting an intake interview with a new client.

Your job: read the user's portfolio request carefully, identify what they've already \
told you, and then ask the follow-up questions YOU think are most important for \
actually building this portfolio. There is no fixed checklist — the right questions \
depend entirely on what the user said. Think about what you'd need to know if you \
were sitting across the table from this person and about to allocate real capital.

Analyze the user's request and:
1. Identify what they have ALREADY specified (detected_preferences) — use the user's \
exact words, do not rephrase or summarize.
2. Generate up to 6 follow-up questions that address the biggest gaps in what you'd \
need to build their portfolio. Every question should be directly motivated by \
something in (or missing from) their request.

Rules:
- NEVER re-ask something the user already specified.
- Ask conversationally, like an experienced PM — not like a survey form.
- Probe for specifics: concrete numbers, scenarios, and constraints beat vague \
preference questions.
- NEVER provide multiple-choice options. All questions should be open-ended to \
capture the user's raw, unbiased perspective.
- Use ids "q1", "q2", etc.
- Each question's category field should be a short snake_case label describing \
what dimension it covers (e.g. "time_horizon", "sector_preference", "downside_comfort").
"""


def generate_clarifying_questions(user_preferences: str) -> ClarificationResponse:
    """Analyze a user query and generate context-aware clarifying questions.

    Args:
        user_preferences: Raw user query describing their portfolio request.

    Returns:
        ClarificationResponse with questions and detected_preferences.
    """
    return parse_with_gpt(
        query=user_preferences,
        target_model=ClarificationResponse,
        system_prompt=CLARIFY_SYSTEM_PROMPT,
    )


def compose_enriched_brief(
    original_query: str, answers: List[ClarifyAnswer]
) -> str:
    """Compose an enriched investment brief from the original query and user answers.

    Pure string composition - no LLM call. If no answers are provided,
    returns the original query unchanged (skip path).

    Args:
        original_query: The user's original portfolio request.
        answers: List of answered clarifying questions.

    Returns:
        A structured markdown brief for the PortfolioBuilder prompt.
    """
    if not answers:
        return original_query

    qa_lines = "\n\n".join(
        f"Q: {a.question}\nA: {a.answer}" for a in answers
    )

    return (
        f"{original_query}\n\n"
        f"### Additional Preferences\n"
        f"{qa_lines}"
    )


def run_interactive_clarification(user_query: str) -> str:
    """Run the full clarification flow interactively in the terminal.

    1. Generates clarifying questions via LLM
    2. Prints each question with numbered options (if any)
    3. Collects free-text input for each
    4. Composes and returns the enriched brief

    Args:
        user_query: The user's raw portfolio request.

    Returns:
        Enriched brief string ready for PortfolioBuilder.
    """
    print(f"\nAnalyzing your request: \"{user_query}\"\n")

    result = generate_clarifying_questions(user_query)

    if result.detected_preferences:
        print("Detected preferences:", ", ".join(result.detected_preferences))
        print()

    answers: List[ClarifyAnswer] = []
    for q in result.questions:
        print(f"  {q.question}")
        raw = input("  > ").strip()

        answers.append(ClarifyAnswer(
            question_id=q.id,
            question=q.question,
            answer=raw,
        ))
        print()

    return compose_enriched_brief(user_query, answers)
