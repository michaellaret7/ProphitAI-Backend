# build_openai.py
import os, re, json, math, faiss, numpy as np, tiktoken
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
AGENT_MESSAGES_FILE = os.path.join(
    BACKEND_DIR,
    "src",
    "agentic_framework",
    "agent_output",
    "agent_messages.json",
)

# ---------- CONFIG ----------
MODEL = "text-embedding-3-large"  # or "text-embedding-3-small"
CHUNK_TOKENS = 800                # size target
CHUNK_OVERLAP = 120              # overlap for context carryover
SOURCE_FILE = os.path.join(BASE_DIR, "corpus.txt")        # or load however you like
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHUNK_STRATEGY = "json_role"
# -----------------------------

def _contains_structured_plan(content):
    """Return True if the content string looks like a structured plan payload."""
    if not isinstance(content, str):
        return False
    try:
        inner = json.loads(content)
        if isinstance(inner, dict) and ("plan" in inner or "structed_plan" in inner):
            return True
    except Exception:
        # Fall through to substring heuristics
        pass
    return ("\"plan\"" in content) or ("\"structed_plan\"" in content)


def _find_plan_boundary_index(messages):
    """Find index of the first tool message that contains a structured plan payload."""
    for idx, m in enumerate(messages):
        if isinstance(m, dict) and m.get("role") == "tool":
            if _contains_structured_plan(m.get("content")):
                return idx
    return None


def seed_corpus_from_agent_messages(
    agent_messages_path: str = AGENT_MESSAGES_FILE,
    corpus_path: str = SOURCE_FILE,
):
    """
    Seed corpus.txt with only the messages AFTER the first structured plan tool result.

    This constructs a minimal JSON payload: { "messages": [ ...post-plan messages... ] }
    and writes it to corpus_path.
    """
    with open(agent_messages_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages")
    if not isinstance(messages, list):
        raise ValueError("agent_messages.json does not contain a 'messages' array")

    boundary_idx = _find_plan_boundary_index(messages)
    if boundary_idx is None:
        raise RuntimeError("Could not locate structured plan tool message in agent_messages.json")

    # Keep all messages strictly after the plan tool message
    kept = messages[boundary_idx + 1 :]
    payload = {"messages": kept}

    # Validate payload is JSON-serializable
    _ = json.dumps(payload)

    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")


# ---------- TOOL METADATA EXTRACTION (for improved retrieval) ----------
def _parse_assistant_tool_calls(text: str):
    """Return list of {id, name, args_dict} from assistant tool_calls within the text."""
    import re as _re
    results = []
    try:
        pattern = _re.compile(
            r'"id"\s*:\s*"(call_[^"]+)"[\s\S]*?"function"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"[\s\S]*?"arguments"\s*:\s*"(.*?)"',
            _re.MULTILINE,
        )
        for m in pattern.finditer(text or ""):
            call_id, name, args_raw = m.group(1), m.group(2), m.group(3)
            args_dict = None
            try:
                # arguments are JSON encoded inside a JSON string
                args_dict = json.loads(args_raw)
            except Exception:
                args_dict = None
            results.append({"id": call_id, "name": name, "args": args_dict})
    except Exception:
        pass
    return results


def _extract_tool_call_id_from_tool_text(text: str):
    try:
        m = __import__("re").search(r'"tool_call_id"\s*:\s*"([^"]+)"', text or "")
        return m.group(1) if m else None
    except Exception:
        return None


def _normalize_tool_args(args):
    """Normalize commonly used args for downstream filtering (e.g., ticker, statement_type)."""
    norm = {}
    if not isinstance(args, dict):
        return norm
    # Ticker
    t = args.get("ticker") or args.get("symbol")
    if isinstance(t, str):
        norm["ticker"] = t.strip().upper()
    # Statement type
    st = args.get("statement_type") or args.get("statement")
    if isinstance(st, str):
        s = st.strip().lower().replace(" ", "_")
        alias = {
            "income": "income_statement",
            "income_stmt": "income_statement",
            "p&l": "income_statement",
            "pnl": "income_statement",
            "balance": "balance_sheet",
            "bs": "balance_sheet",
            "cash": "cash_flow",
            "cashflow": "cash_flow",
        }
        norm["statement_type"] = alias.get(s, s)
    # Industry level
    il = args.get("industry_level")
    if isinstance(il, str):
        norm["industry_level"] = il.strip()
    return norm

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
            rec = {
                "id": len(chunks),
                "source": f"doc_{doc_id}",
                "chunk": j,
                "text": piece,
            }
            if role:
                rec["role"] = role
            # If this is a tool message, try to enrich with tool metadata by peeking at
            # the previous assistant tool_call (neighbor association is done at query time too)
            if role == "tool":
                # Best-effort extraction of tool_call_id for downstream linking
                t_id = _extract_tool_call_id_from_tool_text(piece)
                if t_id:
                    rec["tool_call_id"] = t_id
            chunks.append(rec)

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
