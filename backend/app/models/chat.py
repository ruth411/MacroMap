"""
Chat API Models

Pydantic models for chat request/response validation.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ChatRequest(BaseModel):
    """Request model for chat endpoint."""
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")
    session_id: Optional[str] = Field(default="default", description="Conversation session ID")
    use_templates: bool = Field(default=True, description="Whether to apply prompt templates")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What is the P/E ratio and how do I interpret it?",
                "session_id": "user-123",
                "use_templates": True
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Conversation session ID")
    question_type: Optional[str] = Field(None, description="Detected question type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "response": "The P/E (Price-to-Earnings) ratio is...",
                "session_id": "user-123",
                "question_type": "ratio",
                "timestamp": "2024-01-22T10:30:00Z"
            }
        }


class ConversationClearRequest(BaseModel):
    """Request model for clearing conversation."""
    session_id: str = Field(default="default", description="Session ID to clear")


class HealthResponse(BaseModel):
    """Response model for health check."""
    service: str
    provider: str
    model: str
    healthy: bool
