"""Client for calling Modal PDF extraction service."""

import modal


class ModalPDFClient:
    """Client for GPU-accelerated PDF extraction via Modal."""

    def __init__(self):
        self._extractor = None

    @property
    def extractor(self):
        """Lazy-load the deployed Modal class."""
        if self._extractor is None:
            PDFExtractor = modal.Cls.from_name(
                "prophitai-pdf-extractor",
                "PDFExtractor",
            )
            self._extractor = PDFExtractor()
        return self._extractor

    def extract_from_bytes(self, pdf_bytes: bytes) -> str:
        """Extract PDF content from bytes using Modal GPU."""
        result = self.extractor.extract_from_bytes.remote(pdf_bytes)
        return result["content"]

    def extract_from_s3(self, s3_uri: str) -> str:
        """Extract PDF content from S3 using Modal GPU."""
        result = self.extractor.extract_from_s3.remote(s3_uri)
        return result["content"]

    def extract_batch_from_s3(self, s3_uris: list[str]) -> list[dict]:
        """
        Extract multiple PDFs from S3 in a single Modal call.

        Args:
            s3_uris: List of S3 URIs to process.

        Returns:
            List of dicts with 'content', 'char_count', 's3_uri' (or 'error' if failed).
        """
        return self.extractor.extract_batch_from_s3.remote(s3_uris)
