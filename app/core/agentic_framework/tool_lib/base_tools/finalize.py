from typing import Optional
import yaml


def finalize(answer: str, *, meta: Optional[dict] = None) -> str:
    """Return a structured payload containing the final answer.

    The execution loop will treat a call to this tool as a termination signal.
    """
    payload = {
        "success": True,
        "data": {
            "answer": (answer or "").strip(),
            "meta": meta or {},
        },
    }
    return yaml.dump(payload, default_flow_style=False, sort_keys=False)


FINALIZE_DESCRIPTION = (
    "CRITICAL: This is the ONLY tool to use when you are DONE and ready to deliver the final answer. "
    "Calling this tool TERMINATES the run. Do not summarize or continue planning afterwards. "
    "Provide the COMPLETE final answer as a single string in the 'answer' field."
)

FINALIZE_PARAMETERS = {
    "type": "object",
    "properties": {
        "answer": {
            "type": "string",
            "description": "The complete final answer to return to the user.",
        },
        "meta": {
            "type": "object",
            "description": "Optional metadata to include with the final answer (e.g., scores).",
            "additionalProperties": True,
        },
    },
    "required": ["answer"],
}


