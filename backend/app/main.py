from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import traceback

from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import setup_rate_limiting
from app.api import api_router

# Import models to ensure tables are created
from app.models.user import User  # noqa: F401
from app.models.session import ChatSession, ChatMessage  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure data directories exist
    settings.filings_dir.mkdir(parents=True, exist_ok=True)
    settings.parsed_dir.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Initialize database
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized successfully")

    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title=settings.app_name,
    description="A grounded Financial Analyst Copilot with RAG and verified computation",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting (added first = innermost middleware)
setup_rate_limiting(app)

# CORS middleware (added last = outermost, processes requests first)
# Must be outermost so CORS headers are always included,
# even on rate-limited or error responses
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_cors_headers(request: Request) -> dict:
    """Get CORS headers for the response based on request origin."""
    origin = request.headers.get("origin", "")
    if origin in settings.cors_origins:
        return {
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
        }
    return {}


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler that ensures CORS headers are always present.
    This catches exceptions that bypass the CORS middleware (e.g., from ServerErrorMiddleware).
    """
    logger.error(f"Unhandled exception: {exc}\n{traceback.format_exc()}")

    # Build response with CORS headers
    headers = get_cors_headers(request)

    return JSONResponse(
        status_code=500,
        content={
            "detail": f"Internal server error: {str(exc)}",
            "type": type(exc).__name__,
        },
        headers=headers,
    )


# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.2.0",  # RAG improvements: query expansion, hybrid search, better embeddings
        "llm_provider": settings.llm_provider,
    }


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "app": settings.app_name,
        "description": "Financial Analyst Copilot API",
        "docs": "/docs",
        "health": "/health",
        "chat": f"{settings.api_prefix}/chat",
    }
