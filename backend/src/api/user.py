from fastapi import APIRouter
from backend.src.api.routes.user_routes import router as user_routes

router = APIRouter()

router.include_router(user_routes, tags=["users"])
