"""
Session Service

CRUD operations for chat sessions and messages.
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import ChatSession, ChatMessage


class SessionService:
    """Service for managing chat sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def generate_session_id() -> str:
        """Generate a unique session ID."""
        return f"session-{uuid.uuid4().hex[:12]}"

    @staticmethod
    def generate_title(first_message: str) -> str:
        """Generate a title from the first message."""
        # Clean up and truncate
        title = first_message.strip()
        title = title.replace("\n", " ")
        if len(title) > 50:
            title = title[:47] + "..."
        return title if title else "New Chat"

    async def create_session(self, session_id: Optional[str] = None, title: Optional[str] = None) -> ChatSession:
        """Create a new chat session."""
        session = ChatSession(
            id=session_id or self.generate_session_id(),
            title=title or "New Chat",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get a session by ID."""
        result = await self.db.execute(
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_session(self, session_id: str) -> ChatSession:
        """Get existing session or create new one."""
        session = await self.get_session(session_id)
        if not session:
            session = await self.create_session(session_id=session_id)
        return session

    async def list_sessions(self, limit: int = 50, offset: int = 0) -> tuple[list[ChatSession], int]:
        """List all sessions with pagination."""
        # Get total count
        count_result = await self.db.execute(select(func.count(ChatSession.id)))
        total = count_result.scalar() or 0

        # Get sessions ordered by updated_at desc
        result = await self.db.execute(
            select(ChatSession)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .offset(offset)
        )
        sessions = list(result.scalars().all())

        return sessions, total

    async def delete_session(self, session_id: str) -> bool:
        """Delete a session and all its messages."""
        result = await self.db.execute(
            delete(ChatSession).where(ChatSession.id == session_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def update_session_title(self, session_id: str, title: str) -> Optional[ChatSession]:
        """Update session title."""
        session = await self.get_session(session_id)
        if session:
            session.title = title
            session.updated_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(session)
        return session

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        question_type: Optional[str] = None,
    ) -> ChatMessage:
        """Add a message to a session."""
        # Ensure session exists
        session = await self.get_or_create_session(session_id)

        # If this is the first user message, update title
        if role == "user":
            existing_messages = await self.get_messages(session_id)
            user_messages = [m for m in existing_messages if m.role == "user"]
            if len(user_messages) == 0:
                session.title = self.generate_title(content)

        # Update session timestamp
        session.updated_at = datetime.utcnow()

        # Create message
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            question_type=question_type,
            created_at=datetime.utcnow(),
        )
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        return message

    async def get_messages(self, session_id: str) -> list[ChatMessage]:
        """Get all messages for a session."""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
        )
        return list(result.scalars().all())

    async def get_message_count(self, session_id: str) -> int:
        """Get count of messages in a session."""
        result = await self.db.execute(
            select(func.count(ChatMessage.id))
            .where(ChatMessage.session_id == session_id)
        )
        return result.scalar() or 0
