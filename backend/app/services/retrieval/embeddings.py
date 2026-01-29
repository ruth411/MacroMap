"""Embedding provider for RAG using OpenAI."""

import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingProvider:
    """
    OpenAI embedding provider.

    Uses text-embedding-3-large for highest quality retrieval.
    Supports batching for efficient bulk embedding.
    """

    MODEL = "text-embedding-3-large"
    DIMENSIONS = 3072
    MAX_BATCH_SIZE = 2048  # OpenAI limit

    def __init__(self, api_key: Optional[str] = None):
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)
        self.model = self.MODEL

    async def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector (3072 dimensions)
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """
        Embed multiple texts with batching.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call (max 2048)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            logger.info(
                f"Embedding batch {i // batch_size + 1}/{(len(texts) - 1) // batch_size + 1}, "
                f"size {len(batch)}"
            )

            response = await self.client.embeddings.create(
                model=self.model,
                input=batch,
            )

            # Sort by index to maintain order
            batch_embeddings: list[Optional[list[float]]] = [None] * len(batch)
            for item in response.data:
                batch_embeddings[item.index] = item.embedding

            # Filter out any None values (shouldn't happen but be safe)
            all_embeddings.extend([e for e in batch_embeddings if e is not None])

        return all_embeddings

    async def health_check(self) -> bool:
        """Check if embedding API is accessible."""
        try:
            await self.embed_text("test")
            return True
        except Exception as e:
            logger.error(f"Embedding health check failed: {e}")
            return False


# Singleton instance
_embedding_provider: Optional[EmbeddingProvider] = None


def get_embedding_provider() -> EmbeddingProvider:
    """Get singleton embedding provider."""
    global _embedding_provider
    if _embedding_provider is None:
        _embedding_provider = EmbeddingProvider()
    return _embedding_provider
