from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

import sentry_sdk

from app.core.config import settings
from app.core.database import init_db
from app.core.rate_limit import setup_rate_limiting
from app.api import api_router

# Initialize Sentry error tracking (only when DSN is configured)
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.effective_sentry_environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,  # Don't send personally identifiable info
        enable_tracing=True,
    )

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

# Rate limiting
setup_rate_limiting(app)

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
