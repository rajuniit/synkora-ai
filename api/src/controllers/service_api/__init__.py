"""
Service API router.

Handles backend service endpoints.
"""

from fastapi import APIRouter

# Create main service router
service_router = APIRouter()


@service_router.get("/")
async def index():
    """Service API index."""
    return {
        "message": "Service API",
        "version": "1.0.0",
        "status": "active",
    }


@service_router.get("/health")
async def health():
    """Service health check."""
    return {"status": "healthy"}
