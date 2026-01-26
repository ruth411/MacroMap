"""Reranker service for RAG retrieval."""

import logging
from typing import Optional
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseReranker(ABC):
    """Abstract base class for rerankers."""

    @abstractmethod
    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents based on relevance to query.

        Args:
            query: The search query
            documents: List of documents with 'text' and 'metadata' keys
            top_k: Number of top results to return

        Returns:
            Reranked list of documents with updated scores
        """
        pass


class CrossEncoderReranker(BaseReranker):
    """
    Reranker using a cross-encoder model for semantic similarity.

    Cross-encoders are more accurate than bi-encoders for reranking
    because they process query and document together.
    """

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
    ):
        self.model_name = model_name
        self._model = None

    def _get_model(self):
        """Lazy load the cross-encoder model."""
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading cross-encoder model: {self.model_name}")
                self._model = CrossEncoder(self.model_name)
                logger.info("Cross-encoder model loaded successfully")
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
                raise
        return self._model

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rerank documents using cross-encoder scoring.

        Args:
            query: The search query
            documents: List of dicts with 'text', 'metadata', 'id', and 'score' keys
            top_k: Number of top results to return

        Returns:
            Reranked list of documents sorted by cross-encoder score
        """
        if not documents:
            return []

        if len(documents) <= 1:
            return documents

        try:
            model = self._get_model()

            # Create query-document pairs
            pairs = [(query, doc["text"]) for doc in documents]

            # Get cross-encoder scores
            scores = model.predict(pairs)

            # Attach rerank scores to documents
            for doc, score in zip(documents, scores):
                doc["rerank_score"] = float(score)
                doc["original_score"] = doc.get("score", 0)

            # Sort by rerank score (descending)
            reranked = sorted(
                documents,
                key=lambda x: x["rerank_score"],
                reverse=True
            )

            # Return top_k results
            return reranked[:top_k]

        except Exception as e:
            logger.error(f"Reranking failed: {e}. Returning original order.")
            # Fallback to original order
            return documents[:top_k]


class CohereReranker(BaseReranker):
    """
    Reranker using Cohere's rerank API.

    Requires COHERE_API_KEY environment variable.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "rerank-english-v3.0"):
        import os
        self.api_key = api_key or os.getenv("COHERE_API_KEY")
        self.model = model
        self._client = None

    def _get_client(self):
        """Lazy load the Cohere client."""
        if self._client is None:
            try:
                import cohere
                if not self.api_key:
                    raise ValueError("COHERE_API_KEY not set")
                self._client = cohere.Client(self.api_key)
            except ImportError:
                logger.warning("cohere not installed. Install with: pip install cohere")
                raise
        return self._client

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Rerank using Cohere API."""
        if not documents:
            return []

        try:
            client = self._get_client()

            # Extract texts
            texts = [doc["text"] for doc in documents]

            # Call Cohere rerank
            response = client.rerank(
                model=self.model,
                query=query,
                documents=texts,
                top_n=top_k,
            )

            # Reorder documents based on response
            reranked = []
            for result in response.results:
                doc = documents[result.index].copy()
                doc["rerank_score"] = result.relevance_score
                doc["original_score"] = doc.get("score", 0)
                reranked.append(doc)

            return reranked

        except Exception as e:
            logger.error(f"Cohere reranking failed: {e}. Returning original order.")
            return documents[:top_k]


class NoOpReranker(BaseReranker):
    """No-op reranker that returns documents in original order."""

    async def rerank(
        self,
        query: str,
        documents: list[dict],
        top_k: int = 5,
    ) -> list[dict]:
        """Return documents in original order (no reranking)."""
        return documents[:top_k]


# Singleton instance
_reranker: Optional[BaseReranker] = None


def get_reranker(
    reranker_type: str = "cross-encoder",
    model_name: Optional[str] = None,
) -> BaseReranker:
    """
    Get reranker instance.

    Args:
        reranker_type: Type of reranker ("cross-encoder", "cohere", "none")
        model_name: Optional model name override

    Returns:
        Reranker instance
    """
    global _reranker

    if _reranker is not None:
        return _reranker

    if reranker_type == "cross-encoder":
        model = model_name or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        _reranker = CrossEncoderReranker(model_name=model)
    elif reranker_type == "cohere":
        model = model_name or "rerank-english-v3.0"
        _reranker = CohereReranker(model=model)
    elif reranker_type == "none":
        _reranker = NoOpReranker()
    else:
        logger.warning(f"Unknown reranker type: {reranker_type}. Using cross-encoder.")
        _reranker = CrossEncoderReranker()

    return _reranker


def reset_reranker():
    """Reset the singleton reranker (useful for testing)."""
    global _reranker
    _reranker = None
