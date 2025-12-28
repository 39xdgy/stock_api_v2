"""
API v1 Router

Combines all endpoint routers into a single API router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import market_scanner, trading_signals

api_router = APIRouter()

api_router.include_router(
    market_scanner.router,
    prefix="/market_scanner",
    tags=["market_scanner"]
)

api_router.include_router(
    trading_signals.router,
    prefix="/trading_signals",
    tags=["trading_signals"]
)

