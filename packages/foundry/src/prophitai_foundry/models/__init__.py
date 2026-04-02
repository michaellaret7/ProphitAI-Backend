"""
Foundry models submodule.

Provides data models for document ingestion and processing.
"""
from importlib import import_module

__all__ = [
    "Chunk",
    "Document",
    "EarningsCallMetadata",
    "IndexStats",
    "QueryResult",
    "VectorRecord",
    "IngestionItem",
    "BatchResult",
    "IngestionResult",
]


def __getattr__(name: str):
    """Lazily load model exports to avoid importing optional dependencies eagerly."""
    module_map = {
        "Chunk": ("prophitai_foundry.models.chunk", "Chunk"),
        "Document": ("prophitai_foundry.models.document", "Document"),
        "EarningsCallMetadata": ("prophitai_foundry.models.metadata", "EarningsCallMetadata"),
        "IndexStats": ("prophitai_foundry.models.vector", "IndexStats"),
        "QueryResult": ("prophitai_foundry.models.vector", "QueryResult"),
        "VectorRecord": ("prophitai_foundry.models.vector", "VectorRecord"),
        "IngestionItem": ("prophitai_foundry.models.pipeline", "IngestionItem"),
        "BatchResult": ("prophitai_foundry.models.pipeline", "BatchResult"),
        "IngestionResult": ("prophitai_foundry.models.pipeline", "IngestionResult"),
    }

    if name not in module_map:
        raise AttributeError(f"module 'prophitai_foundry.models' has no attribute {name!r}")

    module_name, attr_name = module_map[name]
    return getattr(import_module(module_name), attr_name)
