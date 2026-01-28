"""Hybrid search combining vector and BM25 keyword search."""

import logging
import re
from typing import Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class BM25Index:
    """
    Simple BM25 index for keyword search.

    BM25 excels at exact keyword matching while vector search
    handles semantic similarity. Combining both gives best results.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.documents: list[dict] = []
        self.doc_freqs: dict[str, int] = defaultdict(int)
        self.doc_lengths: list[int] = []
        self.avg_doc_length: float = 0
        self.tokenized_docs: list[list[str]] = []
        self._indexed = False

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization for BM25."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        # Remove very short tokens
        return [t for t in tokens if len(t) > 2]

    def index(self, documents: list[dict]) -> None:
        """
        Build BM25 index from documents.

        Args:
            documents: List of dicts with 'id', 'text', 'metadata' keys
        """
        self.documents = documents
        self.tokenized_docs = []
        self.doc_lengths = []
        self.doc_freqs = defaultdict(int)

        # Tokenize all documents
        for doc in documents:
            tokens = self._tokenize(doc.get("text", ""))
            self.tokenized_docs.append(tokens)
            self.doc_lengths.append(len(tokens))

            # Count document frequencies
            unique_tokens = set(tokens)
            for token in unique_tokens:
                self.doc_freqs[token] += 1

        # Calculate average document length
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        else:
            self.avg_doc_length = 0

        self._indexed = True
        logger.info(f"BM25 index built with {len(documents)} documents")

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Search the index with BM25 scoring.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of documents with BM25 scores
        """
        if not self._indexed or not self.documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        n_docs = len(self.documents)
        scores = []

        for idx, doc_tokens in enumerate(self.tokenized_docs):
            score = 0.0
            doc_len = self.doc_lengths[idx]

            # Count term frequencies in this document
            term_freqs = defaultdict(int)
            for token in doc_tokens:
                term_freqs[token] += 1

            # Calculate BM25 score for each query term
            for token in query_tokens:
                if token not in term_freqs:
                    continue

                tf = term_freqs[token]
                df = self.doc_freqs.get(token, 0)

                # IDF component
                idf = self._idf(df, n_docs)

                # TF component with length normalization
                tf_norm = (tf * (self.k1 + 1)) / (
                    tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                )

                score += idf * tf_norm

            if score > 0:
                scores.append((idx, score))

        # Sort by score descending
        scores.sort(key=lambda x: x[1], reverse=True)

        # Return top_k results with scores
        results = []
        for idx, score in scores[:top_k]:
            doc = self.documents[idx].copy()
            doc["bm25_score"] = score
            results.append(doc)

        return results

    def _idf(self, df: int, n_docs: int) -> float:
        """Calculate IDF component."""
        import math
        if df == 0:
            return 0
        return math.log((n_docs - df + 0.5) / (df + 0.5) + 1)


class HybridSearcher:
    """
    Combines vector search with BM25 keyword search.

    Uses Reciprocal Rank Fusion (RRF) to merge results from both methods.
    """

    def __init__(self, vector_weight: float = 0.7, bm25_weight: float = 0.3):
        """
        Args:
            vector_weight: Weight for vector search results (0-1)
            bm25_weight: Weight for BM25 results (0-1)
        """
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight
        self.bm25_index = BM25Index()
        self._documents: list[dict] = []

    def index_documents(self, documents: list[dict]) -> None:
        """Index documents for BM25 search."""
        self._documents = documents
        self.bm25_index.index(documents)

    def merge_results(
        self,
        vector_results: list[dict],
        bm25_results: list[dict],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Merge vector and BM25 results using Reciprocal Rank Fusion.

        RRF formula: score = sum(1 / (k + rank)) for each result list
        where k is a constant (typically 60).

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            top_k: Number of final results

        Returns:
            Merged and reranked results
        """
        k = 60  # RRF constant

        # Calculate RRF scores
        rrf_scores: dict[str, float] = defaultdict(float)
        doc_map: dict[str, dict] = {}

        # Score vector results
        for rank, doc in enumerate(vector_results, 1):
            doc_id = doc.get("id", str(rank))
            rrf_scores[doc_id] += self.vector_weight * (1 / (k + rank))
            doc_map[doc_id] = doc

        # Score BM25 results
        for rank, doc in enumerate(bm25_results, 1):
            doc_id = doc.get("id", str(hash(doc.get("text", "")[:100])))
            rrf_scores[doc_id] += self.bm25_weight * (1 / (k + rank))
            if doc_id not in doc_map:
                doc_map[doc_id] = doc

        # Sort by RRF score
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

        # Build final results
        results = []
        for doc_id in sorted_ids[:top_k]:
            doc = doc_map[doc_id].copy()
            doc["hybrid_score"] = rrf_scores[doc_id]
            results.append(doc)

        return results


# Singleton instance
_hybrid_searcher: Optional[HybridSearcher] = None


def get_hybrid_searcher() -> HybridSearcher:
    """Get singleton hybrid searcher."""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher
