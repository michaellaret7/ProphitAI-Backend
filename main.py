from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.prophit_alts import router as prophit_alts_router
from app.api.user import router as user_router

# Create FastAPI app
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

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
