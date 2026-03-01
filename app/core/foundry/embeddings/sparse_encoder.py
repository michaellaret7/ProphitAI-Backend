"""
Sparse encoder for BM25-based hybrid search.

Wraps pinecone-text's BM25Encoder with save/load functionality
for persistence across application restarts.
"""

import zipfile
from pathlib import Path

# Reason: Pre-load NLTK stopwords before BM25Encoder to prevent race condition
# when multiple parallel tool calls try to access the lazy-loaded corpus.
# This fixes: 'WordListCorpusReader' object has no attribute '_LazyCorpusLoader__args'
import nltk
from nltk.corpus import stopwords

try:
    nltk.data.find("corpora/stopwords")
    # Reason: Validate the corpus is loadable, not just present on disk.
    # A corrupt/incomplete download passes the find() check but fails when read.
    stopwords.ensure_loaded()
except (LookupError, zipfile.BadZipFile, OSError):
    # Reason: Force re-download if missing OR corrupted (e.g., partial Render deploy)
    import shutil

    for p in nltk.data.path:
        corrupt = Path(p) / "corpora" / "stopwords"
        if corrupt.exists():
            shutil.rmtree(corrupt, ignore_errors=True)
        corrupt_zip = Path(p) / "corpora" / "stopwords.zip"
        if corrupt_zip.exists():
            corrupt_zip.unlink(missing_ok=True)

    nltk.download("stopwords", quiet=True)

_ = stopwords.words("english")

from pinecone_text.sparse import BM25Encoder

# Default directory for trained models (app/core/foundry/models/encoder/)
FOUNDRY_DIR = Path(__file__).parent.parent
MODELS_DIR = FOUNDRY_DIR / "models" / "encoder"
DEFAULT_MODEL_PATH = MODELS_DIR / "bm25_encoder.json"

class SparseEncoder:
    """BM25 sparse encoder for hybrid search."""

    def __init__(self):
        self.encoder = BM25Encoder()
        self.is_fitted = False

    def fit(self, corpus: list[str]) -> None:
        """Fit on a corpus."""
        self.encoder.fit(corpus)
        self.is_fitted = True

    def encode(self, text: str) -> dict:
        """Encode a document into a sparse vector."""
        if not self.is_fitted:
            raise RuntimeError("Encoder not fitted. Call fit() or load() first.")
        return self.encoder.encode_documents([text])[0] # type: ignore

    def encode_query(self, query: str) -> dict:
        """Encode a query into a sparse vector."""
        if not self.is_fitted:
            raise RuntimeError("Encoder not fitted. Call fit() or load() first.")
        return self.encoder.encode_queries([query])[0] # type: ignore

    def save(self, path: Path | str | None = None) -> Path:
        """Save the fitted encoder."""
        if not self.is_fitted:
            raise RuntimeError("Cannot save unfitted encoder.")

        save_path = Path(path) if path else DEFAULT_MODEL_PATH
        save_path.parent.mkdir(parents=True, exist_ok=True)
        self.encoder.dump(str(save_path))
        return save_path

    def load(self, path: Path | str | None = None) -> None:
        """Load a fitted encoder."""
        load_path = Path(path) if path else DEFAULT_MODEL_PATH
        if not load_path.exists():
            raise FileNotFoundError(f"No encoder found at {load_path}")

        # Reason: BM25Encoder.load is an instance method, not a class method
        self.encoder = BM25Encoder().load(str(load_path))
        self.is_fitted = True

