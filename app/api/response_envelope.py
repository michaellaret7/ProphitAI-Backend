from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union
import math

Payload = Union[Dict[str, Any], List[Dict[str, Any]]]


def sanitize_nan_values(obj: Any) -> Any:
    """
    Recursively convert NaN and Infinity values to None for JSON compliance.

    Reason: Python's json.dumps() with allow_nan=False (used by FastAPI/Starlette)
    raises ValueError when encountering NaN/Inf values. This sanitizer ensures
    all numeric edge cases are converted to JSON-compliant None (null in JSON).
    """
    if obj is None:
        return None

    # Handle numeric types (including numpy types)
    if isinstance(obj, (int, float)):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # Handle numpy numeric types
    try:
        import numpy as np
        if isinstance(obj, (np.floating, np.integer, np.number)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            # Convert to Python native type for JSON serialization
            if isinstance(obj, np.integer):
                return int(obj)
            return float(obj)
    except ImportError:
        pass  # numpy not available, skip numpy checks

    # Recursively handle dictionaries
    if isinstance(obj, dict):
        return {key: sanitize_nan_values(value) for key, value in obj.items()}

    # Recursively handle lists/tuples
    if isinstance(obj, (list, tuple)):
        return [sanitize_nan_values(item) for item in obj]

    # Return other types as-is
    return obj


@dataclass
class DataMeta:
    kind: Optional[str] = None
    id: Optional[str] = None
    selfLink: Optional[str] = None
    updated: Optional[str] = None  # RFC3339
    currentItemCount: Optional[int] = None
    itemsPerPage: Optional[int] = None
    startIndex: Optional[int] = None
    totalItems: Optional[int] = None
    payload: Optional[Payload] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return {k: v for k, v in data.items() if v not in (None, [], {})}


@dataclass
class SuccessEnvelope:
    status: int
    data: DataMeta
    message: str = "OK"

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "data": self.data.to_dict(), "message": self.message}


@dataclass
class ErrorDetails:
    code: int
    message: str
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ErrorEnvelope:
    error: ErrorDetails

    def to_dict(self) -> Dict[str, Any]:
        return {"error": asdict(self.error)}


def ok_envelope(
    *,
    kind: Optional[str] = None,
    resource_id: Optional[str] = None,
    self_link: Optional[str] = None,
    updated: Optional[str] = None,
    counts: Optional[Dict[str, int]] = None,
    payload: Optional[Payload] = None,
    message: str = "OK",
    status: int = 200,
) -> Dict[str, Any]:
    # Reason: Sanitize payload to convert NaN/Inf to None for JSON compliance
    sanitized_payload = sanitize_nan_values(payload) if payload is not None else None

    data = DataMeta(
        kind=kind,
        id=resource_id,
        selfLink=self_link,
        updated=updated,
        currentItemCount=(counts or {}).get("currentItemCount"),
        itemsPerPage=(counts or {}).get("itemsPerPage"),
        startIndex=(counts or {}).get("startIndex"),
        totalItems=(counts or {}).get("totalItems"),
        payload=sanitized_payload,
    )
    return SuccessEnvelope(status=status, data=data, message=message).to_dict()


def error_envelope(code: int, message: str, errors: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return ErrorEnvelope(ErrorDetails(code=code, message=message, errors=errors or [])).to_dict()


