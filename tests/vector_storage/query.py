# query.py
import os, json, faiss, numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL = "text-embedding-3-large"
TOP_K = 5  # number of results to display
SEARCH_K = 20  # candidates to retrieve before filtering
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SHOW_CONTEXT = True  # Show surrounding chunks for context

def load_index():
    """Load FAISS index, embeddings, and document metadata."""
    index = faiss.read_index(os.path.join(BASE_DIR, "corpus.faiss"))
    X = np.load(os.path.join(BASE_DIR, "embeddings.npy"))
    id2text = {}
    with open(os.path.join(BASE_DIR, "docs.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            id2text[r["id"]] = r
    return index, X.shape[1], id2text


def build_source_index(id2text):
    """Index records by source and sort by chunk for context retrieval."""
    by_src = {}
    for rec in id2text.values():
        src = rec.get("source")
        by_src.setdefault(src, []).append(rec)
    for src, arr in by_src.items():
        arr.sort(key=lambda r: r.get("chunk", 0))
    return by_src


def get_context_chunks(rec, by_src, before=1, after=1):
    """Get surrounding chunks for context."""
    src = rec.get("source")
    cur_chunk = rec.get("chunk", -1)
    records = by_src.get(src, [])

    context = {"before": [], "after": []}

    for r in records:
        chunk_id = r.get("chunk", -1)
        if cur_chunk - before <= chunk_id < cur_chunk:
            context["before"].append(r)
        elif cur_chunk < chunk_id <= cur_chunk + after:
            context["after"].append(r)

    return context


def embed_query(q):
    """Embed query text using OpenAI API."""
    client = OpenAI(api_key=OPENAI_API_KEY)
    vec = client.embeddings.create(model=MODEL, input=[q]).data[0].embedding
    v = np.array([vec], dtype="float32")
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return v


def format_result(rank, rec, score, show_context=False, context=None):
    """Format a search result for display."""
    output = []
    output.append(f"\n{'='*80}")
    output.append(f"RESULT {rank} (Similarity: {1-score:.4f})")
    output.append(f"{'='*80}")

    # Display metadata
    section_title = rec.get("section_title")
    header_level = rec.get("header_level")
    sub_chunk = rec.get("sub_chunk")

    if section_title:
        header_prefix = "#" * header_level if header_level else "#"
        output.append(f"Section: {header_prefix} {section_title}")

    if sub_chunk is not None:
        output.append(f"Sub-chunk: {sub_chunk}")

    output.append(f"Source: {rec.get('source')} | Chunk: {rec.get('chunk')}")
    output.append(f"{'-'*80}")

    # Show context if requested
    if show_context and context:
        if context.get("before"):
            output.append("\n[CONTEXT BEFORE]")
            for ctx in context["before"]:
                ctx_title = ctx.get("section_title", "")
                if ctx_title:
                    output.append(f"  [{ctx_title}]")
                output.append(f"  {ctx.get('text', '')[:200]}...")
                output.append("")

    # Main content
    output.append("\n[MAIN CONTENT]")
    output.append(rec.get("text", ""))

    if show_context and context:
        if context.get("after"):
            output.append("\n[CONTEXT AFTER]")
            for ctx in context["after"]:
                ctx_title = ctx.get("section_title", "")
                if ctx_title:
                    output.append(f"  [{ctx_title}]")
                output.append(f"  {ctx.get('text', '')[:200]}...")
                output.append("")

    return "\n".join(output)


def main():
    """Main query loop."""
    print("Loading vector index...")
    index, d, id2text = load_index()
    by_src = build_source_index(id2text)

    print(f"Loaded {len(id2text)} chunks")
    print(f"Index dimension: {d}")
    print(f"\nQuery Settings: TOP_K={TOP_K}, SEARCH_K={SEARCH_K}, SHOW_CONTEXT={SHOW_CONTEXT}")
    print("="*80)

    while True:
        q = input("\nQuery (or 'quit' to exit): ").strip()

        if q.lower() in ['quit', 'exit', 'q']:
            break

        if not q:
            continue

        # Embed and search
        qv = embed_query(q)
        D, I = index.search(qv, SEARCH_K)

        # Collect and display top results
        results = []
        for score, idx in zip(D[0], I[0]):
            r = id2text.get(int(idx))
            if r:
                results.append((score, r))

        # Sort by similarity (lower L2 distance = higher similarity)
        results.sort(key=lambda x: x[0])

        print(f"\nFound {len(results)} results. Showing top {TOP_K}:")

        for rank, (score, rec) in enumerate(results[:TOP_K], start=1):
            context = None
            if SHOW_CONTEXT:
                context = get_context_chunks(rec, by_src, before=1, after=1)

            print(format_result(rank, rec, score, SHOW_CONTEXT, context))


if __name__ == "__main__":
    main()
