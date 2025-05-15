"""
Utilities for formatting data into human-readable or LLM-friendly formats.
"""

def format_dollar_amount(amount, include_cents=True):
    """
    Format a number as a dollar amount.
    
    Args:
        amount: Number to format
        include_cents: Whether to include cents
        
    Returns:
        str: Formatted dollar amount
    """
    if include_cents:
        return f"${amount:,.2f}"
    else:
        return f"${int(amount):,}"

def format_percentage(value, decimal_places=2):
    """
    Format a number as a percentage.
    
    Args:
        value: Number to format (e.g., 0.15 for 15%)
        decimal_places: Number of decimal places
        
    Returns:
        str: Formatted percentage
    """
    return f"{value * 100:.{decimal_places}f}%"

def format_markdown_table(headers, rows, alignments=None):
    """
    Format data as a Markdown table.
    
    Args:
        headers: List of column headers
        rows: List of rows, where each row is a list of values
        alignments: Optional list of alignments ('left', 'center', 'right')
        
    Returns:
        str: Markdown-formatted table
    """
    if not headers or not rows:
        return ""
    
    # Default to left alignment
    if not alignments:
        alignments = ["left"] * len(headers)
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Add padding
    col_widths = [w + 2 for w in col_widths]
    
    # Create header row
    header_cells = []
    for i, header in enumerate(headers):
        width = col_widths[i]
        if alignments[i] == "left":
            header_cells.append(str(header).ljust(width))
        elif alignments[i] == "center":
            header_cells.append(str(header).center(width))
        else:  # right
            header_cells.append(str(header).rjust(width))
    
    table_lines = [f"| {' | '.join(header_cells)} |"]
    
    # Create separator row
    separator_cells = []
    for i, width in enumerate(col_widths):
        if alignments[i] == "left":
            separator_cells.append(":" + "-" * (width - 1))
        elif alignments[i] == "center":
            separator_cells.append(":" + "-" * (width - 2) + ":")
        else:  # right
            separator_cells.append("-" * (width - 1) + ":")
    
    table_lines.append(f"| {' | '.join(separator_cells)} |")
    
    # Create data rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                width = col_widths[i]
                if alignments[i] == "left":
                    cells.append(str(cell).ljust(width))
                elif alignments[i] == "center":
                    cells.append(str(cell).center(width))
                else:  # right
                    cells.append(str(cell).rjust(width))
        table_lines.append(f"| {' | '.join(cells)} |")
    
    return "\n".join(table_lines) 

def strip_formatting(text):
    """Strip asterisks and hashtags from the output text."""
    if not text:
        return text
    # Remove asterisks
    text = text.replace('*', '')
    # Remove hashtags
    text = text.replace('#', '')
    return text
