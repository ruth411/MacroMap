# API routes
from fastapi import APIRouter
from .auth import router as auth_router
from .chat import router as chat_router
from .edgar import router as edgar_router
from .retrieval import router as retrieval_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(edgar_router)
api_router.include_router(retrieval_router)

__all__ = ["api_router"]
