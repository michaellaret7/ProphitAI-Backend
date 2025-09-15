# query_openai.py
import os, json, faiss, numpy as np
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MODEL = "text-embedding-3-large"
TOP_K = 1  # results to display
SEARCH_K = 40  # candidates to retrieve before re-ranking
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def load_index():
    index = faiss.read_index(os.path.join(BASE_DIR, "corpus.faiss"))
    X = np.load(os.path.join(BASE_DIR, "embeddings.npy"))
    id2text = {}
    with open(os.path.join(BASE_DIR, "docs.jsonl"), "r", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            id2text[r["id"]] = r
    return index, X.shape[1], id2text


def build_source_index(id2text):
    """Index records by source then sort by chunk for neighbor lookups."""
    by_src = {}
    for rec in id2text.values():
        src = rec.get("source")
        by_src.setdefault(src, []).append(rec)
    for src, arr in by_src.items():
        arr.sort(key=lambda r: r.get("chunk", 0))
    return by_src


def map_to_tool_output(rec, by_src):
    """
    If a result is an assistant tool_call, return the following tool record's text.
    Otherwise return the record unchanged.
    """
    text = rec.get("text", "")
    role = rec.get("role")
    # Heuristic: assistant role with tool_calls block
    if role == "assistant" and '"tool_calls"' in text:
        src = rec.get("source")
        cur_chunk = rec.get("chunk", -1)
        candidates = by_src.get(src) or []
        for cand in candidates:
            if cand.get("chunk", -1) > cur_chunk and cand.get("role") == "tool":
                return cand
    return rec


def _extract_tool_call_id_from_tool_text(text: str):
    try:
        m = __import__("re").search(r'"tool_call_id"\s*:\s*"([^"]+)"', text or "")
        return m.group(1) if m else None
    except Exception:
        return None


def _find_prev_assistant_record(records, chunk_idx):
    prev = None
    for r in records:
        if r.get("chunk", -1) >= chunk_idx:
            break
        if r.get("role") == "assistant":
            prev = r
    return prev


def _parse_assistant_tool_calls(text: str):
    """Return list of {id, name, args_dict} from assistant tool_calls within the text."""
    import re, json as _json

    results = []
    pattern = re.compile(r'"id"\s*:\s*"(call_[^"]+)"[\s\S]*?"function"\s*:\s*\{[\s\S]*?"name"\s*:\s*"([^"]+)"[\s\S]*?"arguments"\s*:\s*"(.*?)"', re.MULTILINE)
    for m in pattern.finditer(text or ""):
        call_id, name, args_raw = m.group(1), m.group(2), m.group(3)
        args_dict = None
        try:
            args_dict = _json.loads(args_raw)
        except Exception:
            args_dict = None
        results.append({"id": call_id, "name": name, "args": args_dict})
    return results


def _find_tool_record_for_call_id(records, call_id: str):
    import re
    if not call_id:
        return None
    pat = re.compile(r'"tool_call_id"\s*:\s*"' + re.escape(call_id) + r'"')
    for r in records:
        if r.get("role") == "tool" and pat.search(r.get("text", "") or ""):
            return r
    return None


def _get_tool_metadata_for_record(rec, by_src):
    """Return (tool_name, args_dict) for a tool record by inspecting the previous assistant tool_calls."""
    if rec.get("role") != "tool":
        return None, None
    src = rec.get("source")
    records = by_src.get(src) or []
    cur_chunk = rec.get("chunk", -1)
    prev_assistant = _find_prev_assistant_record(records, cur_chunk)
    if not prev_assistant:
        return None, None
    calls = _parse_assistant_tool_calls(prev_assistant.get("text", "") or "")
    if not calls:
        return None, None
    # If tool_call_id present in tool text, match directly
    tcid = _extract_tool_call_id_from_tool_text(rec.get("text", "") or "")
    if tcid:
        for c in calls:
            if c.get("id") == tcid:
                return c.get("name"), c.get("args")
    # Fallback: if only one call, assume it
    if len(calls) == 1:
        c = calls[0]
        return c.get("name"), c.get("args")
    return None, None

def embed_query(q):
    client = OpenAI(api_key=OPENAI_API_KEY)
    vec = client.embeddings.create(model=MODEL, input=[q]).data[0].embedding
    v = np.array([vec], dtype="float32")
    v /= (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)
    return v

def main():
    index, d, id2text = load_index()
    by_src = build_source_index(id2text)
    q = input("Query: ").strip()
    qv = embed_query(q)
    # retrieve wider set for re-ranking
    D, I = index.search(qv, SEARCH_K)

    # Desired filters inferred from query text
    desire_ticker = None
    desire_stmt = None
    desired_tool = None
    ql = q.lower()
    import re as _re
    m = _re.search(r"\b([A-Z]{1,5})\b", q.upper())
    if m:
        desire_ticker = m.group(1)
    for key, val in [("income_statement", ["income statement", "income_statement", "p&l", "pnl"]),
                     ("balance_sheet", ["balance sheet", "balance_sheet", "bs"]),
                     ("cash_flow", ["cash flow", "cashflow", "cash_flow"])]:
        if any(v in ql for v in val):
            desire_stmt = key
            break
    if ("free_search" in ql) or ("free search" in ql):
        desired_tool = "free_search"
    elif "industry_concentration" in ql:
        desired_tool = "industry_concentration"
    elif ("get_ticker_fundamental_data" in ql) or ("fundamentals" in ql) or ("fundamental" in ql) or ("get ticker fundamental" in ql):
        desired_tool = "get_ticker_fundamental_data"

    for rank, (score, idx) in enumerate(zip(D[0], I[0]), start=1):
        r = id2text.get(int(idx))
        if not r:
            continue
        mapped = map_to_tool_output(r, by_src)
        # If mapped is a tool record and original was an assistant call, try to enforce argument-level preference
        src = mapped.get("source")
        records = by_src.get(src) or []
        cur_chunk = mapped.get("chunk", -1)
        prev_assistant = _find_prev_assistant_record(records, cur_chunk)
        if prev_assistant and mapped.get("role") == "tool" and (desire_ticker or desire_stmt):
            calls = _parse_assistant_tool_calls(prev_assistant.get("text", "") or "")
            best = mapped
            best_score = 0
            for c in calls:
                args = c.get("args") or {}
                score_match = 0
                t = args.get("ticker") or args.get("symbol")
                if desire_ticker and isinstance(t, str) and t.strip().upper() == desire_ticker:
                    score_match += 2
                st = args.get("statement_type") or args.get("statement")
                if desire_stmt and isinstance(st, str) and st.strip().lower().replace(" ", "_") == desire_stmt:
                    score_match += 1
                if score_match > best_score:
                    sibling = _find_tool_record_for_call_id(records, c.get("id"))
                    if sibling:
                        best = sibling
                        best_score = score_match
            mapped = best

        # Collect for later sort: compute rerank favoring desired tool and args
        tool_name, tool_args = _get_tool_metadata_for_record(mapped, by_src)
        rerank = score
        if desired_tool and tool_name == desired_tool:
            rerank -= 0.5
        if desire_ticker and isinstance(tool_args, dict):
            t = tool_args.get("ticker") or tool_args.get("symbol")
            if isinstance(t, str) and t.strip().upper() == desire_ticker:
                rerank -= 0.4
        if desire_stmt and isinstance(tool_args, dict):
            st = tool_args.get("statement_type") or tool_args.get("statement")
            if isinstance(st, str) and st.strip().lower().replace(" ", "_") == desire_stmt:
                rerank -= 0.3
        # If seeking free_search with a ticker but args missing, fall back to text contains ticker
        if desired_tool == "free_search" and desire_ticker and desire_ticker in (mapped.get("text", "").upper()):
            rerank -= 0.15

    # After collecting all, sort by rerank and print top 1
    candidates = [id2text[int(i)] for i in I[0] if int(i) in id2text]
    # mapped info stored only in mapped variable above; rebuild mapped list with by_src
    enriched = []
    for idx_val, score_val in zip(I[0], D[0]):
        r = id2text.get(int(idx_val))
        if not r:
            continue
        m = map_to_tool_output(r, by_src)
        tool_name, tool_args = _get_tool_metadata_for_record(m, by_src)
        rerank = score_val
        if desired_tool and tool_name == desired_tool:
            rerank -= 0.5
        if desire_ticker and isinstance(tool_args, dict):
            t = tool_args.get("ticker") or tool_args.get("symbol")
            if isinstance(t, str) and t.strip().upper() == desire_ticker:
                rerank -= 0.4
        if desire_stmt and isinstance(tool_args, dict):
            st = tool_args.get("statement_type") or tool_args.get("statement")
            if isinstance(st, str) and st.strip().lower().replace(" ", "_") == desire_stmt:
                rerank -= 0.3
        if desired_tool == "free_search" and desire_ticker and desire_ticker in (m.get("text", "").upper()):
            rerank -= 0.15
        enriched.append((rerank, score_val, int(idx_val), m))

    if not enriched:
        return
    enriched.sort(key=lambda x: x[0])
    top = enriched[0:TOP_K]
    for rank, (rscore, orig, idx_val, m) in enumerate(top, start=1):
        print(
            f"{rank}. id={idx_val}  score(L2)={orig:.4f}  src={m.get('source')}#{m.get('chunk')}\n   {m.get('text')}\n"
        )

if __name__ == "__main__":
    main()
