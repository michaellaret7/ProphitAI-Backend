"""
Modal GPU-accelerated PDF extraction using Docling.

Deploy: modal deploy app/core/foundry/ingestion/modal_ops/pdf_extractor.py
Test:   modal run app/core/foundry/ingestion/modal_ops/pdf_extractor.py
"""

import modal

app = modal.App(name="prophitai-pdf-extractor")

# Image with Docling and dependencies
docling_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("poppler-utils", "tesseract-ocr", "libgl1")
    .pip_install(
        "docling>=2.0.0",
        "boto3",
        "torch",
        "pymupdf",  # For quick text detection
    )
)

# Cache Docling's ML models across invocations
model_cache = modal.Volume.from_name("docling-model-cache", create_if_missing=True)

# Minimum characters to consider PDF as having extractable text
MIN_TEXT_THRESHOLD = 100


@app.cls(
    image=docling_image,
    gpu="L4",
    timeout=1200,
    volumes={"/cache": model_cache},
    secrets=[modal.Secret.from_name("aws-credentials")],
)
class PDFExtractor:
    """GPU-accelerated PDF extraction with Docling."""

    @modal.enter()
    def setup(self):
        """Load Docling converters once on container start."""
        import os

        os.environ["HF_HOME"] = "/cache/huggingface"
        os.environ["TORCH_HOME"] = "/cache/torch"

        from docling.document_converter import DocumentConverter
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import PdfFormatOption
        from docling.datamodel.pipeline_options import PdfPipelineOptions

        # Converter WITHOUT OCR (fast, for native text PDFs)
        options_no_ocr = PdfPipelineOptions()
        options_no_ocr.do_ocr = False
        options_no_ocr.do_table_structure = True

        self.converter_no_ocr = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options_no_ocr)
            }
        )

        # Converter WITH OCR (slow, for scanned PDFs)
        options_ocr = PdfPipelineOptions()
        options_ocr.do_ocr = True
        options_ocr.do_table_structure = True

        self.converter_ocr = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=options_ocr)
            }
        )

    def _needs_ocr(self, pdf_bytes: bytes) -> bool:
        """Check if PDF needs OCR by testing for extractable text."""
        import fitz  # PyMuPDF

        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        # Check first 3 pages
        for page_num in range(min(3, len(doc))):
            text += doc[page_num].get_text()
        doc.close()

        return len(text.strip()) < MIN_TEXT_THRESHOLD

    @modal.method()
    def extract_from_s3(self, s3_uri: str) -> dict:
        """Extract text from a single PDF in S3."""
        import boto3
        import tempfile
        import os

        bucket = s3_uri[5:].split("/")[0]
        key = "/".join(s3_uri[5:].split("/")[1:])

        s3 = boto3.client("s3")
        response = s3.get_object(Bucket=bucket, Key=key)
        pdf_bytes = response["Body"].read()

        # Choose converter based on PDF content
        needs_ocr = self._needs_ocr(pdf_bytes)
        converter = self.converter_ocr if needs_ocr else self.converter_no_ocr
        print(f"Processing {s3_uri} | OCR: {needs_ocr}")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            result = converter.convert(tmp_path)
            content = result.document.export_to_markdown()
            return {
                "content": content,
                "char_count": len(content),
                "s3_uri": s3_uri,
                "used_ocr": needs_ocr,
            }
        finally:
            os.unlink(tmp_path)

    @modal.method()
    def extract_batch_from_s3(self, s3_uris: list[str]) -> list[dict]:
        """Extract text from multiple PDFs in S3 (single container, sequential)."""
        results = []
        for uri in s3_uris:
            try:
                result = self.extract_from_s3.local(uri)
                results.append(result)
            except Exception as e:
                results.append({"s3_uri": uri, "error": str(e), "content": None})
        return results

    @modal.method()
    def extract_from_bytes(self, pdf_bytes: bytes) -> dict:
        """Extract text from PDF bytes."""
        import tempfile
        import os

        needs_ocr = self._needs_ocr(pdf_bytes)
        converter = self.converter_ocr if needs_ocr else self.converter_no_ocr

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = tmp.name

        try:
            result = converter.convert(tmp_path)
            content = result.document.export_to_markdown()
            return {"content": content, "char_count": len(content), "used_ocr": needs_ocr}
        finally:
            os.unlink(tmp_path)


@app.local_entrypoint()
def main(s3_uri: str | None = None):
    """
    Test the extractor.

    Usage:
        modal run pdf_extractor.py
        modal run pdf_extractor.py --s3-uri "s3://prophitai-s3-bucket/pdfs/test.pdf"
    """
    extractor = PDFExtractor()

    if s3_uri:
        print(f"Extracting from S3: {s3_uri}")
        result = extractor.extract_from_s3.remote(s3_uri)
        print(f"Extracted {result['char_count']} characters (OCR: {result['used_ocr']})")
        print(f"Preview: {result['content'][:500]}...")
    else:
        print("No S3 URI provided. Run with --s3-uri to test S3 extraction.")
