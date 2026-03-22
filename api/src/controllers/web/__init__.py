"""
Web API router.

Handles public-facing web endpoints.
"""

from fastapi import APIRouter

# Create main web router
web_router = APIRouter()


@web_router.get("/")
async def index():
    """Web API index."""
    return {
        "message": "Synkora Web API",
        "version": "1.0.0",
        "docs": "/api/v1/docs",
    }


@web_router.get("/health")
async def health():
    """Web API health check."""
    return {"status": "healthy"}
