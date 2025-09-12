# build_openai.py
import os, re, json, math, faiss, numpy as np, tiktoken
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- CONFIG ----------
MODEL = "text-embedding-3-large"  # or "text-embedding-3-small"
CHUNK_TOKENS = 800                # size target
CHUNK_OVERLAP = 120              # overlap for context carryover
SOURCE_FILE = os.path.join(BASE_DIR, "corpus.txt")        # or load however you like
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# chunk strategy: "json_role" (split by role boundaries) or "token"
CHUNK_STRATEGY = "json_role"
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
    enc = tiktoken.get_encoding("cl100k_base")
    toks = enc.encode(text)
    chunks = []
    i = 0
    while i < len(toks):
        window = toks[i:i+CHUNK_TOKENS]
        chunks.append(enc.decode(window))
        i += CHUNK_TOKENS - CHUNK_OVERLAP
    return chunks

def chunk_by_role_boundaries(text: str):
    # Split before occurrences of JSON message objects containing a role field
    # Matches: ..."role": "user"|"assistant"|"tool"
    pattern = re.compile(r'(?m)(?=\s*\"role\"\s*:\s*\"(?:user|assistant|tool)\")')
    parts = [p.strip() for p in pattern.split(text) if p.strip()]
    return parts if parts else [text]

def extract_role(block: str):
    m = re.search(r'\"role\"\s*:\s*\"([^\"]+)\"', block)
    return m.group(1) if m else None

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
    docs_raw = load_texts()
    # chunk
    chunks = []
    for doc_id, doc in enumerate(docs_raw):
        if CHUNK_STRATEGY == "json_role":
            pieces = chunk_by_role_boundaries(doc)
        else:
            pieces = chunk_by_tokens(doc, MODEL)
        for j, piece in enumerate(pieces):
            role = extract_role(piece)
            chunks.append({
                "id": len(chunks),
                "source": f"doc_{doc_id}",
                "chunk": j,
                "text": piece,
                **({"role": role} if role else {})
            })

    # embed (OpenAI)
    X = embed_texts([c["text"] for c in chunks])

    # FAISS index (HNSW + IDs)
    index = faiss.index_factory(X.shape[1], "HNSW32,IDMap")
    if not index.is_trained:
        index.train(X)
    ids = np.array([c["id"] for c in chunks], dtype="int64")
    index.add_with_ids(X, ids)

    # persist
    np.save(os.path.join(BASE_DIR, "embeddings.npy"), X)
    faiss.write_index(index, os.path.join(BASE_DIR, "corpus.faiss"))
    with open(os.path.join(BASE_DIR, "docs.jsonl"), "w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # simple manifest for reproducibility
    with open(os.path.join(BASE_DIR, "INDEX.yml"), "w") as f:
        f.write(
            f"model: {MODEL}\n"
            f"dim: {X.shape[1]}\n"
            f"chunks: {len(chunks)}\n"
            f"chunk_tokens: {CHUNK_TOKENS}\n"
            f"chunk_overlap: {CHUNK_OVERLAP}\n"
        )

if __name__ == "__main__":
    main()
