"""Render.com API client with Bearer auth and exponential backoff."""

import os
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

BASE_URL = "https://api.render.com/v1"


class RenderClient:
    """HTTP client for the Render.com REST API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        owner_id: Optional[str] = None,
        project_id: Optional[str] = None,
        environment_id: Optional[str] = None,
    ):
        load_dotenv()
        self.api_key = api_key or os.getenv("RENDER_API_KEY")
        self.owner_id = owner_id or os.getenv("RENDER_OWNER_ID")
        self.project_id = project_id or os.getenv("RENDER_FUND_PROJECT_ID")
        self.environment_id = environment_id or os.getenv("RENDER_FUND_ENVIRONMENT_ID")

        if not self.api_key:
            raise ValueError(
                "Render API key required. Provide via constructor or set "
                "RENDER_API_KEY environment variable."
            )

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }
        )

    # ================================
    # --> Helper funcs
    # ================================

    def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any] | List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any] | List[Dict[str, Any]] | None:
        """Execute an HTTP request with exponential backoff on 429 rate limits."""
        url = f"{BASE_URL}{path}"
        max_retries = 5

        for attempt in range(max_retries):
            try:
                response = self._session.request(
                    method, url, params=params, json=json_body
                )

                if response.status_code == 429:
                    wait_time = 2**attempt
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                if response.status_code == 204:
                    return None

                return response.json()
            except requests.exceptions.RequestException:
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)

        return None

    # ================================
    # --> Deploys
    # ================================

    def list_deploys(
        self,
        service_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        """List deploys for a service."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._make_request("GET", f"/services/{service_id}/deploys", params=params)

    def get_deploy(
        self,
        service_id: str,
        deploy_id: str,
    ) -> Dict[str, Any] | None:
        """Retrieve details of a specific deploy."""
        return self._make_request("GET", f"/services/{service_id}/deploys/{deploy_id}")

    def trigger_deploy(
        self,
        service_id: str,
        clear_cache: bool = False,
        commit_id: Optional[str] = None,
        image_url: Optional[str] = None,
    ) -> Dict[str, Any] | None:
        """Trigger a new deploy for a service."""
        body: Dict[str, Any] = {
            "clearCache": "clear" if clear_cache else "do_not_clear",
        }
        if commit_id:
            body["commitId"] = commit_id
        if image_url:
            body["imageUrl"] = image_url
        return self._make_request("POST", f"/services/{service_id}/deploys", json_body=body)

    def cancel_deploy(
        self,
        service_id: str,
        deploy_id: str,
    ) -> Dict[str, Any] | None:
        """Cancel a running deploy."""
        return self._make_request(
            "POST", f"/services/{service_id}/deploys/{deploy_id}/cancel"
        )

    def rollback_deploy(
        self,
        service_id: str,
        deploy_id: str,
    ) -> Dict[str, Any] | None:
        """Roll back to a previous deploy."""
        return self._make_request(
            "POST",
            f"/services/{service_id}/rollback",
            json_body={"deployId": deploy_id},
        )

    # ================================
    # --> Services
    # ================================

    def list_services(
        self,
        name: Optional[str] = None,
        service_type: Optional[str] = None,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        """List services scoped to the fund environment."""
        params: Dict[str, Any] = {"limit": limit}
        if self.owner_id:
            params["ownerId"] = self.owner_id
        if self.environment_id:
            params["environmentId"] = self.environment_id
        if name:
            params["name"] = name
        if service_type:
            params["type"] = service_type
        if cursor:
            params["cursor"] = cursor
        return self._make_request("GET", "/services", params=params)

    def get_service(self, service_id: str) -> Dict[str, Any] | None:
        """Retrieve details of a specific service."""
        return self._make_request("GET", f"/services/{service_id}")

    def create_service(self, config: Dict[str, Any]) -> Dict[str, Any] | None:
        """Create a new service scoped to the fund environment."""
        # Reason: enforce fund environment boundary on all created services
        if self.environment_id:
            config["environmentId"] = self.environment_id
        return self._make_request("POST", "/services", json_body=config)

    def update_service(
        self, service_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any] | None:
        """Update a service configuration. Client-only — not exposed as agent tool."""
        return self._make_request("PATCH", f"/services/{service_id}", json_body=config)

    def delete_service(self, service_id: str) -> Dict[str, Any] | None:
        """Delete a service permanently. Client-only — not exposed as agent tool."""
        return self._make_request("DELETE", f"/services/{service_id}")

    def suspend_service(self, service_id: str) -> Dict[str, Any] | None:
        """Suspend a running service."""
        return self._make_request("POST", f"/services/{service_id}/suspend")

    def resume_service(self, service_id: str) -> Dict[str, Any] | None:
        """Resume a suspended service."""
        return self._make_request("POST", f"/services/{service_id}/resume")

    def restart_service(self, service_id: str) -> Dict[str, Any] | None:
        """Restart a service without redeploying."""
        return self._make_request("POST", f"/services/{service_id}/restart")

    # ================================
    # --> Environment Variables
    # ================================

    def list_env_vars(
        self,
        service_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        """List all environment variables for a service."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._make_request(
            "GET", f"/services/{service_id}/env-vars", params=params
        )

    def set_env_var(
        self, service_id: str, key: str, value: str
    ) -> Dict[str, Any] | None:
        """Add or update a single environment variable."""
        return self._make_request(
            "PUT",
            f"/services/{service_id}/env-vars/{key}",
            json_body={"value": value},
        )

    def delete_env_var(self, service_id: str, key: str) -> Dict[str, Any] | None:
        """Delete an environment variable."""
        return self._make_request(
            "DELETE", f"/services/{service_id}/env-vars/{key}"
        )

    def bulk_update_env_vars(
        self, service_id: str, env_vars: List[Dict[str, str]]
    ) -> List[Dict[str, Any]] | None:
        """Full replacement of all env vars. Client-only — not exposed as agent tool."""
        return self._make_request(
            "PUT", f"/services/{service_id}/env-vars", json_body=env_vars
        )

    # ================================
    # --> Instances
    # ================================

    def list_instances(
        self,
        service_id: str,
        limit: int = 20,
        cursor: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        """List running instances for a service."""
        params: Dict[str, Any] = {"limit": limit}
        if cursor:
            params["cursor"] = cursor
        return self._make_request(
            "GET", f"/services/{service_id}/instances", params=params
        )

    # ================================
    # --> Logs
    # ================================

    def list_logs(
        self,
        resource_id: str,
        direction: str = "backward",
        limit: int = 100,
        level: Optional[List[str]] = None,
        text: Optional[List[str]] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        instance_id: Optional[str] = None,
        host: Optional[str] = None,
    ) -> List[Dict[str, Any]] | None:
        """Pull recent logs for a resource (service, database, or Redis)."""
        if not self.owner_id:
            return None

        params: Dict[str, Any] = {
            "ownerId": self.owner_id,
            "resource": resource_id,
            "direction": direction,
            "limit": limit,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if level:
            params["level"] = level
        if text:
            params["text"] = text
        if instance_id:
            params["instance"] = instance_id
        if host:
            params["host"] = host

        return self._make_request("GET", "/logs", params=params)

    def get_log_label_values(
        self,
        resource_id: str,
        label_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> List[str] | None:
        """Get available values for a log label (e.g. level, instance, host)."""
        if not self.owner_id:
            return None

        params: Dict[str, Any] = {
            "ownerId": self.owner_id,
            "resource": resource_id,
            "labelName": label_name,
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        return self._make_request("GET", "/logs/label-values", params=params)


# ================================
# --> Singleton
# ================================

_render_instance: Optional[RenderClient] = None


def get_render_client() -> RenderClient:
    """Return a lazy-initialised RenderClient singleton."""
    global _render_instance
    if _render_instance is None:
        _render_instance = RenderClient()
    return _render_instance
