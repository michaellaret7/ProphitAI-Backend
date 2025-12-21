import logging
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from app.api.routes.agent_router import router as agent_router
from app.api.routes.alts_router import router as prophit_alts_router
from app.api.routes.broker_router import router as broker_router
from app.api.routes.cache_router import router as cache_router
from app.api.routes.crypto_router import router as crypto_router
from app.api.routes.etf_router import router as etf_router
from app.api.routes.fundamentals_router import router as fundamentals_router
from app.api.routes.macro_router import router as macro_router
from app.api.routes.news_router import router as news_router
from app.api.routes.portfolio_router import router as portfolio_router
from app.api.routes.price_router import router as price_router
from app.api.routes.screener_router import router as screener_router
from app.api.routes.search_router import router as search_router
from app.api.routes.technical_router import router as technical_router
from app.api.routes.ticker_router import router as ticker_router
from app.api.routes.user_routes import router as user_router
from app.api.routes.watchlist_routes import router as watchlist_router
from app.api.routes.websocket_router import router as websocket_router
from app.api.auth.api_key import validate_api_key
from app.api.auth.clerk import clerk_auth
from app.redis.client import cache
from app.api.routes.webhook_router import router as webhook_router

# Load environment variables from .env file
load_dotenv()

# Configure logging to show cache hit/miss INFO messages
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle: startup and shutdown events"""
    # Startup
    logger.info("🚀 Starting ProphitAI API...")
    await cache.connect()

    # Start background task for cache stats logging every 2 minutes
    stats_task = asyncio.create_task(cache.start_stats_logger(interval_seconds=120))

    yield

    # Shutdown
    logger.info("🛑 Shutting down ProphitAI API...")
    stats_task.cancel()
    await cache.close()

app = FastAPI(
    title="ProphitAI API",
    version="1.0.0",
    description="API for ProphitAI services",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
    swagger_ui_parameters={"persistAuthorization": True}
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5500",  # For local HTML file testing
        "http://localhost:5500",
        "https://inspiring-melomakarona-dd431a.netlify.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  # Allows all headers including X-API-Key
)

# Enable gzip compression for responses > 1KB
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Authentication dependencies
auth_dependencies = [Depends(validate_api_key), Depends(clerk_auth)]
api_key_only = [Depends(validate_api_key)]

# User-specific routes require API key + JWT token
app.include_router(user_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(portfolio_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(broker_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(watchlist_router, prefix="/api", dependencies=api_key_only)

# General data routes require API key only (no JWT needed)
app.include_router(prophit_alts_router, prefix="/api", dependencies=api_key_only)
app.include_router(price_router, prefix="/api", dependencies=api_key_only)
app.include_router(cache_router, prefix="/api", dependencies=api_key_only)
app.include_router(ticker_router, prefix="/api", dependencies=api_key_only)
app.include_router(technical_router, prefix="/api", dependencies=api_key_only)
app.include_router(macro_router, prefix="/api", dependencies=api_key_only)
app.include_router(news_router, prefix="/api", dependencies=api_key_only)
app.include_router(fundamentals_router, prefix="/api", dependencies=api_key_only)
app.include_router(etf_router, prefix="/api", dependencies=api_key_only)
app.include_router(search_router, prefix="/api", dependencies=api_key_only)
app.include_router(crypto_router, prefix="/api", dependencies=api_key_only)
app.include_router(screener_router, prefix="/api", dependencies=api_key_only)
app.include_router(agent_router, prefix="/api", dependencies=api_key_only)
# Webhook router - no auth (Clerk calls directly with signature verification)
app.include_router(webhook_router, prefix="/api")

# WebSocket router - no API key auth (WebSocket handles auth differently)
app.include_router(websocket_router)

@app.get("/")
def read_root():
    return {"message": "ProphitAI API is running!"}

# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint with Redis status

    Returns application and cache health status
    """
    redis_stats = await cache.get_stats()

    return {
        "status": "healthy",
        "api": {
            "version": "1.0.0",
            "title": "ProphitAI API"
        },
        "cache": redis_stats
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
