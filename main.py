import logging
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routes.alts_router import router as prophit_alts_router
from app.api.routes.user_routes import router as user_router
from app.api.routes.portfolio_router import router as portfolio_router
from app.api.routes.websocket_router import router as ws_router
from app.api.routes.price_router import router as price_router
from app.api.routes.cache_router import router as cache_router
from app.api.routes.agent_runs_router import router as agent_runs_router
from app.redis.client import cache
from app.api.routes.broker_router import router as broker_router
from app.api.routes.ticker_router import router as ticker_router
from app.api.routes.technical_router import router as technical_router
from app.api.routes.macro_router import router as macro_router
from app.api.routes.news_router import router as news_router

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
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5500",  # For local HTML file testing
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prophit_alts_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(ws_router, prefix="/api")
app.include_router(price_router, prefix="/api")
app.include_router(cache_router, prefix="/api")
app.include_router(agent_runs_router, prefix="/api")
app.include_router(broker_router, prefix="/api")
app.include_router(ticker_router, prefix="/api")
app.include_router(technical_router, prefix="/api")
app.include_router(macro_router, prefix="/api")
app.include_router(news_router, prefix="/api")

# Serve test frontend (WebSocket stream viewer)
app.mount("/static", StaticFiles(directory="app/api/testing/static"), name="static")

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
