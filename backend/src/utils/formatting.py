"""
Utilities for formatting data into human-readable or LLM-friendly formats.
"""

def strip_formatting(text):
    """Strip asterisks and hashtags from the output text."""
    if not text:
        return text
    # Remove asterisks
    text = text.replace('*', '')
    # Remove hashtags
    text = text.replace('#', '')
    return text
