"""Agent tools for managing Render services and instances."""

from typing import List, Optional

from prophitai_atlas.tools.decorator import agent_tool
from prophitai_atlas.tools.responses import error_response, success_response
from prophitai_data.clients.render import get_render_client
from prophitai_data.clients.render.models import RenderInstance, RenderService


@agent_tool(name="create_render_service", category="render")
def create_render_service(
    name: str,
    service_type: str,
    runtime: str = "docker",
    repo: Optional[str] = None,
    branch: Optional[str] = None,
    auto_deploy: str = "yes",
    root_dir: Optional[str] = None,
    build_command: Optional[str] = None,
    start_command: Optional[str] = None,
    dockerfile_path: str = "./Dockerfile",
    docker_context: str = ".",
    publish_path: Optional[str] = None,
    plan: str = "starter",
    region: str = "oregon",
    num_instances: int = 1,
    health_check_path: Optional[str] = None,
    cron_schedule: Optional[str] = None,
    env_var_keys: Optional[List[str]] = None,
    env_var_values: Optional[List[str]] = None,
) -> str:
    """
    Create a new Render service from scratch. Supports Docker and native runtimes
    (Node, Python, Go, Rust, Ruby, Elixir).

    Args:
        name: Unique service name within the workspace.
        service_type: Service type — web_service, private_service, background_worker, static_site, or cron_job.
        runtime: Runtime environment. Use "docker" for Dockerfile-based builds, or a native runtime: "node", "python", "go", "rust", "ruby", "elixir". Default "docker".
        repo: GitHub repository URL (e.g. https://github.com/myorg/myrepo).
        branch: Git branch to deploy. Defaults to the repo's default branch.
        auto_deploy: Enable autodeploy on new commits — "yes" or "no".
        root_dir: Root directory of the service within the repo (e.g. "./backend").
        build_command: Build command for native runtimes (e.g. "npm install") or static sites (e.g. "npm run build").
        start_command: Start command for native runtimes (e.g. "node index.js", "python main.py").
        dockerfile_path: Path to Dockerfile (only for docker runtime, default "./Dockerfile").
        docker_context: Docker build context (only for docker runtime, default ".").
        publish_path: Publish directory for static sites (e.g. "./build").
        plan: Render plan — starter, standard, pro, etc. (default "starter").
        region: Deployment region — oregon, ohio, virginia, frankfurt, singapore (default "oregon").
        num_instances: Number of instances to run (default 1, not applicable to static sites or cron jobs).
        health_check_path: HTTP health check path (e.g. "/health"). Only for web services.
        cron_schedule: Cron schedule expression (e.g. "0 * * * *"). Required for cron_job type.
        env_var_keys: List of environment variable names to set on the service.
        env_var_values: List of environment variable values (must match env_var_keys order and length).
    """
    try:
        client = get_render_client()

        if not client.owner_id:
            return error_response(
                "RENDER_OWNER_ID is not configured. Set it in the environment to create services."
            )

        valid_types = {"web_service", "private_service", "background_worker", "static_site", "cron_job"}
        if service_type not in valid_types:
            return error_response(f"Invalid service_type '{service_type}'. Must be one of: {', '.join(valid_types)}")

        valid_runtimes = {"docker", "node", "python", "go", "rust", "ruby", "elixir"}
        if runtime not in valid_runtimes:
            return error_response(f"Invalid runtime '{runtime}'. Must be one of: {', '.join(valid_runtimes)}")

        if service_type == "cron_job" and not cron_schedule:
            return error_response("cron_schedule is required for cron_job service type.")

        # Reason: env vars must be paired — validate lengths match
        env_vars = None
        if env_var_keys and env_var_values:
            if len(env_var_keys) != len(env_var_values):
                return error_response(
                    f"env_var_keys ({len(env_var_keys)}) and env_var_values ({len(env_var_values)}) must have the same length."
                )
            env_vars = [{"key": k, "value": v} for k, v in zip(env_var_keys, env_var_values)]

        config = {
            "type": service_type,
            "name": name,
            "ownerId": client.owner_id,
            "autoDeploy": auto_deploy,
        }

        if repo:
            config["repo"] = repo
        if branch:
            config["branch"] = branch
        if root_dir:
            config["rootDir"] = root_dir
        if env_vars:
            config["envVars"] = env_vars

        # Reason: service_details structure varies by type and runtime
        if service_type == "static_site":
            details = {"pullRequestPreviewsEnabled": "no"}
            if build_command:
                details["buildCommand"] = build_command
            if publish_path:
                details["publishPath"] = publish_path
            config["serviceDetails"] = details

        elif runtime == "docker":
            details = {
                "env": "docker",
                "envSpecificDetails": {
                    "dockerCommand": start_command or "",
                    "dockerContext": docker_context,
                    "dockerfilePath": dockerfile_path,
                },
                "plan": plan,
                "region": region,
            }
            if service_type == "cron_job":
                details["schedule"] = cron_schedule
            else:
                details["numInstances"] = num_instances
                details["pullRequestPreviewsEnabled"] = "no"
                if health_check_path:
                    details["healthCheckPath"] = health_check_path
            config["serviceDetails"] = details

        else:
            # Reason: native runtimes use buildCommand + startCommand instead of Docker config
            details = {
                "env": runtime,
                "envSpecificDetails": {
                    "buildCommand": build_command or "",
                    "startCommand": start_command or "",
                },
                "plan": plan,
                "region": region,
            }
            if service_type == "cron_job":
                details["schedule"] = cron_schedule
            else:
                details["numInstances"] = num_instances
                details["pullRequestPreviewsEnabled"] = "no"
                if health_check_path:
                    details["healthCheckPath"] = health_check_path
            config["serviceDetails"] = details

        result = client.create_service(config)
        if result is None:
            return error_response(f"Failed to create service '{name}'")

        service = RenderService.from_raw(result)
        return success_response(service.model_dump())

    except Exception as e:
        return error_response(f"Failed to create service: {str(e)}")


@agent_tool(name="list_render_services", category="render")
def list_render_services(
    name: Optional[str] = None,
    service_type: Optional[str] = None,
    limit: int = 20,
) -> str:
    """
    List Render services, optionally filtered by name or type.

    Args:
        name: Filter by service name.
        service_type: Filter by service type (web_service, private_service, background_worker, static_site, cron_job).
        limit: Max number of services to return (1-100, default 20).
    """
    try:
        client = get_render_client()
        result = client.list_services(name=name, service_type=service_type, limit=limit)
        if result is None:
            return error_response("Failed to list Render services")
        services = [RenderService.from_raw(s).model_dump() for s in result]
        return success_response(services)
    except Exception as e:
        return error_response(f"Failed to list services: {str(e)}")


@agent_tool(name="get_render_service", category="render")
def get_render_service(
    service_id: str,
) -> str:
    """
    Get detailed information for a specific Render service.

    Args:
        service_id: The Render service ID (e.g. srv-xxxxxxxxxxxxx).
    """
    try:
        client = get_render_client()
        result = client.get_service(service_id)
        if result is None:
            return error_response(f"Failed to get service {service_id}")
        service = RenderService.from_raw(result)
        return success_response(service.model_dump())
    except Exception as e:
        return error_response(f"Failed to get service: {str(e)}")


@agent_tool(name="list_instances", category="render")
def list_instances(
    service_id: str,
) -> str:
    """
    List running instances for a Render service.

    Args:
        service_id: The Render service ID.
    """
    try:
        client = get_render_client()
        result = client.list_instances(service_id)
        if result is None:
            return error_response(f"Failed to list instances for service {service_id}")
        instances = [RenderInstance.from_raw(i).model_dump() for i in result]
        return success_response(instances)
    except Exception as e:
        return error_response(f"Failed to list instances: {str(e)}")


@agent_tool(name="restart_service", category="render")
def restart_service(
    service_id: str,
) -> str:
    """
    Restart all instances of a Render service without triggering a new build/deploy.

    Args:
        service_id: The Render service ID.
    """
    try:
        client = get_render_client()
        result = client.restart_service(service_id)
        if result is None:
            return success_response(f"Service {service_id} restart initiated")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to restart service: {str(e)}")


@agent_tool(name="suspend_service", category="render")
def suspend_service(
    service_id: str,
) -> str:
    """
    Suspend a Render service. The service will stop serving traffic and billing will stop.

    Args:
        service_id: The Render service ID.
    """
    try:
        client = get_render_client()
        result = client.suspend_service(service_id)
        if result is None:
            return success_response(f"Service {service_id} suspended")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to suspend service: {str(e)}")


@agent_tool(name="resume_service", category="render")
def resume_service(
    service_id: str,
) -> str:
    """
    Resume a previously suspended Render service. This triggers a new deploy.

    Args:
        service_id: The Render service ID.
    """
    try:
        client = get_render_client()
        result = client.resume_service(service_id)
        if result is None:
            return success_response(f"Service {service_id} resume initiated")
        return success_response(result)
    except Exception as e:
        return error_response(f"Failed to resume service: {str(e)}")
