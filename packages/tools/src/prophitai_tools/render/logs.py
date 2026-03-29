"""Agent tools for querying Render service logs."""

from typing import Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_data.clients.render import get_render_client
from prophitai_data.clients.render.models import RenderLogEntry


@agent_tool(name="get_render_logs", category="render")
def get_render_logs(
    resource_id: str,
    limit: int = 100,
    level: Optional[str] = None,
    text: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    instance_id: Optional[str] = None,
    host: Optional[str] = None,
) -> str:
    """
    Query logs for a Render resource (service, database, or Redis).

    Args:
        resource_id: The resource ID to query logs for (e.g. srv-xxxxxxxxxxxxx).
        limit: Max number of log entries to return (default 100).
        level: Comma-separated log levels to filter by (e.g. "error,warn").
        text: Text to search for in log messages.
        start_time: Start of time range in ISO 8601 format.
        end_time: End of time range in ISO 8601 format.
        instance_id: Filter by specific instance ID.
        host: Filter by host name.
    """
    try:
        client = get_render_client()
        if not client.owner_id:
            return error_response(
                "RENDER_OWNER_ID is not configured. Set it in the environment to query logs."
            )

        level_list = [l.strip() for l in level.split(",")] if level else None
        text_list = [text] if text else None

        result = client.list_logs(
            resource_id=resource_id,
            limit=limit,
            level=level_list,
            text=text_list,
            start_time=start_time,
            end_time=end_time,
            instance_id=instance_id,
            host=host,
        )
        if result is None:
            return error_response(f"Failed to fetch logs for resource {resource_id}")

        logs = [RenderLogEntry.from_raw(entry).model_dump() for entry in result]
        return success_response(logs)
    except Exception as e:
        return error_response(f"Failed to fetch logs: {str(e)}")


@agent_tool(name="get_render_log_labels", category="render")
def get_render_log_labels(
    resource_id: str,
    label: str,
) -> str:
    """
    Get available values for a log label on a Render resource.
    Useful for discovering filter values before querying logs.

    Args:
        resource_id: The resource ID (e.g. srv-xxxxxxxxxxxxx).
        label: The label name to get values for (e.g. level, instance, host, type, statusCode, method, path).
    """
    try:
        client = get_render_client()
        if not client.owner_id:
            return error_response(
                "RENDER_OWNER_ID is not configured. Set it in the environment to query log labels."
            )

        result = client.get_log_label_values(resource_id, label)
        if result is None:
            return error_response(
                f"Failed to get label values for '{label}' on resource {resource_id}"
            )
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to get log labels: {str(e)}")
