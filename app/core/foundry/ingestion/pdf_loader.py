"""
PDF ingestion module for RAG pipelines.

Handles digital extraction, OCR fallback, and structured output.
Uses PyMuPDF for fast digital extraction and Docling for layout-aware processing.
"""
import logging
import os
import tempfile
from typing import Optional

import pymupdf
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFInfoNotInstalledError
import pytesseract
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)

logger = logging.getLogger(__name__)

MIN_CHARS_PER_PAGE: int = 50
DEFAULT_OCR_LANG: str = "eng"

class PDFHandler:
    """
    PDF extraction handler for RAG pipelines.

    Accepts bytes and extracts text using PyMuPDF (fast) or Docling (high-fidelity).
    For Docling, bytes are written to a temp file since Docling requires a file path.

    Attributes:
        use_ocr: Whether to fall back to OCR for scanned documents.
        ocr_lang: Language code for OCR (default: "eng").
        min_chars_per_page: Minimum characters per page before triggering OCR fallback.
    """

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_lang: str = DEFAULT_OCR_LANG,
        min_chars_per_page: int = MIN_CHARS_PER_PAGE,
    ) -> None:
        """
        Initialize PDFHandler.

        Args:
            use_ocr: Enable OCR fallback for scanned documents.
            ocr_lang: Tesseract language code for OCR.
            min_chars_per_page: Threshold for OCR fallback detection.
        """
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        self.min_chars_per_page = min_chars_per_page
        self._docling_converter: Optional[DocumentConverter] = None

    def extract(self, data: bytes, high_fidelity: bool = False) -> str:
        """
        Extract text from PDF bytes.

        Args:
            data: PDF file content as bytes.
            high_fidelity: Use Docling for layout-aware extraction.

        Returns:
            Extracted text content.

        Raises:
            RuntimeError: If extraction fails.
        """
        if high_fidelity:
            return self._extract_with_docling(data)

        # Fast digital extraction with PyMuPDF
        text, page_count = self._extract_digital(data)

        # Fallback to OCR if digital text is insufficient
        if self._needs_ocr(text, page_count) and self.use_ocr:
            logger.info("Digital extraction insufficient, falling back to OCR")
            text = self._extract_ocr(data)

        return text

    def _extract_digital(self, data: bytes) -> tuple[str, int]:
        """
        Fast extraction using PyMuPDF for selectable text.

        Args:
            data: PDF file content as bytes.

        Returns:
            Tuple of (extracted text, page count).

        Raises:
            RuntimeError: If PyMuPDF extraction fails.
        """
        try:
            doc = pymupdf.open(stream=data, filetype="pdf")
            page_count = len(doc)
            full_text: list[str] = []

            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    full_text.append(f"--- Page {i + 1} ---\n{text}")

            doc.close()

            extracted = "\n".join(full_text)
            logger.debug(f"Digital extraction: {len(extracted)} chars from {page_count} pages")
            return extracted, page_count

        except Exception as e:
            logger.error(f"Digital extraction failed: {e}")
            raise RuntimeError(f"PyMuPDF extraction failed: {e}") from e

    def _extract_ocr(self, data: bytes) -> str:
        """
        Fallback OCR for scanned documents using Tesseract.

        Args:
            data: PDF file content as bytes.

        Returns:
            OCR-extracted text content.

        Raises:
            RuntimeError: If OCR extraction fails.
        """
        logger.info("Running OCR extraction...")

        # Reason: pdf2image requires a file path, so we use a temp file
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
                tmp.write(data)
                tmp.flush()

                pages = convert_from_path(tmp.name)
                text_output: list[str] = []

                for i, page in enumerate(pages):
                    text = pytesseract.image_to_string(page, lang=self.ocr_lang)
                    text_output.append(f"--- Page {i + 1} (OCR) ---\n{text}")

                extracted = "\n".join(text_output)
                logger.debug(f"OCR extraction: {len(extracted)} chars from {len(pages)} pages")
                return extracted

        except PDFInfoNotInstalledError as e:
            logger.error("Poppler not installed - required for pdf2image")
            raise RuntimeError(
                "Poppler is not installed. Install with: brew install poppler (macOS) "
                "or apt-get install poppler-utils (Linux)"
            ) from e
        except PDFPageCountError as e:
            logger.error(f"Failed to get PDF page count: {e}")
            raise RuntimeError(f"Failed to read PDF for OCR: {e}") from e
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            raise RuntimeError(f"OCR extraction failed: {e}") from e

    def _extract_with_docling(self, data: bytes) -> str:
        """
        Advanced extraction preserving layout and tables using Docling.

        Docling requires a file path, so bytes are written to a temp file.

        Args:
            data: PDF file content as bytes.

        Returns:
            Markdown-formatted text with preserved structure.

        Raises:
            RuntimeError: If Docling extraction fails.
        """
        logger.info("Running Docling extraction (high-fidelity mode)...")

        # Reason: Docling requires a file path, cannot work with bytes directly.
        # On Windows, NamedTemporaryFile with delete=True holds exclusive access,
        # so we use delete=False and manually clean up after Docling reads it.
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp_path = tmp.name

        try:
            tmp.write(data)
            tmp.close()  # Reason: Must close before Docling can read on Windows

            converter = self._get_docling_converter()
            result = converter.convert(tmp_path)
            markdown = result.document.export_to_markdown()

            logger.debug(f"Docling extraction: {len(markdown)} chars")
            return markdown

        except Exception as e:
            logger.error(f"Docling extraction failed: {e}")
            raise RuntimeError(f"Docling extraction failed: {e}") from e

        finally:
            # Reason: Clean up temp file regardless of success/failure
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _get_docling_converter(self) -> DocumentConverter:
        """
        Get or create the Docling converter with optimized settings.

        Returns:
            Configured DocumentConverter instance.
        """
        if self._docling_converter is None:
            pipeline_options = PdfPipelineOptions()
            pipeline_options.do_ocr = self.use_ocr
            pipeline_options.do_table_structure = True

            self._docling_converter = DocumentConverter(
                format_options={
                    InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
                }
            )

        return self._docling_converter

    def _needs_ocr(self, text: str, page_count: int) -> bool:
        """
        Determine if OCR is needed based on extraction quality.

        Args:
            text: Extracted text content.
            page_count: Number of pages in the PDF.

        Returns:
            True if OCR fallback should be used.
        """
        if not text.strip():
            logger.debug("Empty text extraction - OCR needed")
            return True

        avg_chars_per_page = len(text) / max(page_count, 1)
        needs_ocr = avg_chars_per_page < self.min_chars_per_page

        if needs_ocr:
            logger.debug(
                f"Low text density ({avg_chars_per_page:.0f} chars/page) - OCR needed"
            )

        return needs_ocr
