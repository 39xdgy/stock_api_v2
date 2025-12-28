"""
Stock API V2 - Main Application

A lightweight FastAPI application for stock trading signals.
Features:
- MACD and KDJ technical indicators
- New MACD peak detection sell logic
- Flexible filtering and sorting for market scans
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.project_name,
    description="Lightweight stock trading signals API with MACD peak detection",
    version="2.0.0",
    openapi_url=f"{settings.api_v1_str}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix=settings.api_v1_str)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Stock API V2",
        "version": "2.0.0",
        "features": [
            "MACD and KDJ indicators only (lightweight)",
            "MACD peak detection sell logic (instead of death cross)",
            "Flexible exclude rules for filtering",
            "Multi-level sorting support"
        ],
        "endpoints": {
            "market_scanner": f"{settings.api_v1_str}/market_scanner/scan",
            "trading_signals": f"{settings.api_v1_str}/trading_signals/current",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,  # Different port from V1
        reload=True,
        log_level="info"
    )

