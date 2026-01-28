from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from app.core.config import settings
from app.core.database import init_db
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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "0.1.0",
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


@app.get("/debug/env")
async def debug_env():
    """Debug endpoint to check environment variables."""
    import os
    env_key = os.environ.get("OPENAI_API_KEY", "")
    all_env_keys = [k for k in os.environ.keys() if "OPENAI" in k.upper() or "API" in k.upper()]
    return {
        "settings_openai_key_set": bool(settings.openai_api_key),
        "settings_openai_key_length": len(settings.openai_api_key) if settings.openai_api_key else 0,
        "env_openai_key_set": bool(env_key),
        "env_openai_key_length": len(env_key) if env_key else 0,
        "env_openai_key_prefix": env_key[:15] + "..." if env_key else "NOT SET",
        "related_env_vars": all_env_keys,
        "llm_provider": settings.llm_provider,
    }
