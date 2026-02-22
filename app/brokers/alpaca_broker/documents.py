"""
Alpaca Broker Documents
Handles account statements, trade confirmations, and tax documents.

Uses SDK methods where available; thin httpx fallback only for download URL redirect capture.
"""

from alpaca.broker.client import BrokerClient
from alpaca.broker.requests import GetTradeDocumentsRequest
from typing import Optional, List, Dict
import httpx


class BrokerDocuments:
    """Handles document retrieval for end user accounts."""

    def __init__(
        self,
        client: BrokerClient,
        api_key: str,
        secret_key: str,
        sandbox: bool = True,
    ):
        self.client = client
        self.api_key = api_key
        self.secret_key = secret_key
        self.sandbox = sandbox
        self._base_url = (
            "https://broker-api.sandbox.alpaca.markets"
            if sandbox
            else "https://broker-api.alpaca.markets"
        )

    # ════════════════════════════════════════════════════════════
    # --> Helper funcs
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _format_document(doc) -> Dict:
        """Format a document model into a standardized dict."""
        return {
            "document_id": str(doc.id) if hasattr(doc, "id") else None,
            "type": str(doc.type) if hasattr(doc, "type") else None,
            "sub_type": getattr(doc, "sub_type", None),
            "date": str(doc.date) if hasattr(doc, "date") else None,
            "name": getattr(doc, "name", None),
        }

    # ════════════════════════════════════════════════════════════
    # Document Retrieval
    # ════════════════════════════════════════════════════════════

    def get_documents(
        self,
        account_id: str,
        doc_type: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> List[Dict]:
        """
        Get all documents for an account, optionally filtered.

        Args:
            account_id: User's Alpaca account ID
            doc_type: Filter by type:
                - 'account_statement' — monthly account statements
                - 'trade_confirmation' — trade confirmations
                - 'tax_statement' — 1099, 1042-S, 480.6 tax forms
            start: Start date filter (YYYY-MM-DD)
            end: End date filter (YYYY-MM-DD)

        Returns:
            List of document metadata dicts
        """
        try:
            doc_filter = GetTradeDocumentsRequest(start=start, end=end)
            docs = self.client.get_trade_documents_for_account(
                account_id=account_id,
                documents_filter=doc_filter,
            )
            results = [self._format_document(doc) for doc in docs]
            if doc_type:
                results = [d for d in results if d.get("type") == doc_type]
            return results
        except Exception as e:
            raise Exception(f"Failed to get documents for {account_id}: {str(e)}")

    def get_document(self, account_id: str, document_id: str) -> Dict:
        """Get a specific document by ID."""
        try:
            doc = self.client.get_trade_document_for_account_by_id(
                account_id=account_id,
                document_id=document_id,
            )
            return self._format_document(doc)
        except Exception as e:
            raise Exception(f"Failed to get document {document_id}: {str(e)}")

    def get_download_url(self, account_id: str, document_id: str) -> str:
        """
        Get a pre-signed download URL for a document (PDF format).

        The endpoint returns a 301 redirect to a pre-signed URL.
        We capture the redirect URL without following it.

        Args:
            account_id: User's Alpaca account ID
            document_id: Document UUID

        Returns:
            Pre-signed download URL string
        """
        try:
            # Reason: SDK does not expose download URL redirect; use httpx to capture 301
            url = f"{self._base_url}/v1/accounts/{account_id}/documents/{document_id}/download"
            auth = httpx.BasicAuth(self.api_key, self.secret_key)
            response = httpx.get(url, auth=auth, follow_redirects=False)
            if response.status_code == 301 and "location" in response.headers:
                return response.headers["location"]
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Failed to get download URL for document {document_id}: {str(e)}")

    # ── Convenience methods ───────────────────────────────────

    def get_statements(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get monthly account statements."""
        return self.get_documents(account_id, doc_type="account_statement", start=start, end=end)

    def get_trade_confirmations(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get trade confirmations."""
        return self.get_documents(account_id, doc_type="trade_confirmation", start=start, end=end)

    def get_tax_documents(
        self, account_id: str, start: Optional[str] = None, end: Optional[str] = None,
    ) -> List[Dict]:
        """Get tax documents (1099s, 1042-S, etc.)."""
        return self.get_documents(account_id, doc_type="tax_statement", start=start, end=end)
