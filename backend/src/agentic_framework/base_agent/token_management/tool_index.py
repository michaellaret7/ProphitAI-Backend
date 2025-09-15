import os
import json
import re
import hashlib
from typing import Dict, List, Tuple, Any
from backend.src.utils.file_utils import get_project_root


PROJECT_ROOT = get_project_root()
AGENT_MESSAGES_FILE = os.path.join(
    PROJECT_ROOT,
    "backend",
    "src",
    "agentic_framework",
    "agent_output",
    "agent_messages.json",
)

def _parse_assistant_tool_calls(message: Dict[str, Any]) -> List[Dict[str, Any]]:
    tool_calls = message.get("tool_calls")
    if not isinstance(tool_calls, list):
        return []
    calls: List[Dict[str, Any]] = []
    for tc in tool_calls:
        call_id = tc.get("id")
        func = tc.get("function", {}) or {}
        name = func.get("name")
        args_raw = func.get("arguments")
        args: Dict[str, Any] = None
        if isinstance(args_raw, str):
            try:
                args = json.loads(args_raw)
            except Exception:
                args = None
        calls.append({"id": call_id, "name": name, "args": args})
    return calls


def _extract_tool_call_id_from_tool_message(message: Dict[str, Any]) -> str:
    tcid = message.get("tool_call_id")
    if tcid:
        return tcid
    # Fallback: attempt to parse from text
    text = message.get("content") or ""
    try:
        m = re.search(r'"tool_call_id"\s*:\s*"([^"]+)"', text)
        return m.group(1) if m else None
    except Exception:
        return None


def normalize_args(args: Dict[str, Any]) -> Dict[str, Any]:
    norm: Dict[str, Any] = {}
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


def _extract_ticker_from_text(text: str) -> str:
    """Heuristically extract a likely ticker (A–Z, 1–5 chars) from free text.
    Skips quarter tokens like Q1..Q4 and possessives (strips trailing 's/’s).
    """
    if not text:
        return None
    candidates = re.findall(r"[A-Za-z]{1,5}(?:['’]s)?", text)
    for tok in candidates:
        base = re.sub(r"['’]s$", "", tok).upper()
        if not base:
            continue
        # skip common quarter tokens
        if base in {"Q1", "Q2", "Q3", "Q4"}:
            continue
        # letters only to avoid pure acronyms with numbers; adjust as needed
        if re.fullmatch(r"[A-Z]{1,5}", base):
            return base
    return None

def build_tool_index(
    agent_messages_path: str = AGENT_MESSAGES_FILE,
    *,
    source_path: str | None = None,
) -> List[Dict[str, Any]]:
    """
    Build deterministic tool-output rows from agent_messages.json.
    """
    # Always use tool_lookup/messages.json unless an explicit source_path is given
    if source_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        use_path = os.path.join(here, "messages.json")
        if not os.path.exists(use_path):
            raise FileNotFoundError(
                "messages.json not found in tool_lookup. Seed it first via seed_messages_json() or provide source_path."
            )
    else:
        use_path = source_path

    with open(use_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages")
    if not isinstance(messages, list):
        raise ValueError("agent_messages.json does not contain a 'messages' array")

    pending_calls: Dict[str, Dict[str, Any]] = {}
    rows: List[Dict[str, Any]] = []
    order_counter = 0

    for msg in messages:
        role = msg.get("role")
        if role == "assistant":
            for c in _parse_assistant_tool_calls(msg):
                if c.get("id"):
                    pending_calls[c["id"]] = {
                        "name": c.get("name"),
                        "args": c.get("args"),
                    }
        elif role == "tool":
            tcid = _extract_tool_call_id_from_tool_message(msg)
            if not tcid:
                order_counter += 1
                continue
            call = pending_calls.get(tcid)
            if not call:
                order_counter += 1
                continue
            tool_name = call.get("name")
            args = call.get("args")
            norm = normalize_args(args or {})
            text = msg.get("content") or ""
            row = {
                "tool_name": tool_name,
                "tool_call_id": tcid,
                "args": args,
                "norm": norm,
                "order": order_counter,
                "text": text,
            }
            # Special handling: derive ticker for free_search from its query or text
            if tool_name == "free_search" and not row["norm"].get("ticker"):
                q = (args or {}).get("query") if isinstance(args, dict) else None
                derived = _extract_ticker_from_text(q) or _extract_ticker_from_text(text)
                if derived:
                    row["norm"]["ticker"] = derived
            rows.append(row)
        order_counter += 1

    # Sort rows by order to define recency
    rows.sort(key=lambda r: r.get("order", 0))

    return rows


def filter_latest(
    rows: List[Dict[str, Any]],
    tool_name: str = None,
    norm_filters: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """Return latest row matching provided filters; None if not found."""
    norm_filters = norm_filters or {}
    best: Dict[str, Any] = None
    best_order = -1
    for r in rows:
        if tool_name and r.get("tool_name") != tool_name:
            continue
        norm = r.get("norm", {}) or {}
        matched = True
        for k, v in norm_filters.items():
            if norm.get(k) != v:
                matched = False
                break
        if not matched:
            continue
        order = r.get("order", 0)
        if order >= best_order:
            best = r
            best_order = order
    return best


# -----------------------
# Seeding helper (messages.json)
# -----------------------
def _contains_structured_plan(content: str) -> bool:
    """Best-effort check for a structured plan payload within a message.content string."""
    if not isinstance(content, str):
        return False
    try:
        inner = json.loads(content)
        if isinstance(inner, dict) and ("plan" in inner or "structed_plan" in inner):
            return True
    except Exception:
        pass
    return ("\"plan\"" in content) or ("\"structed_plan\"" in content)


def _find_plan_boundary_index(messages: List[Dict[str, Any]]) -> int:
    """Return index of the first tool message that appears to contain a structured plan result."""
    for idx, m in enumerate(messages or []):
        if isinstance(m, dict) and m.get("role") == "tool":
            if _contains_structured_plan(m.get("content")):
                return idx
    return None

def seed_messages_json(
    *,
    agent_messages_path: str = AGENT_MESSAGES_FILE,
    output_path: str | None = None,
    append: bool = False,
) -> str:
    """
    Write a trimmed messages payload to tool_lookup/messages.json (or provided output_path):
    - Keeps only messages strictly AFTER the first structured plan tool result.
    - Payload schema: { "messages": [ ... ] }
    - If append=True and output exists, merges new messages (deduped) instead of overwriting.

    Returns the absolute output path written.
    """
    if output_path is None:
        here = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(here, "messages.json")

    with open(agent_messages_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages")
    if not isinstance(messages, list):
        raise ValueError("agent_messages.json does not contain a 'messages' array")

    boundary_idx = _find_plan_boundary_index(messages)
    if boundary_idx is None:
        raise RuntimeError("Could not locate structured plan tool message in agent_messages.json")

    kept = messages[boundary_idx + 1 :]

    # Append mode: read existing and merge with dedupe
    if append and os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as f:
                existing = json.load(f)
            existing_msgs = existing.get("messages") if isinstance(existing, dict) else None
            if not isinstance(existing_msgs, list):
                existing_msgs = []
        except Exception:
            existing_msgs = []

        def _sig(m: dict) -> str:
            try:
                return hashlib.sha1(json.dumps(m, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
            except Exception:
                return hashlib.sha1(str(m).encode("utf-8")).hexdigest()

        seen = { _sig(m) for m in existing_msgs if isinstance(m, dict) }
        to_add = [m for m in kept if isinstance(m, dict) and _sig(m) not in seen]
        merged = existing_msgs + to_add
        payload = {"messages": merged}
    else:
        payload = {"messages": kept}

    # Validate serializable, then write
    _ = json.dumps(payload)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return os.path.abspath(output_path)

