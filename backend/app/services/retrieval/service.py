"""Main retrieval service for RAG."""

import logging
from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from .embeddings import EmbeddingProvider, get_embedding_provider
from .vector_store import VectorStore, get_vector_store
from .models import RetrievalQuery, RetrievalResult, Citation

if TYPE_CHECKING:
    from app.services.chunking.models import Chunk

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Main RAG retrieval service.

    Coordinates:
    - Embedding generation
    - Vector store queries
    - Metadata filtering
    - Citation formatting
    """

    # Token budget for context (rough estimate: 4 chars per token)
    MAX_CONTEXT_TOKENS = 4000
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None,
    ):
        self.embeddings = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()

    async def index_chunks(self, chunks: list["Chunk"]) -> int:
        """
        Index chunks into the vector store.

        Args:
            chunks: List of Chunk objects from ChunkingService

        Returns:
            Number of chunks indexed
        """
        if not chunks:
            return 0

        # Extract data for embedding
        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id, doc, meta = chunk.to_chroma_format()
            ids.append(chunk_id)
            documents.append(doc)
            metadatas.append(meta)

        # Generate embeddings in batches
        logger.info(f"Generating embeddings for {len(chunks)} chunks...")
        embeddings = await self.embeddings.embed_batch(documents)

        # Store in vector store
        count = self.vector_store.add_documents(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        logger.info(f"Indexed {count} chunks into vector store")
        return count

    async def retrieve(self, query: RetrievalQuery) -> RetrievalResult:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: RetrievalQuery with query text and filters

        Returns:
            RetrievalResult with chunks, citations, and formatted context
        """
        # Build metadata filter
        where_filter = self._build_where_filter(query)

        # Embed query
        query_embedding = await self.embeddings.embed_text(query.query)

        # Query vector store
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=query.top_k,
            where=where_filter,
        )

        # Build response
        chunks = []
        citations = []

        for doc_id, doc, meta, distance in zip(
            results["ids"],
            results["documents"],
            results["metadatas"],
            results["distances"],
        ):
            # Convert distance to similarity score (cosine: lower distance is better)
            score = 1 - distance

            chunks.append({
                "id": doc_id,
                "text": doc,
                "metadata": meta,
                "score": score,
            })

            citations.append(Citation(
                chunk_id=doc_id,
                ticker=meta.get("ticker", ""),
                company_name=meta.get("company_name", ""),
                filing_type=meta.get("filing_type", ""),
                filing_date=meta.get("filing_date", ""),
                section_item=meta.get("section_item", ""),
                section_title=meta.get("section_title", ""),
                relevance_score=score,
            ))

        # Format context for LLM
        formatted_context = self._format_context(chunks, citations)
        token_estimate = len(formatted_context) // self.CHARS_PER_TOKEN

        return RetrievalResult(
            chunks=chunks,
            citations=citations,
            formatted_context=formatted_context,
            total_tokens_estimate=token_estimate,
        )

    def _build_where_filter(self, query: RetrievalQuery) -> Optional[dict]:
        """Build ChromaDB where filter from query parameters."""
        conditions = []

        if query.ticker:
            conditions.append({"ticker": query.ticker.upper()})

        if query.filing_type:
            conditions.append({"filing_type": query.filing_type})

        if query.section_items:
            conditions.append({"section_item": {"$in": query.section_items}})

        # Date range filtering
        if query.date_from:
            conditions.append({
                "filing_date": {"$gte": query.date_from.isoformat()}
            })

        if query.date_to:
            conditions.append({
                "filing_date": {"$lte": query.date_to.isoformat()}
            })

        if not conditions:
            return None
        elif len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _format_context(
        self,
        chunks: list[dict],
        citations: list[Citation],
    ) -> str:
        """
        Format retrieved chunks as context for LLM.

        Uses numbered sources for citation tracking.
        """
        if not chunks:
            return ""

        sections = []

        for i, (chunk, citation) in enumerate(zip(chunks, citations), 1):
            year = citation.filing_date[:4] if citation.filing_date else "N/A"
            header = (
                f"[Source {i}] {citation.ticker} {citation.filing_type} "
                f"({year}), {citation.section_title}"
            )
            sections.append(f"{header}\n{chunk['text']}")

        return "\n\n---\n\n".join(sections)

    def format_citations_section(self, citations: list[Citation]) -> str:
        """Format citations as a references section for the response."""
        if not citations:
            return ""

        lines = ["\n\n---\n**Sources:**"]
        for i, citation in enumerate(citations, 1):
            lines.append(f"{i}. {citation.format_full()}")

        return "\n".join(lines)

    async def health_check(self) -> dict:
        """Check service health."""
        embedding_healthy = await self.embeddings.health_check()
        store_stats = self.vector_store.get_stats()

        return {
            "service": "retrieval",
            "healthy": embedding_healthy,
            "embedding_model": self.embeddings.model,
            "vector_store": store_stats,
        }


# Singleton instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get singleton retrieval service."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
