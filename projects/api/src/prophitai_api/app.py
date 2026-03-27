"""
ProphitAI FastAPI application factory.

Configures middleware, mounts all routers, and manages the application lifecycle
(Redis cache connection, PDF service startup/shutdown).
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware


from prophitai_api.routes.agent import router as agent_router
from prophitai_api.routes.broker import router as broker_router
from prophitai_api.routes.cache import router as cache_router
from prophitai_api.routes.chat import router as chat_router
from prophitai_api.routes.crypto import router as crypto_router
from prophitai_api.routes.dashboard import router as dashboard_router
from prophitai_api.routes.document import router as document_router
from prophitai_api.routes.etf import router as etf_router
from prophitai_api.routes.fundamentals import router as fundamentals_router
from prophitai_api.routes.macro import router as macro_router
from prophitai_api.routes.messaging import router as messaging_router
from prophitai_api.routes.news import router as news_router
from prophitai_api.routes.portfolio import router as portfolio_router
from prophitai_api.routes.price import router as price_router
from prophitai_api.routes.screener import router as screener_router
from prophitai_api.routes.search import router as search_router
from prophitai_api.routes.technical import router as technical_router
from prophitai_api.routes.ticker import router as ticker_router
from prophitai_api.routes.trade_proposal import router as trade_proposal_router
from prophitai_api.routes.user import router as user_router
from prophitai_api.routes.watchlist import router as watchlist_router
from prophitai_api.routes.webhook import router as webhook_router
from prophitai_api.routes.websocket import router as websocket_router

from prophitai_api.auth.api_key import validate_api_key
from prophitai_api.auth.clerk import clerk_auth
from prophitai_api.cache.redis_client import cache
from prophitai_api.services.pdf.pdf_service import pdf_service

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:     %(name)s - %(message)s'
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Manage application lifecycle: startup and shutdown events."""
    logger.info("Starting ProphitAI API...")
    await cache.connect()
    try:
        await pdf_service.startup()
    except Exception as e:
        logger.warning("PDF service failed to start — PDF generation disabled: %s", e)

    # Background task: log cache stats every 2 minutes
    stats_task = asyncio.create_task(cache.start_stats_logger(interval_seconds=120))

    yield

    logger.info("Shutting down ProphitAI API...")
    stats_task.cancel()
    await pdf_service.shutdown()
    await cache.close()


app = FastAPI(
    title="ProphitAI API",
    version="1.0.0",
    description="API for ProphitAI services",
    lifespan=lifespan,
    swagger_ui_parameters={"persistAuthorization": True}
)

# ================================
# --> Middleware
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "https://inspiring-melomakarona-dd431a.netlify.app",
        "https://dev--inspiring-melomakarona-dd431a.netlify.app",
        "https://prophitai.com",
        "https://www.prophitai.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# ================================
# --> Authentication dependency groups
# ================================
auth_dependencies = [Depends(validate_api_key), Depends(clerk_auth)]
api_key_only = [Depends(validate_api_key)]

# ================================
# --> User-specific routes (API key + Clerk JWT)
# ================================
app.include_router(user_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(portfolio_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(broker_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(trade_proposal_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(watchlist_router, prefix="/api", dependencies=auth_dependencies)
app.include_router(dashboard_router, prefix="/api", dependencies=auth_dependencies)

# ================================
# --> API key only routes
# ================================
app.include_router(document_router, prefix="/api", dependencies=api_key_only)
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

# ================================
# --> No auth routes
# ================================
# Webhook router — Clerk calls directly with signature verification
app.include_router(webhook_router, prefix="/api")
# WebSocket router — auth handled at connection level
app.include_router(websocket_router)
# Messaging router — WebSocket + REST (auth handled internally)
app.include_router(messaging_router, prefix="/api")
# Chat router — WebSocket + REST for interactive agent chat
app.include_router(chat_router, prefix="/api")


@app.get("/")
def read_root():
    return {"message": "ProphitAI API is running!"}


@app.get("/health")
async def health_check():
    """Health check endpoint with Redis status."""
    redis_stats = await cache.get_stats()
    return {
        "status": "healthy",
        "api": {
            "version": "1.0.0",
            "title": "ProphitAI API"
        },
        "cache": redis_stats
    }
