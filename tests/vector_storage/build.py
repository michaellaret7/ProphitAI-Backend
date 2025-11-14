# build.py
import os, re, json, faiss, numpy as np, tiktoken
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- CONFIG ----------
MODEL = "text-embedding-3-large"  # or "text-embedding-3-small"
CHUNK_TOKENS = 800                # size target
CHUNK_OVERLAP = 120              # overlap for context carryover
SOURCE_FILE = os.path.join(BASE_DIR, "corpus.txt")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHUNK_STRATEGY = "markdown_sections"  # "markdown_sections" for essays, "tokens" for generic text
# -----------------------------

def load_texts():
    # Example corpus: put each doc on its own line or read a big file and chunk it.
    if os.path.exists(SOURCE_FILE):
        with open(SOURCE_FILE, "r", encoding="utf-8") as f:
            raw = f.read()
        return [raw]
    # fallback demo
    return ["doc chunk 1... ", "doc chunk 2..."]

def chunk_by_tokens(text, model):
    """Split text into chunks based on token count with overlap."""
    enc = tiktoken.get_encoding("cl100k_base")
    toks = enc.encode(text)
    chunks = []
    i = 0
    while i < len(toks):
        window = toks[i:i+CHUNK_TOKENS]
        chunks.append(enc.decode(window))
        i += CHUNK_TOKENS - CHUNK_OVERLAP
    return chunks

def chunk_by_markdown_sections(text: str, max_tokens: int = CHUNK_TOKENS):
    """
    Split text by markdown headers, keeping sections together.
    If a section exceeds max_tokens, further split it using token-based chunking.
    Returns list of dicts with 'text', 'header_level', and 'section_title' metadata.
    """
    enc = tiktoken.get_encoding("cl100k_base")

    # Split on markdown headers (# ## ### etc.)
    header_pattern = re.compile(r'^(#{1,6})\s+(.+?)$', re.MULTILINE)

    chunks = []
    current_section = []
    current_header = None
    current_level = None

    lines = text.split('\n')

    for line in lines:
        header_match = header_pattern.match(line)

        if header_match:
            # Save previous section if exists
            if current_section:
                section_text = '\n'.join(current_section).strip()
                if section_text:
                    # Check if section is too long
                    section_tokens = len(enc.encode(section_text))
                    if section_tokens > max_tokens:
                        # Split long section using token-based chunking
                        sub_chunks = chunk_by_tokens(section_text, MODEL)
                        for idx, sub_chunk in enumerate(sub_chunks):
                            chunks.append({
                                'text': sub_chunk,
                                'header_level': current_level,
                                'section_title': current_header,
                                'sub_chunk': idx
                            })
                    else:
                        chunks.append({
                            'text': section_text,
                            'header_level': current_level,
                            'section_title': current_header
                        })

            # Start new section
            current_level = len(header_match.group(1))
            current_header = header_match.group(2).strip()
            current_section = [line]
        else:
            current_section.append(line)

    # Don't forget the last section
    if current_section:
        section_text = '\n'.join(current_section).strip()
        if section_text:
            section_tokens = len(enc.encode(section_text))
            if section_tokens > max_tokens:
                sub_chunks = chunk_by_tokens(section_text, MODEL)
                for idx, sub_chunk in enumerate(sub_chunks):
                    chunks.append({
                        'text': sub_chunk,
                        'header_level': current_level,
                        'section_title': current_header,
                        'sub_chunk': idx
                    })
            else:
                chunks.append({
                    'text': section_text,
                    'header_level': current_level,
                    'section_title': current_header
                })

    return chunks

def embed_texts(texts):
    client = OpenAI(api_key=OPENAI_API_KEY)

    # OpenAI supports batching; keep under ~2048 inputs per call for comfort
    BATCH = 256
    vecs = []
    for s in range(0, len(texts), BATCH):
        batch = texts[s:s+BATCH]
        resp = client.embeddings.create(model=MODEL, input=batch)
        vecs.extend([d.embedding for d in resp.data])
    X = np.array(vecs, dtype="float32")
    # L2-normalize for cosine via L2
    norms = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    return (X / norms).astype("float32")

def main():
    """Build FAISS index from corpus with configured chunking strategy."""
    print(f"Loading corpus from {SOURCE_FILE}...")
    docs_raw = load_texts()
    print(f"Loaded {len(docs_raw)} document(s)")

    # Chunk documents based on strategy
    print(f"Chunking with strategy: {CHUNK_STRATEGY}")
    chunks = []
    for doc_id, doc in enumerate(docs_raw):
        if CHUNK_STRATEGY == "markdown_sections":
            # Semantic chunking by markdown headers
            pieces = chunk_by_markdown_sections(doc)
            for j, piece_dict in enumerate(pieces):
                rec = {
                    "id": len(chunks),
                    "source": f"doc_{doc_id}",
                    "chunk": j,
                    "text": piece_dict["text"],
                }
                # Add markdown-specific metadata
                if piece_dict.get("header_level"):
                    rec["header_level"] = piece_dict["header_level"]
                if piece_dict.get("section_title"):
                    rec["section_title"] = piece_dict["section_title"]
                if piece_dict.get("sub_chunk") is not None:
                    rec["sub_chunk"] = piece_dict["sub_chunk"]
                chunks.append(rec)
        else:
            # Default: token-based chunking
            pieces = chunk_by_tokens(doc, MODEL)
            for j, piece in enumerate(pieces):
                rec = {
                    "id": len(chunks),
                    "source": f"doc_{doc_id}",
                    "chunk": j,
                    "text": piece,
                }
                chunks.append(rec)

    print(f"Created {len(chunks)} chunks")

    # Embed texts using OpenAI
    print(f"Embedding {len(chunks)} chunks using {MODEL}...")
    X = embed_texts([c["text"] for c in chunks])

    # Build FAISS index (HNSW + IDs)
    print("Building FAISS index...")
    index = faiss.index_factory(X.shape[1], "HNSW32,IDMap")
    if not index.is_trained:
        index.train(X)
    ids = np.array([c["id"] for c in chunks], dtype="int64")
    index.add_with_ids(X, ids)

    # Persist index and metadata
    print("Saving index files...")
    np.save(os.path.join(BASE_DIR, "embeddings.npy"), X)
    faiss.write_index(index, os.path.join(BASE_DIR, "corpus.faiss"))
    with open(os.path.join(BASE_DIR, "docs.jsonl"), "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # Create manifest for reproducibility
    with open(os.path.join(BASE_DIR, "INDEX.yml"), "w") as f:
        f.write(
            f"model: {MODEL}\n"
            f"dim: {X.shape[1]}\n"
            f"chunks: {len(chunks)}\n"
            f"chunk_strategy: {CHUNK_STRATEGY}\n"
            f"chunk_tokens: {CHUNK_TOKENS}\n"
            f"chunk_overlap: {CHUNK_OVERLAP}\n"
        )

    print(f"\n{'='*60}")
    print(f"✓ Index built successfully!")
    print(f"  - Embeddings: embeddings.npy")
    print(f"  - Index: corpus.faiss")
    print(f"  - Metadata: docs.jsonl")
    print(f"  - Manifest: INDEX.yml")
    print(f"  - Total chunks: {len(chunks)}")
    print(f"  - Dimension: {X.shape[1]}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
