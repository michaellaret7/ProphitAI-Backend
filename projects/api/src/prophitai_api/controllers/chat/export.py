"""Chat export controllers — PDF generation from agent responses."""

from typing import Any, Dict, Optional

from prophitai_api.services.pdf.pdf_service import pdf_service
from prophitai_api.utils.decorators import handle_controller_errors


@handle_controller_errors
async def export_pdf_controller(content: str, title: Optional[str] = None) -> bytes:
    """Convert markdown content to a branded PDF.

    Args:
        content: Markdown content from an agent response.
        title: Optional title displayed at the top of the PDF.

    Returns:
        PDF file contents as bytes.
    """
    return await pdf_service.generate_pdf(markdown=content, title=title)
