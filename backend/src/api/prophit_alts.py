from fastapi import APIRouter
from backend.src.api.routes.prophit_alts_router import router as prophit_alts_routes

router = APIRouter()

router.include_router(prophit_alts_routes, tags=["prophit-alts"])
