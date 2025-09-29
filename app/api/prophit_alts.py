from fastapi import APIRouter
from app.api.routes.alts_router import router as prophit_alts_routes

router = APIRouter()

router.include_router(prophit_alts_routes, tags=["alts"])
