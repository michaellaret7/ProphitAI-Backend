"""HTML/CSS template for PDF generation.

Provides a professional, institutional-grade HTML template that Playwright
renders to PDF. Styled after sell-side equity research reports (Goldman Sachs,
JP Morgan, Morgan Stanley) with muted navy palette, horizontal-only table
rules, right-aligned numbers, and compact information-dense typography.
"""


def build_pdf_html(
    body_html: str,
    title: str | None = None,
    logo_b64: str | None = None,
) -> str:
    """Wrap rendered HTML content in a styled, print-optimized template.

    Args:
        body_html: The agent response already converted from markdown to HTML.
        title: Optional title displayed at the top of the PDF.
        logo_b64: Base64-encoded PNG logo. Embedded as a data URI in the header.

    Returns:
        A complete HTML document string ready for Playwright's page.pdf().
    """
    title_block = f'<h1 class="doc-title">{title}</h1>' if title else ""

    if logo_b64:
        logo_html = f'<img class="logo" src="data:image/png;base64,{logo_b64}" alt="ProphitAI">'
    else:
        logo_html = '<span class="brand">ProphitAI</span>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
    /* ---- Color Palette (Institutional Navy) ---- */
    :root {{
        --navy-900: #0A1628;
        --navy-800: #0F2440;
        --navy-700: #153660;
        --navy-600: #1B4A82;
        --navy-500: #2168A8;
        --navy-200: #B8D4EA;
        --navy-100: #E3EEF7;
        --navy-50:  #F2F7FC;
        --gray-900: #1A1A1A;
        --gray-700: #4A4A4A;
        --gray-600: #6B6B6B;
        --gray-400: #ABABAB;
        --gray-300: #CCCCCC;
        --gray-200: #E5E5E5;
        --gray-100: #F2F2F2;
        --gray-50:  #FAFAFA;
    }}

    /* ---- Base Typography ---- */
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}

    body {{
        font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.45;
        color: var(--gray-900);
        background: #ffffff;
        padding: 0;
        font-feature-settings: 'tnum' 1, 'lnum' 1;
    }}

    /* ---- Accent Bar (top of first page) ---- */
    .accent-bar {{
        height: 3px;
        background: var(--navy-700);
        margin-bottom: 14px;
    }}

    /* ---- Header / Branding ---- */
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 10px;
        margin-bottom: 16px;
        border-bottom: 1px solid var(--gray-300);
    }}

    .logo {{
        height: 28px;
        width: auto;
    }}

    .brand {{
        font-size: 13pt;
        font-weight: 700;
        color: var(--navy-700);
        letter-spacing: 0.3px;
    }}

    /* ---- Document Title ---- */
    .doc-title {{
        font-size: 20pt;
        font-weight: 700;
        color: var(--navy-900);
        margin-bottom: 4px;
        padding-bottom: 8px;
        border-bottom: 2px solid var(--navy-600);
        letter-spacing: -0.01em;
    }}

    /* ---- Headings (Institutional Hierarchy) ---- */

    /* H2: Major section — dark navy background bar */
    h2 {{
        font-size: 12pt;
        font-weight: 700;
        color: #ffffff;
        background: var(--navy-800);
        padding: 6px 12px;
        margin: 22px 0 10px 0;
        letter-spacing: 0.02em;
        page-break-after: avoid;
    }}

    /* H3: Subsection — left accent bar */
    h3 {{
        font-size: 10.5pt;
        font-weight: 700;
        color: var(--navy-800);
        border-left: 3px solid var(--navy-600);
        padding-left: 10px;
        margin: 16px 0 6px 0;
        page-break-after: avoid;
    }}

    /* H4: Minor heading — bottom rule only */
    h4 {{
        font-size: 9.5pt;
        font-weight: 700;
        color: var(--gray-900);
        padding-bottom: 3px;
        border-bottom: 1px solid var(--gray-300);
        margin: 12px 0 5px 0;
        page-break-after: avoid;
    }}

    /* H1: Used only for doc-title, styled above */
    h1 {{
        font-size: 16pt;
        font-weight: 700;
        color: var(--navy-900);
        margin: 18px 0 8px 0;
        page-break-after: avoid;
    }}

    /* ---- Paragraphs & Text ---- */
    p {{
        margin: 6px 0;
    }}

    strong {{ font-weight: 600; }}
    em {{ font-style: italic; }}

    /* ---- Links ---- */
    a {{
        color: var(--navy-500);
        text-decoration: none;
    }}

    /* ---- Lists ---- */
    ul, ol {{
        margin: 6px 0 6px 20px;
        font-size: 9.5pt;
    }}

    li {{
        margin: 2px 0;
        line-height: 1.45;
    }}

    /* ---- Tables (Institutional Financial Style) ---- */
    table {{
        width: 100%;
        border-collapse: collapse;
        margin: 10px 0;
        font-size: 8.5pt;
        font-feature-settings: 'tnum' 1, 'lnum' 1;
    }}

    /* Header row — dark navy, white text */
    thead th {{
        background: var(--navy-700);
        color: #ffffff;
        font-weight: 600;
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        padding: 5px 8px;
        text-align: right;
        border: none;
        border-bottom: 2px solid var(--navy-900);
    }}

    /* First column header left-aligned (row labels) */
    thead th:first-child {{
        text-align: left;
    }}

    /* Data cells — horizontal rules only, NO vertical borders */
    tbody td {{
        padding: 4px 8px;
        text-align: right;
        border: none;
        border-bottom: 0.5px solid var(--gray-200);
        vertical-align: baseline;
    }}

    /* First column left-aligned (row labels) */
    tbody td:first-child {{
        text-align: left;
        font-weight: 500;
        color: var(--gray-900);
    }}

    /* Subtle alternating rows */
    tbody tr:nth-child(even) {{
        background-color: var(--gray-50);
    }}

    /* Prevent table rows from splitting across pages */
    tr {{
        page-break-inside: avoid;
    }}

    /* ---- Code Blocks ---- */
    pre {{
        background: #1a1f2e;
        color: #cdd6f4;
        border-radius: 3px;
        padding: 12px 14px;
        margin: 10px 0;
        overflow-x: auto;
        font-size: 8.5pt;
        line-height: 1.5;
        page-break-inside: avoid;
        border-left: 3px solid var(--navy-600);
    }}

    pre code {{
        background: none;
        padding: 0;
        color: inherit;
        font-size: inherit;
    }}

    /* ---- Inline Code ---- */
    code {{
        background: var(--gray-100);
        color: var(--navy-800);
        padding: 1px 4px;
        border-radius: 2px;
        font-size: 8.5pt;
        font-family: "SF Mono", "Consolas", "Liberation Mono", monospace;
    }}

    /* ---- Blockquotes (Callout Panels) ---- */
    blockquote {{
        border-left: 3px solid var(--navy-600);
        margin: 12px 0;
        padding: 10px 16px;
        background: var(--navy-50);
        color: var(--gray-700);
        font-style: italic;
        font-size: 9.5pt;
        page-break-inside: avoid;
    }}

    /* ---- Horizontal Rules ---- */
    hr {{
        border: none;
        border-top: 1px solid var(--gray-300);
        margin: 14px 0;
    }}

    /* ---- Syntax Highlighting (Pygments) ---- */
    .highlight .k  {{ color: #cba6f7; font-weight: 600; }}
    .highlight .kn {{ color: #cba6f7; font-weight: 600; }}
    .highlight .kd {{ color: #cba6f7; font-weight: 600; }}
    .highlight .s  {{ color: #a6e3a1; }}
    .highlight .s2 {{ color: #a6e3a1; }}
    .highlight .s1 {{ color: #a6e3a1; }}
    .highlight .n  {{ color: #cdd6f4; }}
    .highlight .nf {{ color: #89b4fa; }}
    .highlight .nn {{ color: #f9e2af; }}
    .highlight .nc {{ color: #f9e2af; font-weight: 600; }}
    .highlight .c  {{ color: #6c7086; font-style: italic; }}
    .highlight .c1 {{ color: #6c7086; font-style: italic; }}
    .highlight .mi {{ color: #fab387; }}
    .highlight .mf {{ color: #fab387; }}
    .highlight .o  {{ color: #89dceb; }}
    .highlight .p  {{ color: #cdd6f4; }}
    .highlight .nb {{ color: #f38ba8; }}

    /* ---- Content Area ---- */
    .content {{
        margin-top: 6px;
    }}
</style>
</head>
<body>
    <div class="accent-bar"></div>

    <div class="header">
        <div>
            {logo_html}
        </div>
    </div>

    {title_block}

    <div class="content">
        {body_html}
    </div>
</body>
</html>"""


def build_footer_template() -> str:
    """Build the Playwright footer template with page numbers and branding.

    Rendered by Chrome in the bottom margin of every page. Uses Playwright's
    special CSS classes for automatic page numbering.

    Returns:
        An HTML string for Playwright's footerTemplate parameter.
    """
    return """<div style="width: 100%; font-size: 7px; font-family: Helvetica, Arial, sans-serif;
                          color: #6B6B6B; padding: 0 50px; display: flex;
                          justify-content: space-between; align-items: center;
                          border-top: 1px solid #CCCCCC; padding-top: 6px;">
        <span>ProphitAI Research</span>
        <span style="font-size: 6px; color: #ABABAB;">For authorized recipients only</span>
        <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
    </div>"""
