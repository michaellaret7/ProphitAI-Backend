"""Pydantic response models for the Render.com API."""

from typing import Any, Dict, Optional

from pydantic import BaseModel


# ================================
# --> Helper funcs
# ================================


def _safe_get(data: Dict[str, Any], key: str, default: Any = "") -> Any:
    """Safely extract a value from a dict, returning *default* when missing."""
    return data.get(key, default)


# ================================
# --> Models
# ================================


class RenderService(BaseModel):
    """Render service resource."""

    model_config = {"frozen": True}

    id: str
    name: str
    type: str
    repo: str
    branch: str
    auto_deploy: bool
    suspended: str
    dashboard_url: str
    owner_id: str
    created_at: str
    updated_at: str

    @staticmethod
    def from_raw(data: Dict[str, Any]) -> "RenderService":
        """Create from raw API response, handling nested ``service`` wrapper."""
        svc = data.get("service", data)
        return RenderService(
            id=_safe_get(svc, "id"),
            name=_safe_get(svc, "name"),
            type=_safe_get(svc, "type"),
            repo=_safe_get(svc, "repo"),
            branch=_safe_get(svc, "branch"),
            auto_deploy=_safe_get(svc, "autoDeploy", "no") == "yes",
            suspended=_safe_get(svc, "suspended", "not_suspended"),
            dashboard_url=_safe_get(svc, "dashboardUrl"),
            owner_id=_safe_get(svc, "ownerId"),
            created_at=_safe_get(svc, "createdAt"),
            updated_at=_safe_get(svc, "updatedAt"),
        )


class RenderDeploy(BaseModel):
    """Render deploy resource."""

    model_config = {"frozen": True}

    id: str
    status: str
    commit_id: str
    commit_message: str
    trigger: str
    created_at: str
    updated_at: str
    finished_at: Optional[str] = None

    @staticmethod
    def from_raw(data: Dict[str, Any]) -> "RenderDeploy":
        """Create from raw API response, handling nested ``deploy`` wrapper."""
        dep = data.get("deploy", data)
        commit = dep.get("commit") or {}
        return RenderDeploy(
            id=_safe_get(dep, "id"),
            status=_safe_get(dep, "status"),
            commit_id=_safe_get(commit, "id"),
            commit_message=_safe_get(commit, "message"),
            trigger=_safe_get(dep, "trigger"),
            created_at=_safe_get(dep, "createdAt"),
            updated_at=_safe_get(dep, "updatedAt"),
            finished_at=dep.get("finishedAt"),
        )


class RenderEnvVar(BaseModel):
    """Render environment variable."""

    model_config = {"frozen": True}

    key: str
    value: str

    @staticmethod
    def from_raw(data: Dict[str, Any]) -> "RenderEnvVar":
        """Create from raw API response, handling nested ``envVar`` wrapper."""
        ev = data.get("envVar", data)
        return RenderEnvVar(
            key=_safe_get(ev, "key"),
            value=_safe_get(ev, "value"),
        )


class RenderInstance(BaseModel):
    """Render service instance."""

    model_config = {"frozen": True}

    id: str
    created_at: str

    @staticmethod
    def from_raw(data: Dict[str, Any]) -> "RenderInstance":
        """Create from raw API response, handling nested ``instance`` wrapper."""
        inst = data.get("instance", data)
        return RenderInstance(
            id=_safe_get(inst, "id"),
            created_at=_safe_get(inst, "createdAt"),
        )


class RenderLogEntry(BaseModel):
    """Single log entry from the Render logs API."""

    model_config = {"frozen": True}

    id: str
    timestamp: str
    level: str
    message: str

    @staticmethod
    def from_raw(data: Any) -> "RenderLogEntry":
        """Create from raw API response.

        The logs endpoint can return dicts or raw strings depending on
        the log type, so we handle both.
        """
        if isinstance(data, str):
            return RenderLogEntry(id="", timestamp="", level="", message=data)
        if not isinstance(data, dict):
            return RenderLogEntry(id="", timestamp="", level="", message=str(data))
        return RenderLogEntry(
            id=_safe_get(data, "id"),
            timestamp=_safe_get(data, "timestamp"),
            level=_safe_get(data, "level"),
            message=_safe_get(data, "message"),
        )
