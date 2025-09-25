from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.prophit_alts import router as prophit_alts_router
from app.api.user import router as user_router
from app.api.portfolio import router as portfolio_router
from app.api.websocket import router as ws_router

app = FastAPI(
    title="ProphitAI API",
    version="1.0.0",
    description="API for ProphitAI services"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(prophit_alts_router, prefix="/api")
app.include_router(user_router, prefix="/api")
app.include_router(portfolio_router, prefix="/api")
app.include_router(ws_router, prefix="/api")

# Serve test frontend (WebSocket stream viewer)
app.mount("/static", StaticFiles(directory="app/api/testing/static"), name="static")

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
