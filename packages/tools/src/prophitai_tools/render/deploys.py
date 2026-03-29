"""Agent tools for managing Render deploys."""

from typing import Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_data.clients.render import get_render_client
from prophitai_data.clients.render.models import RenderDeploy


@agent_tool(name="list_deploys", category="render")
def list_deploys(
    service_id: str,
    limit: int = 20,
) -> str:
    """
    List recent deploys for a Render service.

    Args:
        service_id: The Render service ID (e.g. srv-xxxxxxxxxxxxx).
        limit: Max number of deploys to return (1-100, default 20).
    """
    try:
        client = get_render_client()
        result = client.list_deploys(service_id, limit=limit)

        if result is None:
            return error_response(f"Failed to list deploys for service {service_id}")

        deploys = [RenderDeploy.from_raw(d).model_dump() for d in result]
        
        return success_response(deploys)
    
    except Exception as e:
        return error_response(f"Failed to list deploys: {str(e)}")


@agent_tool(name="get_deploy", category="render")
def get_deploy(
    service_id: str,
    deploy_id: str,
) -> str:
    """
    Get details for a specific Render deploy.

    Args:
        service_id: The Render service ID.
        deploy_id: The deploy ID (e.g. dep-xxxxxxxxxxxxx).
    """
    try:
        client = get_render_client()
        result = client.get_deploy(service_id, deploy_id)
        if result is None:
            return error_response(f"Failed to get deploy {deploy_id}")
        deploy = RenderDeploy.from_raw(result)
        return success_response(deploy.model_dump())
    except Exception as e:
        return error_response(f"Failed to get deploy: {str(e)}")


@agent_tool(name="trigger_deploy", category="render")
def trigger_deploy(
    service_id: str,
    clear_cache: bool = False,
    commit_id: Optional[str] = None,
    image_url: Optional[str] = None,
) -> str:
    """
    Trigger a new deploy for a Render service.

    Args:
        service_id: The Render service ID.
        clear_cache: Whether to clear the build cache before deploying.
        commit_id: SHA of a specific Git commit to deploy. Defaults to latest on connected branch.
        image_url: URL of the image to deploy (for image-backed services only).
    """
    try:
        client = get_render_client()
        result = client.trigger_deploy(
            service_id,
            clear_cache=clear_cache,
            commit_id=commit_id,
            image_url=image_url,
        )
        if result is None:
            return error_response(f"Failed to trigger deploy for service {service_id}")
        deploy = RenderDeploy.from_raw(result)
        return success_response(deploy.model_dump())
    except Exception as e:
        return error_response(f"Failed to trigger deploy: {str(e)}")


@agent_tool(name="cancel_deploy", category="render")
def cancel_deploy(
    service_id: str,
    deploy_id: str,
) -> str:
    """
    Cancel an in-progress Render deploy.

    Args:
        service_id: The Render service ID.
        deploy_id: The deploy ID to cancel.
    """
    try:
        client = get_render_client()
        result = client.cancel_deploy(service_id, deploy_id)
        if result is None:
            return error_response(f"Failed to cancel deploy {deploy_id}")
        deploy = RenderDeploy.from_raw(result)
        return success_response(deploy.model_dump())
    except Exception as e:
        return error_response(f"Failed to cancel deploy: {str(e)}")


@agent_tool(name="rollback_deploy", category="render")
def rollback_deploy(
    service_id: str,
    deploy_id: str,
) -> str:
    """
    Roll back a Render service to a previous deploy.

    Args:
        service_id: The Render service ID.
        deploy_id: The deploy ID to roll back to.
    """
    try:
        client = get_render_client()
        result = client.rollback_deploy(service_id, deploy_id)
        if result is None:
            return error_response(f"Failed to rollback to deploy {deploy_id}")
        deploy = RenderDeploy.from_raw(result)
        return success_response(deploy.model_dump())
    except Exception as e:
        return error_response(f"Failed to rollback deploy: {str(e)}")
