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
    # RAG parameters
    use_rag: bool = Field(default=True, description="Enable RAG context retrieval")
    ticker_filter: Optional[str] = Field(None, description="Filter retrieval to specific ticker")
    filing_type_filter: Optional[str] = Field(None, description="Filter by filing type (10-K, 10-Q)")

    class Config:
        json_schema_extra = {
            "example": {
                "message": "What are Apple's main risk factors?",
                "session_id": "user-123",
                "use_templates": True,
                "use_rag": True,
                "ticker_filter": "AAPL"
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint."""
    response: str = Field(..., description="Assistant's response")
    session_id: str = Field(..., description="Conversation session ID")
    question_type: Optional[str] = Field(None, description="Detected question type")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    # RAG metadata
    sources_used: int = Field(default=0, description="Number of sources retrieved")
    citations: list[str] = Field(default_factory=list, description="Source citations")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "Based on Apple's 10-K filing, the main risk factors include...",
                "session_id": "user-123",
                "question_type": "general",
                "timestamp": "2024-01-22T10:30:00Z",
                "sources_used": 3,
                "citations": ["Apple Inc. (AAPL) - 10-K filed 2024-10-31, Risk Factors (Item 1A)"]
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
