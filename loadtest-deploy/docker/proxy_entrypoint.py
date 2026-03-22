"""
LLM Proxy Gateway - Standalone Entrypoint

This runs the LLM Proxy as an isolated service, separate from the main Synkora platform.
Used for high-scale load testing where resource isolation is critical.
"""

import os
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("llm-proxy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting LLM Proxy Gateway (Standalone Mode)")
    logger.info(f"Workers: {os.getenv('WORKERS', 4)}")
    logger.info(f"Max connections: {os.getenv('MAX_CONNECTIONS', 10000)}")
    yield
    logger.info("Shutting down LLM Proxy Gateway")


# Create standalone FastAPI app
app = FastAPI(
    title="LLM Proxy Gateway",
    description="Mock LLM endpoints for load testing AI agents",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow all origins for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check for Kubernetes probes."""
    return {"status": "healthy", "mode": "standalone"}


# Metrics endpoint (Prometheus format)
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return """
# HELP llm_proxy_requests_total Total number of requests
# TYPE llm_proxy_requests_total counter
llm_proxy_requests_total 0

# HELP llm_proxy_request_duration_seconds Request duration histogram
# TYPE llm_proxy_request_duration_seconds histogram
llm_proxy_request_duration_seconds_bucket{le="0.1"} 0
llm_proxy_request_duration_seconds_bucket{le="0.5"} 0
llm_proxy_request_duration_seconds_bucket{le="1.0"} 0
llm_proxy_request_duration_seconds_bucket{le="+Inf"} 0
"""


# Import and mount the LLM proxy router
try:
    from src.controllers.llm_proxy import router as llm_proxy_router
    app.include_router(llm_proxy_router, tags=["llm-proxy"])
    logger.info("LLM Proxy routes mounted successfully")
except ImportError as e:
    logger.warning(f"Could not import LLM proxy router: {e}")
    logger.info("Running in minimal mode - only health endpoint available")


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_server_error", "message": "An unexpected error occurred"},
    )


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    workers = int(os.getenv("WORKERS", 4))

    uvicorn.run(
        "proxy_entrypoint:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        access_log=True,
        limit_concurrency=int(os.getenv("MAX_CONNECTIONS", 10000)),
    )
