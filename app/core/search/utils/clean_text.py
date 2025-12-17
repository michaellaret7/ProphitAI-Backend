from typing import Union

def clean_text(text: str) -> str:
    """Clean Unicode special characters from text."""
    if isinstance(text, str):
        # Replace non-breaking spaces and other special spaces with regular space
        text = text.replace('\u202f', ' ')  # Narrow no-break space
        text = text.replace('\u00a0', ' ')  # Non-breaking space
        text = text.replace('\u2009', ' ')  # Thin space
        # Normalize multiple spaces to single space
        text = ' '.join(text.split())
        return text
    return text