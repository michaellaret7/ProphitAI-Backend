from fastapi import APIRouter
from app.api.routes.websocket_router import router as websocket_routes
from app.api.routes.agent_runs_router import router as agent_runs_routes

router = APIRouter()
router.include_router(websocket_routes, tags=["websocket"])
router.include_router(agent_runs_routes, tags=["agents"])