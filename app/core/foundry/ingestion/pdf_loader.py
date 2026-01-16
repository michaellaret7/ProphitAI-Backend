"""
PDF ingestion module for RAG pipelines.

Handles digital extraction, OCR fallback, and structured output.
Uses PyMuPDF for fast digital extraction and Docling for layout-aware processing.
"""
import logging
from pathlib import Path
from typing import Optional

from app.core.foundry.models.ingestion_output import Document
import pymupdf
from pdf2image import convert_from_path
from pdf2image.exceptions import PDFPageCountError, PDFInfoNotInstalledError
import pytesseract
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
import warnings

# Suppress warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration constants
MIN_CHARS_PER_PAGE: int = 50
DEFAULT_OCR_LANG: str = "eng"

class PDFIngestor:
    """
    A unified PDF ingestion class for RAG pipelines.

    Handles digital extraction, OCR fallback, and structured Markdown output.
    Uses PyMuPDF for fast digital extraction (570x faster than pypdf).

    Attributes:
        use_ocr: Whether to fall back to OCR for scanned documents.
        ocr_lang: Language code for OCR (default: "eng").
        high_fidelity: Use Docling for layout-aware extraction.
        min_chars_per_page: Minimum characters per page before triggering OCR fallback.
    """

    def __init__(
        self,
        use_ocr: bool = True,
        ocr_lang: str = DEFAULT_OCR_LANG,
        high_fidelity: bool = False,
        min_chars_per_page: int = MIN_CHARS_PER_PAGE,
    ) -> None:
        """
        Initialize PDFIngestor with extraction options.

        Args:
            use_ocr: Enable OCR fallback for scanned documents.
            ocr_lang: Tesseract language code for OCR.
            high_fidelity: Use Docling for layout-aware extraction.
            min_chars_per_page: Threshold for OCR fallback detection.
        """
        self.use_ocr = use_ocr
        self.ocr_lang = ocr_lang
        self.high_fidelity = high_fidelity
        self.min_chars_per_page = min_chars_per_page
        self._docling_converter: Optional[DocumentConverter] = None

    def process(self, file_path: str | Path) -> Document:
        """
        Main entry point to get cleaned text from a PDF.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Document with content and metadata.

        Raises:
            FileNotFoundError: If the file does not exist.
            RuntimeError: If extraction fails completely.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        logger.info(f"Processing PDF: {path.name}")

        extraction_method = "digital"
        page_count = 0

        # Option 1: State-of-the-art layout-aware extraction
        if self.high_fidelity:
            content, page_count = self._extract_with_docling(str(path))
            extraction_method = "docling"
        else:
            # Option 2: Fast Digital Extraction
            content, page_count = self._extract_digital_text(str(path))

            # Fallback to OCR if digital text is insufficient
            if self._needs_ocr(content, page_count) and self.use_ocr:
                logger.info("Digital extraction insufficient, falling back to OCR")
                content = self._extract_ocr_text(str(path))
                extraction_method = "ocr"

        metadata = {
            "filename": path.name,
            "extension": ".pdf",
            "size_bytes": path.stat().st_size,
            "char_count": len(content),
            "page_count": page_count,
            "extraction_method": extraction_method,
            "high_fidelity": self.high_fidelity,
        }

        return Document(
            content=content,
            metadata=metadata,
            source=str(path.absolute()),
        )

    def _extract_digital_text(self, pdf_path: str) -> tuple[str, int]:
        """
        Fast extraction using PyMuPDF for selectable text.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Tuple of (extracted text, page count).

        Raises:
            RuntimeError: If PyMuPDF extraction fails.
        """
        try:
            doc = pymupdf.open(pdf_path)
            page_count = len(doc)
            full_text: list[str] = []

            for i, page in enumerate(doc):
                text = page.get_text()
                if text.strip():
                    full_text.append(f"--- Page {i + 1} ---\n{text}")

            doc.close()

            extracted = "\n".join(full_text)
            logger.debug(
                f"Digital extraction: {len(extracted)} chars from {page_count} pages"
            )
            return extracted, page_count

        except Exception as e:
            logger.error(f"Digital extraction failed: {e}")
            raise RuntimeError(f"PyMuPDF extraction failed: {e}") from e

    def _extract_ocr_text(self, pdf_path: str) -> str:
        """
        Fallback OCR for scanned documents using Tesseract.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            OCR-extracted text content.

        Raises:
            RuntimeError: If OCR extraction fails.
        """
        logger.info(f"Running OCR on {Path(pdf_path).name}...")

        try:
            pages = convert_from_path(pdf_path)
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

    def _extract_with_docling(self, pdf_path: str) -> tuple[str, int]:
        """
        Advanced extraction preserving layout and tables using Docling.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Tuple of (markdown-formatted text, page count).

        Raises:
            RuntimeError: If Docling extraction fails.
        """
        logger.info(f"Running Docling extraction on {Path(pdf_path).name}...")

        try:
            converter = self._get_docling_converter()
            result = converter.convert(pdf_path)
            markdown = result.document.export_to_markdown()

            # Get page count using pymupdf (docling doesn't expose this directly)
            doc = pymupdf.open(pdf_path)
            page_count = len(doc)
            doc.close()

            logger.debug(f"Docling extraction: {len(markdown)} chars from {page_count} pages")
            return markdown, page_count

        except Exception as e:
            logger.error(f"Docling extraction failed: {e}")
            raise RuntimeError(f"Docling extraction failed: {e}") from e

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



