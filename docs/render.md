# Render API — Tier 1 Endpoint Reference

> **Base URL:** `https://api.render.com/v1`
>
> **Authentication:** Bearer token in the `Authorization` header
> ```
> Authorization: Bearer rnd_xxxxxxxxxxxxx
> ```
>
> **Pagination:** List endpoints return paginated results. Use `cursor` (from previous response) and `limit` (1–100, default 20) query params.
>
> **Rate Limiting:** Requests that exceed the rate limit return `429`. Implement exponential backoff.

---

## 1. DEPLOYS

### 1.1 List Deploys

```
GET /services/{serviceId}/deploys
```

List deploys matching the provided filters. If no filters are provided, all deploys for the service are returned.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `status` | array of strings | No | Filter for deploys with the specified statuses. Values: `created`, `queued`, `build_in_progress`, `update_in_progress`, `live`, `deactivated`, `build_failed`, `update_failed`, `canceled`, `pre_deploy_in_progress`, `pre_deploy_failed` |
| `createdBefore` | string (ISO 8601) | No | Filter for deploys created before this timestamp |
| `createdAfter` | string (ISO 8601) | No | Filter for deploys created after this timestamp |
| `updatedBefore` | string (ISO 8601) | No | Filter for deploys updated before this timestamp |
| `updatedAfter` | string (ISO 8601) | No | Filter for deploys updated after this timestamp |
| `finishedBefore` | string (ISO 8601) | No | Filter for deploys finished before this timestamp |
| `finishedAfter` | string (ISO 8601) | No | Filter for deploys finished after this timestamp |
| `cursor` | string | No | Pagination cursor from previous response |
| `limit` | integer (1–100) | No | Max items to return. Default: 20 |

**Response (200):** Array of deploy wrapper objects

```json
[
  {
    "deploy": {
      "id": "dep-xxxxxxxxxxxxx",
      "commit": {
        "id": "abc123def456",
        "message": "fix: resolve login bug",
        "createdAt": "2026-03-27T13:45:02.906Z"
      },
      "image": {
        "ref": "docker.io/myorg/myimage:latest",
        "sha": "sha256:abc123...",
        "registryCredential": "string"
      },
      "status": "live",
      "trigger": "api",
      "startedAt": "2026-03-27T13:45:02.906Z",
      "finishedAt": "2026-03-27T13:47:02.906Z",
      "createdAt": "2026-03-27T13:45:02.906Z",
      "updatedAt": "2026-03-27T13:47:02.906Z"
    },
    "cursor": "string"
  }
]
```

---

### 1.2 Trigger Deploy

```
POST /services/{serviceId}/deploys
```

Trigger a new deploy for the specified service.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `clearCache` | string | No | Set to `"clear"` to clear build cache before deploying. Values: `clear`, `do_not_clear` |
| `commitId` | string | No | SHA of a specific Git commit to deploy. Defaults to latest commit on connected branch. Does not disable autodeploys. Not supported for cron jobs. |
| `imageUrl` | string | No | URL of the image to deploy (for image-backed services only) |

**Example Request Body:**

```json
{
  "clearCache": "do_not_clear",
  "commitId": "abc123def456"
}
```

**Response (201):** Deploy object (same schema as individual item in List Deploys response)

---

### 1.3 Retrieve Deploy

```
GET /services/{serviceId}/deploys/{deployId}
```

Retrieve details of a specific deploy.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |
| `deployId` | string | Yes | The ID of the deploy |

**Response (200):** Single deploy object

```json
{
  "id": "dep-xxxxxxxxxxxxx",
  "commit": {
    "id": "abc123def456",
    "message": "fix: resolve login bug",
    "createdAt": "2026-03-27T13:45:02.906Z"
  },
  "status": "live",
  "trigger": "api",
  "startedAt": "2026-03-27T13:45:02.906Z",
  "finishedAt": "2026-03-27T13:47:02.906Z",
  "createdAt": "2026-03-27T13:45:02.906Z",
  "updatedAt": "2026-03-27T13:47:02.906Z"
}
```

---

### 1.4 Cancel Deploy

```
POST /services/{serviceId}/deploys/{deployId}/cancel
```

Cancel a running deploy.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |
| `deployId` | string | Yes | The ID of the deploy to cancel |

**Request Body:** None

**Response (200):** The canceled deploy object

---

### 1.5 Roll Back Deploy

```
POST /services/{serviceId}/rollback
```

Roll back to a previous deploy.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `deployId` | string | Yes | The ID of the deploy to roll back to |

**Example Request Body:**

```json
{
  "deployId": "dep-xxxxxxxxxxxxx"
}
```

**Response (200):** The newly created rollback deploy object

---

### Deploy Status Values Reference

| Status | Description |
|--------|-------------|
| `created` | Deploy has been created but not yet started |
| `queued` | Deploy is queued waiting to start |
| `build_in_progress` | Build step is running |
| `update_in_progress` | Service is being updated with the new build |
| `live` | Deploy is live and serving traffic |
| `deactivated` | Deploy has been superseded by a newer deploy |
| `build_failed` | Build step failed |
| `update_failed` | Service update step failed |
| `canceled` | Deploy was canceled |
| `pre_deploy_in_progress` | Pre-deploy command is running |
| `pre_deploy_failed` | Pre-deploy command failed |

### Deploy Trigger Values Reference

| Trigger | Description |
|---------|-------------|
| `api` | Triggered via the API |
| `blueprint_sync` | Triggered by a Blueprint sync |
| `deploy_hook` | Triggered by a deploy hook URL |
| `deployed_by_render` | Triggered automatically by Render |
| `manual` | Triggered manually from the Dashboard |
| `new_commit` | Triggered by a new commit (autodeploy) |
| `rollback` | Triggered by a rollback |
| `service_resumed` | Triggered by resuming a suspended service |
| `service_updated` | Triggered by updating the service config |
| `other` | Other trigger |

---

## 2. SERVICES

### 2.1 List Services

```
GET /services
```

List all services in your workspace.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | array of strings | No | Filter by service name |
| `type` | array of strings | No | Filter by service type. Values: `static_site`, `web_service`, `private_service`, `background_worker`, `cron_job` |
| `env` | array of strings | No | Filter by runtime (deprecated; use `runtime` instead) |
| `region` | array of strings | No | Filter by region |
| `suspended` | array of strings | No | Filter by suspended status. Values: `suspended`, `not_suspended` |
| `createdBefore` | string (ISO 8601) | No | Filter for services created before this timestamp |
| `createdAfter` | string (ISO 8601) | No | Filter for services created after this timestamp |
| `updatedBefore` | string (ISO 8601) | No | Filter for services updated before this timestamp |
| `updatedAfter` | string (ISO 8601) | No | Filter for services updated after this timestamp |
| `ownerId` | array of strings | No | Filter by workspace/owner ID |
| `environmentId` | array of strings | No | Filter by environment ID |
| `cursor` | string | No | Pagination cursor |
| `limit` | integer (1–100) | No | Max items to return. Default: 20 |

**Response (200):** Array of service wrapper objects

```json
[
  {
    "service": {
      "id": "srv-xxxxxxxxxxxxx",
      "autoDeploy": "yes",
      "branch": "main",
      "createdAt": "2026-03-27T13:45:02.906Z",
      "dashboardUrl": "https://dashboard.render.com/web/srv-xxxxxxxxxxxxx",
      "environmentId": "string",
      "imagePath": "string",
      "name": "my-web-service",
      "ownerId": "own-xxxxxxxxxxxxx",
      "repo": "https://github.com/myorg/myrepo",
      "rootDir": "./",
      "slug": "my-web-service",
      "suspended": "not_suspended",
      "suspenders": [],
      "type": "web_service",
      "updatedAt": "2026-03-27T13:45:02.906Z",
      "serviceDetails": { ... }
    },
    "cursor": "string"
  }
]
```

---

### 2.2 Create Service

```
POST /services
```

Create a new service.

**Request Body (JSON):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | **Yes** | Service type. Values: `static_site`, `web_service`, `private_service`, `background_worker`, `cron_job` |
| `name` | string | **Yes** | Service name. Must be unique within the workspace. |
| `ownerId` | string | **Yes** | Workspace ID. Get from Dashboard Settings. |
| `repo` | string | No | Repository URL. Do not include branch in this string. |
| `autoDeploy` | string | No | Enable autodeploy on new commits. Values: `yes`, `no` |
| `branch` | string | No | Git branch to pull and deploy. Defaults to repo's default branch. |
| `image` | object | No | Image config for image-backed services. Contains `ownerId`, `registryCredentialId`, `imagePath`. |
| `buildFilter` | object | No | Build filter configuration. |
| `rootDir` | string | No | Root directory of the service within the repo. |
| `envVars` | array | No | Array of `{key, value}` pairs for environment variables. |
| `secretFiles` | array | No | Array of secret files. |
| `serviceDetails` | object | No | Type-specific config (varies by service type — see below). |

**serviceDetails by service type:**

For `web_service` / `private_service` / `background_worker`:
```json
{
  "serviceDetails": {
    "env": "docker",
    "envSpecificDetails": {
      "dockerCommand": "npm start",
      "dockerContext": ".",
      "dockerfilePath": "./Dockerfile"
    },
    "plan": "starter",
    "region": "oregon",
    "numInstances": 1,
    "healthCheckPath": "/health",
    "pullRequestPreviewsEnabled": "no"
  }
}
```

For `static_site`:
```json
{
  "serviceDetails": {
    "buildCommand": "npm run build",
    "publishPath": "./build",
    "pullRequestPreviewsEnabled": "no"
  }
}
```

For `cron_job`:
```json
{
  "serviceDetails": {
    "env": "docker",
    "envSpecificDetails": {
      "dockerCommand": "python job.py",
      "dockerContext": ".",
      "dockerfilePath": "./Dockerfile"
    },
    "plan": "starter",
    "region": "oregon",
    "schedule": "0 * * * *"
  }
}
```

**Example — Create a Docker-backed web service:**

```json
{
  "type": "web_service",
  "name": "my-api",
  "ownerId": "own-xxxxxxxxxxxxx",
  "repo": "https://github.com/myorg/myrepo",
  "branch": "main",
  "autoDeploy": "yes",
  "serviceDetails": {
    "env": "docker",
    "envSpecificDetails": {
      "dockerCommand": "",
      "dockerContext": ".",
      "dockerfilePath": "./Dockerfile"
    },
    "plan": "starter",
    "region": "oregon",
    "numInstances": 1,
    "healthCheckPath": "/health"
  },
  "envVars": [
    {"key": "NODE_ENV", "value": "production"},
    {"key": "PORT", "value": "3000"}
  ]
}
```

**Response (201):** The created service object

---

### 2.3 Retrieve Service

```
GET /services/{serviceId}
```

Get details of a specific service.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Response (200):** Service object (same schema as individual item in List Services)

---

### 2.4 Update Service

```
PATCH /services/{serviceId}
```

Update an existing service's configuration. Only include the fields you want to change.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body (JSON) — all fields optional:**

| Field | Type | Description |
|-------|------|-------------|
| `autoDeploy` | string | Values: `yes`, `no` |
| `branch` | string | Git branch |
| `image` | object | Image config for image-backed services |
| `name` | string | Service name |
| `repo` | string | Repository URL |
| `rootDir` | string | Root directory path |
| `buildFilter` | object | Build filter config |
| `serviceDetails` | object | Type-specific config (same structure as Create, but all fields optional) |

**Example — Update branch and disable autodeploy:**

```json
{
  "branch": "staging",
  "autoDeploy": "no"
}
```

**Response (200):** The updated service object

---

### 2.5 Delete Service

```
DELETE /services/{serviceId}
```

Delete a service permanently.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Response (204):** No content

---

### 2.6 Suspend Service

```
POST /services/{serviceId}/suspend
```

Suspend a running service. The service will stop serving traffic and you will no longer be billed for it.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body:** None

**Response (200):** Empty or confirmation

---

### 2.7 Resume Service

```
POST /services/{serviceId}/resume
```

Resume a suspended service. This triggers a new deploy.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body:** None

**Response (200):** Empty or confirmation

---

### 2.8 Restart Service

```
POST /services/{serviceId}/restart
```

Restart a running service without triggering a new build/deploy.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body:** None

**Response (200):** Empty or confirmation

---

## 3. ENVIRONMENT VARIABLES

### 3.1 List Environment Variables

```
GET /services/{serviceId}/env-vars
```

List all environment variables for a service.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | string | No | Pagination cursor |
| `limit` | integer (1–100) | No | Max items to return. Default: 20 |

**Response (200):** Array of env var wrapper objects

```json
[
  {
    "envVar": {
      "key": "NODE_ENV",
      "value": "production"
    },
    "cursor": "string"
  }
]
```

---

### 3.2 Update Environment Variables (Bulk)

```
PUT /services/{serviceId}/env-vars
```

Replace all environment variables for a service. This is a **full replacement** — any env vars not included in the request body will be removed.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Request Body (JSON):** Array of env var objects

```json
[
  {"key": "NODE_ENV", "value": "production"},
  {"key": "PORT", "value": "3000"},
  {"key": "DATABASE_URL", "value": "postgres://user:pass@host:5432/db"}
]
```

Each object in the array:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `key` | string | Yes | The environment variable name |
| `value` | string | Yes | The environment variable value |

**Response (200):** Array of the updated env var objects

---

### 3.3 Add or Update Environment Variable

```
PUT /services/{serviceId}/env-vars/{envVarKey}
```

Add a new env var or update an existing one by key.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |
| `envVarKey` | string | Yes | The key of the environment variable |

**Request Body (JSON):**

```json
{
  "value": "new-value-here"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `value` | string | Yes | The new value for the env var |

**Response (200):** The updated env var object

---

### 3.4 Delete Environment Variable

```
DELETE /services/{serviceId}/env-vars/{envVarKey}
```

Delete a specific environment variable.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |
| `envVarKey` | string | Yes | The key of the environment variable to delete |

**Response (204):** No content

---

## 4. INSTANCES

### 4.1 List Instances

```
GET /services/{serviceId}/instances
```

List all running instances for a service.

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `serviceId` | string | Yes | The ID of the service |

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `cursor` | string | No | Pagination cursor |
| `limit` | integer (1–100) | No | Max items to return. Default: 20 |

**Response (200):** Array of instance objects

```json
[
  {
    "instance": {
      "id": "inst-xxxxxxxxxxxxx",
      "createdAt": "2026-03-27T13:45:02.906Z"
    },
    "cursor": "string"
  }
]
```

---

## 5. LOGS

### 5.1 List Logs

```
GET /logs
```

Pull recent logs for one or more resources. Use this to diagnose deploy failures or verify app health.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ownerId` | string | **Yes** | The ID of the workspace to return logs for |
| `resource` | array of strings | **Yes** | Filter logs by resource. A resource is a service ID (e.g., `srv-xxxxxxxxxxxxx`), a Postgres ID, or a Redis ID. |
| `startTime` | string (ISO 8601) | No | Start of time range. Defaults to `now() - 1 hour`. |
| `endTime` | string (ISO 8601) | No | End of time range. Defaults to `now()`. |
| `direction` | string | No | Direction to query. `backward` (default) returns most recent first. `forward` starts with oldest. Values: `forward`, `backward` |
| `level` | array of strings | No | Filter by log level |
| `text` | array of strings | No | Filter logs containing this text |
| `host` | array of strings | No | Filter by host |
| `statusCode` | array of strings | No | Filter by HTTP status code |
| `method` | array of strings | No | Filter by HTTP method |
| `path` | array of strings | No | Filter by HTTP path |
| `type` | array of strings | No | Filter by log type |
| `instance` | array of strings | No | Filter by instance ID |
| `limit` | integer | No | Max log entries to return |

**Example Request:**

```
GET /logs?ownerId=own-xxxxx&resource=srv-xxxxx&direction=backward&limit=100
```

**Response (200):** Array of log entry objects

```json
[
  {
    "id": "log-xxxxx",
    "timestamp": "2026-03-27T13:45:02.906Z",
    "level": "info",
    "message": "Server listening on port 3000",
    "resource": "srv-xxxxxxxxxxxxx",
    "instance": "inst-xxxxxxxxxxxxx",
    "host": "my-web-service",
    "type": "app"
  }
]
```

---

### 5.2 Subscribe to New Logs

```
GET /logs/subscribe
```

Stream logs in real-time via Server-Sent Events (SSE). Use this to monitor a deploy as it happens.

**Query Parameters:** Same as List Logs (see 5.1), with these differences:

- Connection stays open and streams new log entries as they arrive
- Uses SSE protocol — handle the event stream accordingly in your client

**Example Request:**

```
GET /logs/subscribe?ownerId=own-xxxxx&resource=srv-xxxxx
```

**Response:** SSE stream of log entry objects

---

### 5.3 List Log Label Values

```
GET /logs/label-values
```

Discover available log sources and label values so your agent knows what to filter on (e.g., which instance IDs, which hosts, which service types).

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `ownerId` | string | **Yes** | The ID of the workspace |
| `resource` | array of strings | **Yes** | Filter by resource (service IDs) |
| `startTime` | string (ISO 8601) | No | Start of time range |
| `endTime` | string (ISO 8601) | No | End of time range |
| `labelName` | string | **Yes** | The label to get values for (e.g., `host`, `instance`, `level`, `type`, `statusCode`, `method`, `path`) |

**Example Request:**

```
GET /logs/label-values?ownerId=own-xxxxx&resource=srv-xxxxx&labelName=level
```

**Response (200):** Array of available values for the specified label

---

## Common Error Responses

All endpoints may return the following error codes:

| Code | Description |
|------|-------------|
| `401` | Authorization information is missing or invalid |
| `403` | You do not have permissions for the requested resource |
| `404` | Unable to find the requested resource |
| `406` | Unable to generate preferred media types as specified by Accept header |
| `410` | The requested resource is no longer available |
| `429` | Rate limit has been surpassed — implement backoff and retry |
| `500` | Unexpected server error |
| `503` | Server currently unavailable |

---

## Python SDK Usage Pattern

Here's the recommended pattern for your Python wrapper functions:

```python
import requests
from typing import Optional

BASE_URL = "https://api.render.com/v1"

class RenderClient:
    def __init__(self, api_key: str):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        })

    def _request(self, method: str, path: str, **kwargs):
        resp = self.session.request(method, f"{BASE_URL}{path}", **kwargs)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    # --- DEPLOYS ---

    def list_deploys(self, service_id: str, status: list[str] = None,
                     limit: int = 20, cursor: str = None) -> list:
        params = {"limit": limit}
        if status: params["status"] = status
        if cursor: params["cursor"] = cursor
        return self._request("GET", f"/services/{service_id}/deploys", params=params)

    def trigger_deploy(self, service_id: str, clear_cache: str = None,
                       commit_id: str = None, image_url: str = None) -> dict:
        body = {}
        if clear_cache: body["clearCache"] = clear_cache
        if commit_id: body["commitId"] = commit_id
        if image_url: body["imageUrl"] = image_url
        return self._request("POST", f"/services/{service_id}/deploys", json=body)

    def retrieve_deploy(self, service_id: str, deploy_id: str) -> dict:
        return self._request("GET", f"/services/{service_id}/deploys/{deploy_id}")

    def cancel_deploy(self, service_id: str, deploy_id: str) -> dict:
        return self._request("POST", f"/services/{service_id}/deploys/{deploy_id}/cancel")

    def rollback_deploy(self, service_id: str, deploy_id: str) -> dict:
        return self._request("POST", f"/services/{service_id}/rollback",
                             json={"deployId": deploy_id})

    # --- SERVICES ---

    def list_services(self, name: list[str] = None, type: list[str] = None,
                      region: list[str] = None, suspended: list[str] = None,
                      owner_id: list[str] = None, limit: int = 20,
                      cursor: str = None) -> list:
        params = {"limit": limit}
        if name: params["name"] = name
        if type: params["type"] = type
        if region: params["region"] = region
        if suspended: params["suspended"] = suspended
        if owner_id: params["ownerId"] = owner_id
        if cursor: params["cursor"] = cursor
        return self._request("GET", "/services", params=params)

    def create_service(self, type: str, name: str, owner_id: str,
                       repo: str = None, branch: str = None,
                       auto_deploy: str = "yes",
                       service_details: dict = None,
                       env_vars: list[dict] = None) -> dict:
        body = {"type": type, "name": name, "ownerId": owner_id}
        if repo: body["repo"] = repo
        if branch: body["branch"] = branch
        body["autoDeploy"] = auto_deploy
        if service_details: body["serviceDetails"] = service_details
        if env_vars: body["envVars"] = env_vars
        return self._request("POST", "/services", json=body)

    def retrieve_service(self, service_id: str) -> dict:
        return self._request("GET", f"/services/{service_id}")

    def update_service(self, service_id: str, **kwargs) -> dict:
        body = {}
        field_map = {
            "auto_deploy": "autoDeploy",
            "branch": "branch",
            "name": "name",
            "repo": "repo",
            "root_dir": "rootDir",
            "image": "image",
            "build_filter": "buildFilter",
            "service_details": "serviceDetails"
        }
        for py_key, api_key in field_map.items():
            if py_key in kwargs and kwargs[py_key] is not None:
                body[api_key] = kwargs[py_key]
        return self._request("PATCH", f"/services/{service_id}", json=body)

    def delete_service(self, service_id: str) -> None:
        return self._request("DELETE", f"/services/{service_id}")

    def suspend_service(self, service_id: str) -> dict:
        return self._request("POST", f"/services/{service_id}/suspend")

    def resume_service(self, service_id: str) -> dict:
        return self._request("POST", f"/services/{service_id}/resume")

    def restart_service(self, service_id: str) -> dict:
        return self._request("POST", f"/services/{service_id}/restart")

    # --- ENVIRONMENT VARIABLES ---

    def list_env_vars(self, service_id: str, limit: int = 20,
                      cursor: str = None) -> list:
        params = {"limit": limit}
        if cursor: params["cursor"] = cursor
        return self._request("GET", f"/services/{service_id}/env-vars", params=params)

    def update_env_vars(self, service_id: str,
                        env_vars: list[dict]) -> list:
        """Full replacement of all env vars. Pass list of {key, value} dicts."""
        return self._request("PUT", f"/services/{service_id}/env-vars", json=env_vars)

    def set_env_var(self, service_id: str, key: str, value: str) -> dict:
        return self._request("PUT", f"/services/{service_id}/env-vars/{key}",
                             json={"value": value})

    def delete_env_var(self, service_id: str, key: str) -> None:
        return self._request("DELETE", f"/services/{service_id}/env-vars/{key}")

    # --- INSTANCES ---

    def list_instances(self, service_id: str, limit: int = 20,
                       cursor: str = None) -> list:
        params = {"limit": limit}
        if cursor: params["cursor"] = cursor
        return self._request("GET", f"/services/{service_id}/instances", params=params)

    # --- LOGS ---

    def list_logs(self, owner_id: str, resource: list[str],
                  start_time: str = None, end_time: str = None,
                  direction: str = "backward", level: list[str] = None,
                  text: list[str] = None, instance: list[str] = None,
                  limit: int = None) -> list:
        params = {"ownerId": owner_id, "resource": resource, "direction": direction}
        if start_time: params["startTime"] = start_time
        if end_time: params["endTime"] = end_time
        if level: params["level"] = level
        if text: params["text"] = text
        if instance: params["instance"] = instance
        if limit: params["limit"] = limit
        return self._request("GET", "/logs", params=params)

    def subscribe_logs(self, owner_id: str, resource: list[str],
                       start_time: str = None) -> requests.Response:
        """Returns a streaming response (SSE). Iterate over response.iter_lines()."""
        params = {"ownerId": owner_id, "resource": resource}
        if start_time: params["startTime"] = start_time
        return self.session.get(f"{BASE_URL}/logs/subscribe",
                                params=params, stream=True)

    def list_log_label_values(self, owner_id: str, resource: list[str],
                              label_name: str, start_time: str = None,
                              end_time: str = None) -> list:
        params = {
            "ownerId": owner_id,
            "resource": resource,
            "labelName": label_name
        }
        if start_time: params["startTime"] = start_time
        if end_time: params["endTime"] = end_time
        return self._request("GET", "/logs/label-values", params=params)
```

---

## Quick Reference Card

| Action | Method | Endpoint |
|--------|--------|----------|
| List deploys | `GET` | `/services/{serviceId}/deploys` |
| Trigger deploy | `POST` | `/services/{serviceId}/deploys` |
| Retrieve deploy | `GET` | `/services/{serviceId}/deploys/{deployId}` |
| Cancel deploy | `POST` | `/services/{serviceId}/deploys/{deployId}/cancel` |
| Roll back deploy | `POST` | `/services/{serviceId}/rollback` |
| List services | `GET` | `/services` |
| Create service | `POST` | `/services` |
| Retrieve service | `GET` | `/services/{serviceId}` |
| Update service | `PATCH` | `/services/{serviceId}` |
| Delete service | `DELETE` | `/services/{serviceId}` |
| Suspend service | `POST` | `/services/{serviceId}/suspend` |
| Resume service | `POST` | `/services/{serviceId}/resume` |
| Restart service | `POST` | `/services/{serviceId}/restart` |
| List env vars | `GET` | `/services/{serviceId}/env-vars` |
| Update env vars (bulk) | `PUT` | `/services/{serviceId}/env-vars` |
| Set env var | `PUT` | `/services/{serviceId}/env-vars/{envVarKey}` |
| Delete env var | `DELETE` | `/services/{serviceId}/env-vars/{envVarKey}` |
| List instances | `GET` | `/services/{serviceId}/instances` |
| List logs | `GET` | `/logs` |
| Subscribe logs (SSE) | `GET` | `/logs/subscribe` |
| List log label values | `GET` | `/logs/label-values` |