"""ChromaDB vector store for RAG."""

import logging
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    ChromaDB vector store for SEC filing chunks.

    Features:
    - Persistent storage in data/chroma
    - Metadata filtering (ticker, filing_type, date range)
    - Upsert support for re-indexing
    """

    def __init__(
        self,
        collection_name: Optional[str] = None,
        persist_directory: Optional[str] = None,
    ):
        self.collection_name = collection_name or settings.chroma_collection_name
        self.persist_directory = persist_directory or str(settings.chroma_dir)

        # Ensure directory exists
        settings.chroma_dir.mkdir(parents=True, exist_ok=True)

        # Initialize persistent client
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        # Get or create collection
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},  # Use cosine similarity
        )

        logger.info(
            f"VectorStore initialized: {self.collection_name} "
            f"({self._collection.count()} documents)"
        )

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
    ) -> int:
        """
        Add documents to the vector store.

        Uses upsert to handle re-indexing gracefully.

        Args:
            ids: Document IDs
            documents: Text content
            embeddings: Embedding vectors
            metadatas: Metadata dictionaries

        Returns:
            Number of documents added
        """
        if not ids:
            return 0

        self._collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Upserted {len(ids)} documents to {self.collection_name}")
        return len(ids)

    def query(
        self,
        query_embedding: list[float],
        n_results: int = 5,
        where: Optional[dict] = None,
        where_document: Optional[dict] = None,
    ) -> dict:
        """
        Query the vector store.

        Args:
            query_embedding: Query vector
            n_results: Number of results to return
            where: Metadata filter (e.g., {"ticker": "AAPL"})
            where_document: Document content filter

        Returns:
            Dict with ids, documents, metadatas, distances
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            where_document=where_document,
            include=["documents", "metadatas", "distances"],
        )

        return {
            "ids": results["ids"][0] if results["ids"] else [],
            "documents": results["documents"][0] if results["documents"] else [],
            "metadatas": results["metadatas"][0] if results["metadatas"] else [],
            "distances": results["distances"][0] if results["distances"] else [],
        }

    def get_by_ticker(self, ticker: str, limit: int = 100) -> dict:
        """Get all documents for a ticker."""
        results = self._collection.get(
            where={"ticker": ticker.upper()},
            limit=limit,
            include=["documents", "metadatas"],
        )
        return {
            "ids": results["ids"] if results["ids"] else [],
            "documents": results["documents"] if results["documents"] else [],
            "metadatas": results["metadatas"] if results["metadatas"] else [],
        }

    def delete_by_ticker(self, ticker: str) -> int:
        """Delete all documents for a ticker."""
        # Get IDs to delete
        results = self._collection.get(
            where={"ticker": ticker.upper()},
            include=[],
        )

        if results["ids"]:
            self._collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} documents for {ticker}")
            return len(results["ids"])
        return 0

    def count(self) -> int:
        """Get total document count."""
        return self._collection.count()

    def count_by_ticker(self, ticker: str) -> int:
        """Get document count for a specific ticker."""
        results = self._collection.get(
            where={"ticker": ticker.upper()},
            include=[],
        )
        return len(results["ids"]) if results["ids"] else 0

    def get_stats(self) -> dict:
        """Get collection statistics."""
        return {
            "collection_name": self.collection_name,
            "document_count": self._collection.count(),
            "persist_directory": self.persist_directory,
        }


# Singleton instance
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get singleton vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
