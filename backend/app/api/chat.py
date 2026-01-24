"""
Chat API Router

Endpoints for chat interactions with the financial assistant.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ConversationClearRequest,
    HealthResponse,
)
from app.services.llm import LLMService, FinancialPrompts
from app.services.llm.service import get_llm_service

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the financial assistant.

    The assistant will analyze your question and provide an educational,
    accurate response about financial concepts.
    """
    try:
        llm_service = get_llm_service()

        # Detect question type for response metadata
        question_type = FinancialPrompts.detect_question_type(request.message)

        # Generate response
        if request.use_templates:
            response = await llm_service.chat(
                message=request.message,
                session_id=request.session_id,
            )
        else:
            response = await llm_service.simple_chat(
                message=request.message,
                session_id=request.session_id,
            )

        return ChatResponse(
            response=response,
            session_id=request.session_id,
            question_type=question_type,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate response: {str(e)}"
        )


@router.post("/clear")
async def clear_conversation(request: ConversationClearRequest) -> dict:
    """Clear the conversation history for a session."""
    try:
        llm_service = get_llm_service()
        llm_service.clear_conversation(request.session_id)
        return {"status": "success", "message": f"Conversation {request.session_id} cleared"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear conversation: {str(e)}"
        )


@router.delete("/{session_id}")
async def delete_conversation(session_id: str) -> dict:
    """Delete a conversation entirely."""
    try:
        llm_service = get_llm_service()
        llm_service.delete_conversation(session_id)
        return {"status": "success", "message": f"Conversation {session_id} deleted"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@router.get("/health", response_model=HealthResponse)
async def chat_health() -> HealthResponse:
    """Check the health of the chat service and LLM provider."""
    try:
        llm_service = get_llm_service()
        health = await llm_service.health_check()
        return HealthResponse(**health)
    except Exception as e:
        return HealthResponse(
            service="llm",
            provider="unknown",
            model="unknown",
            healthy=False,
        )
