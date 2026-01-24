# API routes
from fastapi import APIRouter
from .chat import router as chat_router
from .edgar import router as edgar_router

api_router = APIRouter()
api_router.include_router(chat_router)
api_router.include_router(edgar_router)

__all__ = ["api_router"]
