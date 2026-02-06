"""PDF generation service using Playwright.

Converts markdown content from agent responses into professionally styled PDFs.
Maintains a persistent browser context to avoid cold-start latency on each request.
"""

import base64
import logging
import re

from botocore.exceptions import ClientError
from markdown_it import MarkdownIt
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

from app.api.controller.foundry.helpers.s3_upload import S3_BUCKET, get_s3_client
from app.services.shared.pdf_template import build_footer_template, build_pdf_html

logger = logging.getLogger(__name__)

# Markdown renderer with table support
_md = MarkdownIt("commonmark").enable("table")

# Pygments formatter (no wrapper <pre> — we handle that in the template)
_formatter = HtmlFormatter(nowrap=True, style="monokai")

# Regex to find fenced code blocks in the rendered HTML and apply syntax highlighting.
# markdown-it-py outputs: <code class="language-python">...</code>
_CODE_BLOCK_RE = re.compile(
    r'<code class="language-(\w+)">(.*?)</code>',
    re.DOTALL,
)


def _highlight_code_blocks(html: str) -> str:
    """Apply Pygments syntax highlighting to fenced code blocks.

    Replaces <code class="language-X">...</code> with highlighted HTML.
    Falls back to plain text if the language isn't recognized.
    """

    def _replace(match: re.Match) -> str:
        lang = match.group(1)
        code = match.group(2)

        # Unescape HTML entities that markdown-it encoded
        code = (
            code.replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
        )

        try:
            lexer = get_lexer_by_name(lang, stripall=True)
        except ClassNotFound:
            try:
                lexer = guess_lexer(code)
            except ClassNotFound:
                return f'<code>{code}</code>'

        highlighted = highlight(code, lexer, _formatter)
        return f'<code class="highlight">{highlighted}</code>'

    return _CODE_BLOCK_RE.sub(_replace, html)


def markdown_to_html(markdown: str) -> str:
    """Convert markdown text to styled HTML with syntax highlighting.

    Args:
        markdown: Raw markdown string from an agent response.

    Returns:
        HTML string with tables rendered and code blocks syntax-highlighted.
    """
    raw_html = _md.render(markdown)
    return _highlight_code_blocks(raw_html)


class PDFService:
    """Generates PDFs from markdown using a persistent Playwright browser.

    Call ``startup()`` once during app initialization and ``shutdown()``
    during teardown. Between those calls, ``generate_pdf()`` reuses the
    same browser context for fast, low-overhead rendering.
    """

    _LOGO_S3_KEY = "logos/full_logo.png"

    def __init__(self) -> None:
        self._playwright = None
        self._browser = None
        self._logo_b64: str | None = None

    async def startup(self) -> None:
        """Launch Playwright and a persistent Chromium instance."""
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)

        # Download logo from S3 once at startup and cache as base64
        try:
            s3 = get_s3_client()
            response = s3.get_object(Bucket=S3_BUCKET, Key=self._LOGO_S3_KEY)
            raw = response["Body"].read()
            self._logo_b64 = base64.b64encode(raw).decode()
            logger.info("PDF service loaded logo from s3://%s/%s", S3_BUCKET, self._LOGO_S3_KEY)
        except ClientError as e:
            logger.warning("Failed to load logo from S3 — PDFs will omit logo: %s", e)

        logger.info("PDF service started — Playwright browser ready")

    async def shutdown(self) -> None:
        """Close browser and Playwright."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("PDF service shut down")

    async def generate_pdf(
        self,
        markdown: str,
        title: str | None = None,
    ) -> bytes:
        """Render a markdown string to a branded PDF document.

        Args:
            markdown: Raw markdown from an agent response.
            title: Optional title printed at the top of the PDF.

        Returns:
            The PDF file contents as bytes.

        Raises:
            RuntimeError: If the service has not been started.
        """
        if self._browser is None:
            raise RuntimeError("PDFService not started — call startup() first")

        body_html = markdown_to_html(markdown)
        full_html = build_pdf_html(body_html, title=title, logo_b64=self._logo_b64)

        footer_html = build_footer_template()

        page = await self._browser.new_page()
        try:
            await page.set_content(full_html, wait_until="networkidle")
            pdf_bytes = await page.pdf(
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template='<span></span>',
                footer_template=footer_html,
                margin={
                    "top": "60px",
                    "bottom": "70px",
                    "left": "50px",
                    "right": "50px",
                },
            )
        finally:
            await page.close()

        return pdf_bytes


# Global singleton — started/stopped by the FastAPI lifespan
pdf_service = PDFService()
