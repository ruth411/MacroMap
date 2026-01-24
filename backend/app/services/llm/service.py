"""
LLM Service for MacroMap

Main service that handles chat interactions, manages conversation history,
and coordinates between prompts and LLM providers.
"""

from typing import Optional
from dataclasses import dataclass, field

from app.core.config import settings
from .prompts import FinancialPrompts
from .providers import get_provider, BaseLLMProvider


@dataclass
class Message:
    """Represents a chat message."""
    role: str  # "user", "assistant", or "system"
    content: str


@dataclass
class Conversation:
    """Manages a conversation with history."""
    messages: list[Message] = field(default_factory=list)
    max_history: int = 10

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation."""
        self.messages.append(Message(role=role, content=content))
        # Keep only the last N messages (plus system prompt)
        if len(self.messages) > self.max_history + 1:
            # Preserve system message if it exists
            if self.messages[0].role == "system":
                self.messages = [self.messages[0]] + self.messages[-(self.max_history):]
            else:
                self.messages = self.messages[-(self.max_history):]

    def to_dict_list(self) -> list[dict]:
        """Convert messages to list of dicts for LLM API."""
        return [{"role": m.role, "content": m.content} for m in self.messages]

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []


class LLMService:
    """
    Main LLM service for handling chat interactions.

    This service:
    - Manages the LLM provider
    - Applies prompt engineering
    - Handles conversation context
    - Detects question types for optimal responses
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        """Initialize the LLM service."""
        self.provider = provider or get_provider()
        self.conversations: dict[str, Conversation] = {}

    def get_or_create_conversation(self, session_id: str) -> Conversation:
        """Get existing conversation or create a new one."""
        if session_id not in self.conversations:
            conv = Conversation(max_history=settings.max_history_length)
            # Add system prompt
            conv.add_message("system", FinancialPrompts.get_system_prompt())
            self.conversations[session_id] = conv
        return self.conversations[session_id]

    async def chat(
        self,
        message: str,
        session_id: str = "default",
        context: Optional[str] = None,
    ) -> str:
        """
        Process a chat message and return the response.

        Args:
            message: User's message
            session_id: Conversation session ID
            context: Optional RAG context to include

        Returns:
            Assistant's response
        """
        conversation = self.get_or_create_conversation(session_id)

        # Detect question type and format with appropriate template
        question_type = FinancialPrompts.detect_question_type(message)
        formatted_message = FinancialPrompts.format_user_message(
            question=message,
            template_type=question_type,
            context=context,
        )

        # Add user message to conversation
        conversation.add_message("user", formatted_message)

        # Generate response
        response = await self.provider.generate(
            messages=conversation.to_dict_list(),
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

        # Add assistant response to conversation
        conversation.add_message("assistant", response)

        return response

    async def simple_chat(
        self,
        message: str,
        session_id: str = "default",
    ) -> str:
        """
        Simple chat without template formatting.
        Useful when you want raw conversation without question type detection.

        Args:
            message: User's message
            session_id: Conversation session ID

        Returns:
            Assistant's response
        """
        conversation = self.get_or_create_conversation(session_id)

        # Add user message directly
        conversation.add_message("user", message)

        # Generate response
        response = await self.provider.generate(
            messages=conversation.to_dict_list(),
            max_tokens=settings.max_tokens,
            temperature=settings.temperature,
        )

        # Add assistant response
        conversation.add_message("assistant", response)

        return response

    def clear_conversation(self, session_id: str) -> None:
        """Clear a conversation's history."""
        if session_id in self.conversations:
            self.conversations[session_id].clear()
            # Re-add system prompt
            self.conversations[session_id].add_message(
                "system", FinancialPrompts.get_system_prompt()
            )

    def delete_conversation(self, session_id: str) -> None:
        """Delete a conversation entirely."""
        if session_id in self.conversations:
            del self.conversations[session_id]

    async def health_check(self) -> dict:
        """Check the health of the LLM service."""
        provider_healthy = await self.provider.health_check()
        return {
            "service": "llm",
            "provider": settings.llm_provider,
            "model": self._get_model_name(),
            "healthy": provider_healthy,
        }

    def _get_model_name(self) -> str:
        """Get the current model name based on provider."""
        if settings.llm_provider == "openai":
            return settings.openai_model
        elif settings.llm_provider == "ollama":
            return settings.ollama_model
        elif settings.llm_provider == "bedrock":
            return settings.bedrock_model_id
        elif settings.llm_provider == "huggingface":
            return settings.hf_model_id
        return "unknown"


# Global service instance (lazy initialization)
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
