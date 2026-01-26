"""Main retrieval service for RAG with reranking support."""

import logging
from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from .embeddings import EmbeddingProvider, get_embedding_provider
from .vector_store import VectorStore, get_vector_store
from .reranker import BaseReranker, get_reranker
from .models import RetrievalQuery, RetrievalResult, Citation

if TYPE_CHECKING:
    from app.services.chunking.models import Chunk

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    Main RAG retrieval service with reranking support.

    Coordinates:
    - Embedding generation
    - Vector store queries
    - Reranking for improved relevance
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
        reranker: Optional[BaseReranker] = None,
    ):
        self.embeddings = embedding_provider or get_embedding_provider()
        self.vector_store = vector_store or get_vector_store()

        # Initialize reranker based on settings
        if settings.reranker_enabled:
            self.reranker = reranker or get_reranker(
                reranker_type=settings.reranker_type,
                model_name=settings.reranker_model,
            )
            self.reranking_enabled = True
            logger.info(f"Reranking enabled with {settings.reranker_type}")
        else:
            self.reranker = None
            self.reranking_enabled = False
            logger.info("Reranking disabled")

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
        Retrieve relevant chunks for a query with optional reranking.

        The retrieval pipeline:
        1. Embed the query
        2. Fetch initial candidates from vector store (more than needed)
        3. Rerank candidates using cross-encoder (if enabled)
        4. Return top_k most relevant results

        Args:
            query: RetrievalQuery with query text and filters

        Returns:
            RetrievalResult with chunks, citations, and formatted context
        """
        # Build metadata filter
        where_filter = self._build_where_filter(query)

        # Embed query
        query_embedding = await self.embeddings.embed_text(query.query)

        # Determine how many results to fetch initially
        # If reranking is enabled, fetch more candidates for better reranking results
        if self.reranking_enabled:
            initial_k = max(query.top_k, settings.retrieval_initial_k)
        else:
            initial_k = query.top_k

        # Query vector store for initial candidates
        results = self.vector_store.query(
            query_embedding=query_embedding,
            n_results=initial_k,
            where=where_filter,
        )

        # Build initial chunk list
        initial_chunks = []

        for doc_id, doc, meta, distance in zip(
            results["ids"],
            results["documents"],
            results["metadatas"],
            results["distances"],
        ):
            # Convert distance to similarity score (cosine: lower distance is better)
            score = 1 - distance

            initial_chunks.append({
                "id": doc_id,
                "text": doc,
                "metadata": meta,
                "score": score,
            })

        # Apply reranking if enabled
        if self.reranking_enabled and self.reranker and len(initial_chunks) > 1:
            logger.debug(f"Reranking {len(initial_chunks)} chunks...")
            reranked_chunks = await self.reranker.rerank(
                query=query.query,
                documents=initial_chunks,
                top_k=query.top_k,
            )
            chunks = reranked_chunks
            logger.debug(f"Reranking complete, returning top {len(chunks)} results")
        else:
            # No reranking, just take top_k
            chunks = initial_chunks[:query.top_k]

        # Build citations from final chunks
        citations = []
        for chunk in chunks:
            meta = chunk["metadata"]
            # Use rerank_score if available, otherwise use original score
            score = chunk.get("rerank_score", chunk.get("score", 0))

            citations.append(Citation(
                chunk_id=chunk["id"],
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

        reranker_info = {
            "enabled": self.reranking_enabled,
            "type": settings.reranker_type if self.reranking_enabled else None,
            "model": settings.reranker_model if self.reranking_enabled else None,
        }

        return {
            "service": "retrieval",
            "healthy": embedding_healthy,
            "embedding_model": self.embeddings.model,
            "vector_store": store_stats,
            "reranker": reranker_info,
        }


# Singleton instance
_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    """Get singleton retrieval service."""
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
