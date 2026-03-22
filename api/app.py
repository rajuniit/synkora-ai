"""
Main application entry point.

This file is used by Uvicorn to run the FastAPI application.
"""

from src.app import create_app

# Create FastAPI application
app = create_app()

if __name__ == "__main__":
    # Run development server
    import uvicorn

    from src.config import settings

    uvicorn.run(
        "app:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_debug,
        log_level="debug" if settings.app_debug else "info",
    )
