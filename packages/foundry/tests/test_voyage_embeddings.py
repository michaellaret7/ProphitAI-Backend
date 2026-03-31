import importlib.util
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest
import voyageai.error as voyage_error  # type: ignore[import-untyped]


ROOT = Path(__file__).resolve().parents[1] / "src" / "prophitai_foundry"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


prophitai_pkg = types.ModuleType("prophitai_foundry")
prophitai_pkg.__path__ = [str(ROOT)]
sys.modules.setdefault("prophitai_foundry", prophitai_pkg)

models_pkg = types.ModuleType("prophitai_foundry.models")
models_pkg.__path__ = [str(ROOT / "models")]
sys.modules.setdefault("prophitai_foundry.models", models_pkg)

embeddings_pkg = types.ModuleType("prophitai_foundry.embeddings")
embeddings_pkg.__path__ = [str(ROOT / "embeddings")]
sys.modules.setdefault("prophitai_foundry.embeddings", embeddings_pkg)

chunk_module = _load_module("prophitai_foundry.models.chunk", ROOT / "models" / "chunk.py")
voyage_embeddings = _load_module(
    "prophitai_foundry.embeddings.voyage_embeddings",
    ROOT / "embeddings" / "voyage_embeddings.py",
)
Chunk = chunk_module.Chunk


def _chunk(text: str, token_count: int) -> Chunk:
    return Chunk(
        text=text,
        start_index=0,
        end_index=len(text),
        token_count=token_count,
        metadata={},
    )


def test_batch_chunks_by_tokens_uses_inflated_estimates():
    chunks = [
        _chunk("x" * 900, token_count=500),
        _chunk("y" * 900, token_count=500),
    ]

    batches = voyage_embeddings._batch_chunks_by_tokens(chunks, max_tokens=1100)

    assert len(batches) == 2
    assert batches[0] == [chunks[0]]
    assert batches[1] == [chunks[1]]


def test_embed_chunks_retries_by_splitting_oversized_batch(monkeypatch: pytest.MonkeyPatch):
    calls: list[list[str]] = []

    class FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def embed(self, texts: list[str], model: str, input_type: str) -> SimpleNamespace:
            calls.append(texts)
            if len(texts) > 1:
                raise voyage_error.InvalidRequestError("Please lower the number of tokens in the batch")

            return SimpleNamespace(embeddings=[[float(len(texts[0]))]])

    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setattr(voyage_embeddings.voyageai, "Client", FakeClient)
    monkeypatch.setattr(voyage_embeddings, "_batch_chunks_by_tokens", lambda chunks: [chunks])

    embedded = voyage_embeddings.embed_chunks(
        [
            _chunk("alpha", token_count=10),
            _chunk("beta", token_count=10),
        ]
    )

    assert [len(call) for call in calls] == [2, 1, 1]
    assert [chunk.embedding for chunk in embedded] == [[5.0], [4.0]]


def test_embed_chunks_raises_clear_error_for_single_oversized_chunk(monkeypatch: pytest.MonkeyPatch):
    class FakeClient:
        def __init__(self, api_key: str):
            self.api_key = api_key

        def embed(self, texts: list[str], model: str, input_type: str) -> SimpleNamespace:
            raise voyage_error.InvalidRequestError("Please lower the number of tokens in the batch")

    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")
    monkeypatch.setattr(voyage_embeddings.voyageai, "Client", FakeClient)

    with pytest.raises(ValueError, match="Voyage rejected a single chunk"):
        voyage_embeddings.embed_chunks([_chunk("alpha", token_count=10)])
