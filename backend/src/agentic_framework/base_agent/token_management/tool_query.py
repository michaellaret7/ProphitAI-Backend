from .tool_index import build_tool_index, filter_latest
import json
import os
import re

def lookup_ticker_tool_output(tool_name: str, *, ticker: str = None, args: str = None) -> str:
    """
    Unified deterministic lookup.
    - For general tools: returns latest output text matching provided normalized args.
    - For free_search with regex_pattern: returns latest output text matching regex (optionally constrained by ticker).
    Returns None if no match.
    """
    rows = build_tool_index()

    # regex-constrained path
    if isinstance(args, str) and args:
        import re as _re
        rx = None
        try:
            rx = _re.compile(args, _re.IGNORECASE)
        except Exception:
            pass
        if rx is not None:
            for r in reversed(rows):  # newest first
                if r.get("tool_name") != tool_name:
                    continue
                if ticker and (r.get("norm", {}).get("ticker") != ticker.strip().upper()):
                    continue
                text = r.get("text", "") or ""
                if rx.search(text):
                    return text
            return None

    # generic deterministic latest
    norm_filters = {}
    if ticker:
        norm_filters["ticker"] = ticker.strip().upper()

    if norm_filters:
        row = filter_latest(rows, tool_name=tool_name, norm_filters=norm_filters)
        return None if row is None else row.get("text")

    return None

def list_tool_runs(tool_name: str, args: str = None) -> str:
    """
    Return a JSON payload of all occurrences of the given tool (most recent first).
    Schema:
    {
      "tool_name": str,
      "count": int,
      "runs": [
        { "order": int, "tool_call_id": str, "args": dict|null, "norm": dict, "output": str }
      ]
    }
    """
    rows = build_tool_index()
    matches = [r for r in rows if r.get("tool_name") == tool_name]
    # Optional regex filter against args/norm/output
    if isinstance(args, str) and args:
        import re as _re
        rx = None
        try:
            rx = _re.compile(args, _re.IGNORECASE)
        except Exception:
            rx = None
        if rx is not None:
            filtered = []
            for r in matches:
                a = json.dumps(r.get("args"), ensure_ascii=False) if r.get("args") is not None else ""
                n = json.dumps(r.get("norm", {}), ensure_ascii=False)
                t = (r.get("text") or "")
                if rx.search(a) or rx.search(n) or rx.search(t):
                    filtered.append(r)
            matches = filtered
    matches.sort(key=lambda r: r.get("order", 0), reverse=True)
    payload = {
        "tool_name": tool_name,
        "count": len(matches),
        "runs": [
            {
                "order": r.get("order"),
                "tool_call_id": r.get("tool_call_id"),
                "args": r.get("args"),
                "norm": r.get("norm", {}),
                "output": (r.get("text") or "").strip(),
            }
            for r in matches
        ],
    }
    return json.dumps(payload)

def tool_lookup(tool_name: str, *, ticker: str = None, args: str = None) -> str:
    """
    Single entry point:
    - If ticker provided: return latest ticker-scoped output (optionally regex-filtered via args).
    - If only tool_name: return JSON payload of all runs for that tool (most recent first).
    """
    if ticker:
        return lookup_ticker_tool_output(tool_name, ticker=ticker, args=args)

    return list_tool_runs(tool_name, args=args)

def tool_lookup_by_call_id(tool_call_id: str) -> str:
    """
    Return the output text for a specific tool invocation by its tool_call_id.
    - Looks up rows built from messages.json (or fallback agent_messages.json).
    - Returns the tool message text (string) or None if not found.
    """
    if not isinstance(tool_call_id, str) or not tool_call_id:
        return None
    rows = build_tool_index()
    for r in rows:
        if r.get("tool_call_id") == tool_call_id:
            return (r.get("text") or "").strip()
    return None

def list_tool_calls_condensed(
    *,
    exclude_tools: list | None = None,
    exclude_pattern: str | None = None,
    corpus_path: str | None = None,
    output: str = "lines",
) -> str:
    """
    Return all tool calls (name + args + tool_call_id) from messages.json in a condensed format.
    - Excludes planning/task tools by default; you can add excludes via exclude_tools or exclude_pattern (regex).
    - output="lines" → one line per call: name k1=v1 k2=v2 ...
      output="json"  → JSON array of {"name": str, "args": dict|null, "tool_call_id": str|null}
    """
    if corpus_path is None:
        # Default to tool_lookup/messages.json (seeded via seed_messages_json)
        here = os.path.dirname(os.path.abspath(__file__))
        corpus_path = os.path.join(here, "messages.json")

    with open(corpus_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    messages = data.get("messages") if isinstance(data, dict) else None
    if not isinstance(messages, list):
        return "" if output == "lines" else json.dumps([])

    default_excludes = {
        "create_structured_plan",
        "add_task_evidence",
        "get_current_task_info",
        "get_completion_analysis",
        "update_task_status",
        "mark_task_complete",
        "advance_to_next_task"
    }
    excludes = set(exclude_tools or []) | default_excludes
    rx = re.compile(exclude_pattern, re.IGNORECASE) if isinstance(exclude_pattern, str) and exclude_pattern else None

    records = []
    for msg in messages:
        if not isinstance(msg, dict):
            continue
        tool_calls = msg.get("tool_calls")
        if not isinstance(tool_calls, list):
            continue
        for tc in tool_calls:
            func = tc.get("function") if isinstance(tc, dict) else None
            if not isinstance(func, dict):
                continue
            name = func.get("name")
            if not name or name in excludes:
                continue
            if rx is not None and rx.search(name):
                continue
            args_raw = func.get("arguments")
            args_obj = None
            if isinstance(args_raw, str):
                try:
                    args_obj = json.loads(args_raw)
                except Exception:
                    args_obj = None
            # Redact large portfolio_dict payloads for compactness
            if isinstance(args_obj, dict) and isinstance(args_obj.get("portfolio_dict"), dict):
                args_obj = dict(args_obj)  # shallow copy
                args_obj["portfolio_dict"] = "{...}"
            tool_call_id = tc.get("id") if isinstance(tc, dict) else None
            records.append({"name": name, "args": args_obj, "tool_call_id": tool_call_id})

    if output == "json":
        return json.dumps(records)

    # lines output
    lines = []
    for r in records:
        args_obj = r.get("args") or {}
        if isinstance(args_obj, dict) and args_obj:
            parts = [f"{k}={args_obj[k]}" for k in sorted(args_obj.keys())]
            id_part = f" tool_call_id={r['tool_call_id']}" if r.get("tool_call_id") else ""
            lines.append(f"{r['name']} " + " ".join(parts) + id_part)
        else:
            id_part = f" tool_call_id={r['tool_call_id']}" if r.get("tool_call_id") else ""
            lines.append(r["name"] + id_part)
    return "\n".join(lines)



if __name__ == "__main__":
    print(tool_lookup_by_call_id("call_IqEjRoICy1UxNeyTF5kVW67b"))




