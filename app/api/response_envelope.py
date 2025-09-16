from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Union

Payload = Union[Dict[str, Any], List[Dict[str, Any]]]


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
    data = DataMeta(
        kind=kind,
        id=resource_id,
        selfLink=self_link,
        updated=updated,
        currentItemCount=(counts or {}).get("currentItemCount"),
        itemsPerPage=(counts or {}).get("itemsPerPage"),
        startIndex=(counts or {}).get("startIndex"),
        totalItems=(counts or {}).get("totalItems"),
        payload=payload,
    )
    return SuccessEnvelope(status=status, data=data, message=message).to_dict()


def error_envelope(code: int, message: str, errors: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    return ErrorEnvelope(ErrorDetails(code=code, message=message, errors=errors or [])).to_dict()


