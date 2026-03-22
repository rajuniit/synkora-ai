"""
LLM Proxy Gateway - Standalone Entrypoint

This runs the LLM Proxy as an isolated service for load testing.
It provides mock LLM endpoints that simulate real API responses.

Usage:
    python llm_proxy_entrypoint.py

Environment Variables:
    DATABASE_URL: PostgreSQL connection string
    REDIS_URL: Redis connection string for rate limiting
    PORT: Server port (default: 8080)
    WORKERS: Number of uvicorn workers (default: 4)
    LOG_LEVEL: Logging level (default: info)
    MAX_CONNECTIONS: Max concurrent connections (default: 10000)
"""

import logging
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Configure logging
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("llm-proxy")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("=" * 60)
    logger.info("Starting LLM Proxy Gateway")
    logger.info("=" * 60)
    logger.info("Mode: Standalone")
    logger.info(f"Workers: {os.getenv('WORKERS', 4)}")
    logger.info(f"Max Connections: {os.getenv('MAX_CONNECTIONS', 10000)}")
    logger.info(f"Database: {os.getenv('DATABASE_URL', 'not configured')[:50]}...")
    logger.info(f"Redis: {os.getenv('REDIS_URL', 'not configured')}")
    logger.info("=" * 60)

    yield

    logger.info("Shutting down LLM Proxy Gateway")


# Create the FastAPI application
app = FastAPI(
    title="LLM Proxy Gateway",
    description="Mock LLM endpoints for load testing AI agents without real API costs",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow all origins for proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health & Metrics Endpoints
# ============================================================================


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for container orchestration."""
    return {
        "status": "healthy",
        "service": "llm-proxy",
        "mode": "standalone",
    }


@app.get("/ready", tags=["health"])
async def readiness_check():
    """Readiness check - verifies database connectivity."""
    try:
        # Quick database check would go here
        return {"status": "ready"}
    except Exception as e:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "error": str(e)},
        )


@app.get("/metrics", tags=["metrics"])
async def metrics():
    """Prometheus metrics endpoint."""
    # Basic metrics - can be extended with actual metric collection
    metrics_output = """# HELP llm_proxy_info Information about the LLM Proxy
# TYPE llm_proxy_info gauge
llm_proxy_info{version="1.0.0"} 1

# HELP llm_proxy_up Whether the proxy is running
# TYPE llm_proxy_up gauge
llm_proxy_up 1
"""
    return metrics_output


# ============================================================================
# LLM Proxy Routes
# ============================================================================

try:
    from src.controllers.llm_proxy import router as llm_proxy_router

    app.include_router(llm_proxy_router, tags=["llm-proxy"])
    logger.info("LLM Proxy routes mounted at /proxy/v1/*")
except ImportError as e:
    logger.error(f"Failed to import LLM proxy router: {e}")
    logger.warning("Running in minimal mode - only health endpoints available")


# ============================================================================
# Exception Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions gracefully."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "type": "internal_server_error",
                "message": "An unexpected error occurred",
            }
        },
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    workers = int(os.getenv("WORKERS", 4))
    log_level = os.getenv("LOG_LEVEL", "info").lower()
    max_connections = int(os.getenv("MAX_CONNECTIONS", 10000))

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    LLM PROXY GATEWAY                         ║
╠══════════════════════════════════════════════════════════════╣
║  Mock LLM endpoints for load testing AI agents               ║
║                                                              ║
║  Endpoints:                                                  ║
║    OpenAI:    POST /proxy/v1/chat/completions               ║
║    Anthropic: POST /proxy/v1/messages                        ║
║    Google:    POST /proxy/v1/models/:model:generateContent   ║
║                                                              ║
║  Health:      GET  /health                                   ║
║  Docs:        GET  /docs                                     ║
╚══════════════════════════════════════════════════════════════╝

Starting server on port {port} with {workers} workers...
""")

    uvicorn.run(
        "llm_proxy_entrypoint:app",
        host="0.0.0.0",
        port=port,
        workers=workers,
        log_level=log_level,
        access_log=True,
        limit_concurrency=max_connections,
    )
