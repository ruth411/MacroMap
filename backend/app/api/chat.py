"""
Chat API Router

Endpoints for chat interactions with the financial assistant.
"""

import logging
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
from app.services.retrieval.service import get_retrieval_service
from app.services.retrieval.models import RetrievalQuery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Send a message to the financial assistant.

    The assistant will analyze your question and provide an educational,
    accurate response about financial concepts. When RAG is enabled,
    responses are grounded in SEC filings with citations.
    """
    try:
        llm_service = get_llm_service()

        # Detect question type for response metadata
        question_type = FinancialPrompts.detect_question_type(request.message)

        # RAG retrieval
        context = None
        citations = []
        sources_used = 0

        if request.use_rag:
            try:
                retrieval_service = get_retrieval_service()

                # Check if we have any documents indexed
                if retrieval_service.vector_store.count() > 0:
                    retrieval_query = RetrievalQuery(
                        query=request.message,
                        top_k=5,
                        ticker=request.ticker_filter,
                        filing_type=request.filing_type_filter,
                    )

                    retrieval_result = await retrieval_service.retrieve(retrieval_query)

                    if retrieval_result.has_results:
                        context = retrieval_result.formatted_context
                        citations = [c.format_full() for c in retrieval_result.citations]
                        sources_used = len(retrieval_result.chunks)
                        logger.info(f"Retrieved {sources_used} sources for query")
            except Exception as e:
                # Log but don't fail - continue without RAG
                logger.warning(f"RAG retrieval failed, continuing without context: {e}")

        # Generate response with context
        if request.use_templates:
            response = await llm_service.chat(
                message=request.message,
                session_id=request.session_id,
                context=context,
            )
        else:
            response = await llm_service.simple_chat(
                message=request.message,
                session_id=request.session_id,
            )

        # Append citations section if we have sources
        if citations and sources_used > 0:
            retrieval_service = get_retrieval_service()
            response += retrieval_service.format_citations_section(
                retrieval_result.citations
            )

        return ChatResponse(
            response=response,
            session_id=request.session_id,
            question_type=question_type,
            timestamp=datetime.utcnow(),
            sources_used=sources_used,
            citations=citations,
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
