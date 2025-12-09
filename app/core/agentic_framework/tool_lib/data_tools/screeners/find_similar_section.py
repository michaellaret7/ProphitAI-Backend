from difflib import get_close_matches
from typing import Set

def find_similar_sections(
    user_inputs: list[str],
    valid_sections: Set[str],
    n_suggestions: int = 3,
    cutoff: float = 0.4
) -> dict[str, list[str]]:
    """
    Find similar valid sections for user-provided inputs that don't match exactly.

    Args:
        user_inputs: List of user-provided section names (sectors, industries, etc.)
        valid_sections: Set of valid section names from the database
        n_suggestions: Max number of suggestions to return per invalid input
        cutoff: Minimum similarity score (0-1) for a match to be considered

    Returns:
        Dict mapping invalid inputs to lists of similar valid sections.
        Empty dict if all inputs are valid.
    """
    suggestions = {}
    valid_list = list(valid_sections)

    for user_input in user_inputs:
        if user_input not in valid_sections:
            # Reason: Case-insensitive matching improves user experience
            matches = get_close_matches(
                user_input.lower(),
                [v.lower() for v in valid_list],
                n=n_suggestions,
                cutoff=cutoff
            )
            # Reason: Map back to original case from valid_sections
            original_case_matches = [
                v for v in valid_list
                if v.lower() in matches
            ]
            suggestions[user_input] = original_case_matches

    return suggestions

def format_invalid_sections_error(
    field_name: str,
    invalid_values: set[str],
    suggestions: dict[str, list[str]]
) -> str:
    """
    Format a helpful error message with suggestions for invalid section values.

    Args:
        field_name: Name of the field (e.g., 'sectors', 'industries')
        invalid_values: Set of invalid values provided by user
        suggestions: Dict mapping invalid values to suggested alternatives

    Returns:
        Formatted error message string with suggestions
    """
    error_parts = [f"Invalid {field_name}: {invalid_values}"]

    for invalid, matches in suggestions.items():
        if matches:
            error_parts.append(f"  '{invalid}' -> Did you mean: {matches}?")
        else:
            error_parts.append(f"  '{invalid}' -> No similar {field_name} found")

    return "\n".join(error_parts)
