"""Agent tools for managing Render service environment variables."""

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_data.clients.render import get_render_client
from prophitai_data.clients.render.models import RenderEnvVar


@agent_tool(name="list_env_vars", category="render")
def list_env_vars(
    service_id: str,
) -> str:
    """
    List all environment variables for a Render service.

    Args:
        service_id: The Render service ID (e.g. srv-xxxxxxxxxxxxx).
    """
    try:
        client = get_render_client()
        result = client.list_env_vars(service_id)
        if result is None:
            return error_response(f"Failed to list env vars for service {service_id}")
        env_vars = [RenderEnvVar.from_raw(ev).model_dump() for ev in result]
        return success_response(env_vars)
    except Exception as e:
        return error_response(f"Failed to list env vars: {str(e)}")


@agent_tool(name="set_env_var", category="render")
def set_env_var(
    service_id: str,
    key: str,
    value: str,
) -> str:
    """
    Set or update a single environment variable on a Render service. This may trigger a redeploy.

    Args:
        service_id: The Render service ID.
        key: The environment variable name.
        value: The environment variable value.
    """
    try:
        client = get_render_client()
        result = client.set_env_var(service_id, key, value)
        if result is None:
            return error_response(f"Failed to set env var {key} on service {service_id}")
        env_var = RenderEnvVar.from_raw(result)
        return success_response(env_var.model_dump())
    except Exception as e:
        return error_response(f"Failed to set env var: {str(e)}")


@agent_tool(name="delete_env_var", category="render")
def delete_env_var(
    service_id: str,
    key: str,
) -> str:
    """
    Delete an environment variable from a Render service. This may trigger a redeploy.

    Args:
        service_id: The Render service ID.
        key: The environment variable name to delete.
    """
    try:
        client = get_render_client()
        result = client.delete_env_var(service_id, key)
        if result is None:
            return success_response(f"Env var '{key}' deleted from service {service_id}")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to delete env var: {str(e)}")
