"""
Chat API Router

Endpoints for chat interactions with the financial assistant.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rate_limit import limiter
from app.core.config import settings
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    ConversationClearRequest,
    HealthResponse,
    SessionSummary,
    SessionListResponse,
    SessionDetailResponse,
    MessageResponse,
    CreateSessionRequest,
    CreateSessionResponse,
)
from app.models.user import User
from app.services.llm import LLMService, FinancialPrompts
from app.services.llm.service import get_llm_service
from app.services.retrieval.service import get_retrieval_service
from app.services.retrieval.models import RetrievalQuery
from app.core.database import get_db
from app.core.security import get_optional_user, get_current_user
from app.services.session_service import SessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
@limiter.limit(settings.rate_limit_chat)
async def chat(
    chat_request: ChatRequest,
    request: Request,  # Required for rate limiter (must be named 'request')
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> ChatResponse:
    """
    Send a message to the financial assistant.

    For authenticated users, messages are persisted.
    For guests, messages are not saved to database.
    """
    try:
        llm_service = get_llm_service()
        session_service = SessionService(db)

        user_id = current_user.id if current_user else None
        is_guest = user_id is None

        # Check if this is the first message (for title generation later)
        is_first_message = False
        if not is_guest:
            existing_messages = await session_service.get_messages(chat_request.session_id)
            is_first_message = len([m for m in existing_messages if m.role == "user"]) == 0

        # Detect question type for response metadata
        question_type = FinancialPrompts.detect_question_type(chat_request.message)

        # Persist user message (only for authenticated users)
        if not is_guest:
            await session_service.add_message(
                session_id=chat_request.session_id,
                role="user",
                content=chat_request.message,
                user_id=user_id,
            )

        # RAG retrieval
        context = None
        citations = []
        sources_used = 0

        if chat_request.use_rag:
            try:
                retrieval_service = get_retrieval_service()

                # Check if we have any documents indexed
                if retrieval_service.vector_store.count() > 0:
                    retrieval_query = RetrievalQuery(
                        query=chat_request.message,
                        top_k=5,
                        ticker=chat_request.ticker_filter,
                        filing_type=chat_request.filing_type_filter,
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
        if chat_request.use_templates:
            response = await llm_service.chat(
                message=chat_request.message,
                session_id=chat_request.session_id,
                context=context,
            )
        else:
            response = await llm_service.simple_chat(
                message=chat_request.message,
                session_id=chat_request.session_id,
            )

        # Append citations section if we have sources
        if citations and sources_used > 0:
            retrieval_service = get_retrieval_service()
            response += retrieval_service.format_citations_section(
                retrieval_result.citations
            )

        # Persist assistant response (only for authenticated users)
        if not is_guest:
            await session_service.add_message(
                session_id=chat_request.session_id,
                role="assistant",
                content=response,
                question_type=question_type,
                user_id=user_id,
            )

            # Generate summarized title for first message
            if is_first_message:
                try:
                    title_prompt = f"Generate a very short title (3-5 words max) summarizing this question. Only respond with the title, nothing else.\n\nQuestion: {chat_request.message}"
                    title = await llm_service.simple_chat(
                        message=title_prompt,
                        session_id=f"title-gen-{chat_request.session_id}",
                    )
                    # Clean up the title
                    title = title.strip().strip('"').strip("'")
                    if len(title) > 50:
                        title = title[:47] + "..."
                    if title:
                        await session_service.update_session_title(
                            chat_request.session_id, title, user_id=user_id
                        )
                    # Clean up the title generation session
                    llm_service.delete_conversation(f"title-gen-{chat_request.session_id}")
                except Exception as e:
                    logger.warning(f"Failed to generate title: {e}")

        return ChatResponse(
            response=response,
            session_id=chat_request.session_id,
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


# Session endpoints (require authentication)
@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionListResponse:
    """List all chat sessions for the authenticated user."""
    session_service = SessionService(db)
    sessions, total = await session_service.list_sessions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    session_summaries = []
    for s in sessions:
        msg_count = await session_service.get_message_count(s.id)
        session_summaries.append(
            SessionSummary(
                id=s.id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=msg_count,
            )
        )

    return SessionListResponse(sessions=session_summaries, total=total)


@router.post("/sessions", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CreateSessionResponse:
    """Create a new chat session for the authenticated user."""
    session_service = SessionService(db)
    title = request.title if request else None
    session = await session_service.create_session(
        title=title,
        user_id=current_user.id,
    )

    return CreateSessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
    )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SessionDetailResponse:
    """Get a session with all its messages (user must own the session)."""
    session_service = SessionService(db)
    session = await session_service.get_session(session_id, user_id=current_user.id)

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    messages = [
        MessageResponse(
            role=m.role,
            content=m.content,
            question_type=m.question_type,
            created_at=m.created_at,
        )
        for m in session.messages
    ]

    return SessionDetailResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        messages=messages,
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Delete a chat session (user must own the session)."""
    session_service = SessionService(db)

    # Also clear from LLM service memory
    try:
        llm_service = get_llm_service()
        llm_service.delete_conversation(session_id)
    except Exception:
        pass  # Ignore if not in memory

    deleted = await session_service.delete_session(session_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")

    return {"status": "success", "message": f"Session {session_id} deleted"}
