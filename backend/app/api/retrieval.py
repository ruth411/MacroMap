"""API endpoints for RAG retrieval management."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from app.services.retrieval.service import get_retrieval_service
from app.services.retrieval.vector_store import get_vector_store
from app.services.retrieval.models import RetrievalQuery
from app.services.edgar.service import get_edgar_service
from app.services.chunking.service import get_chunking_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/retrieval", tags=["retrieval"])


class IndexRequest(BaseModel):
    """Request to index filings for a ticker."""
    ticker: str = Field(..., description="Ticker to index")


class IndexResponse(BaseModel):
    """Response after indexing."""
    ticker: str
    chunks_indexed: int
    status: str


class SearchRequest(BaseModel):
    """Direct search request."""
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    ticker: Optional[str] = None
    filing_type: Optional[str] = None


class SearchResult(BaseModel):
    """A single search result."""
    id: str
    text: str
    score: float
    ticker: str
    filing_type: str
    filing_date: str
    section_title: str


class SearchResponse(BaseModel):
    """Search results."""
    query: str
    results: list[SearchResult]
    total: int


class RetrievalStatsResponse(BaseModel):
    """Statistics for the retrieval service."""
    service: str
    healthy: bool
    embedding_model: str
    document_count: int


class IndexAllRequest(BaseModel):
    """Request to index all tickers."""
    pass


async def _index_ticker_task(ticker: str) -> int:
    """Background task to index a ticker."""
    edgar_service = get_edgar_service()
    retrieval_service = get_retrieval_service()
    chunking_service = get_chunking_service()

    # Get all parsed filings
    filings = await edgar_service.list_filings(ticker.upper())

    if not filings:
        return 0

    # Load and chunk each filing
    all_chunks = []
    for filing_info in filings:
        parsed = await edgar_service.get_filing(
            ticker.upper(),
            filing_info["accession_number"],
        )
        if parsed:
            chunks = chunking_service.chunk_filing(parsed)
            all_chunks.extend(chunks)

    # Index chunks
    if all_chunks:
        indexed = await retrieval_service.index_chunks(all_chunks)
        return indexed
    return 0


@router.post("/index", response_model=IndexResponse)
async def index_ticker(request: IndexRequest) -> IndexResponse:
    """
    Index all filings for a ticker into the vector store.

    This chunks and embeds all parsed filings for the ticker.
    """
    ticker = request.ticker.upper()

    try:
        indexed = await _index_ticker_task(ticker)

        if indexed == 0:
            raise HTTPException(
                status_code=404,
                detail=f"No filings found for {ticker}. Ingest filings first."
            )

        return IndexResponse(
            ticker=ticker,
            chunks_indexed=indexed,
            status="completed",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Indexing failed for {ticker}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Indexing failed: {str(e)}"
        )


@router.post("/index-all", response_model=dict)
async def index_all_tickers(background_tasks: BackgroundTasks) -> dict:
    """
    Index all tickers with parsed filings (runs in background).
    """
    from app.core.config import settings

    parsed_dir = settings.parsed_dir
    if not parsed_dir.exists():
        raise HTTPException(
            status_code=404,
            detail="No parsed filings found"
        )

    tickers = [d.name for d in parsed_dir.iterdir() if d.is_dir()]

    if not tickers:
        raise HTTPException(
            status_code=404,
            detail="No tickers found in parsed directory"
        )

    async def index_all():
        total = 0
        for ticker in tickers:
            try:
                indexed = await _index_ticker_task(ticker)
                total += indexed
                logger.info(f"Indexed {ticker}: {indexed} chunks")
            except Exception as e:
                logger.error(f"Failed to index {ticker}: {e}")
        logger.info(f"Total indexed: {total} chunks")

    background_tasks.add_task(index_all)

    return {
        "status": "started",
        "tickers": tickers,
        "message": f"Indexing {len(tickers)} tickers in background",
    }


@router.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """
    Direct semantic search for testing/debugging.
    """
    retrieval_service = get_retrieval_service()

    query = RetrievalQuery(
        query=request.query,
        top_k=request.top_k,
        ticker=request.ticker,
        filing_type=request.filing_type,
    )

    result = await retrieval_service.retrieve(query)

    return SearchResponse(
        query=request.query,
        results=[
            SearchResult(
                id=chunk["id"],
                text=chunk["text"][:500] + "..." if len(chunk["text"]) > 500 else chunk["text"],
                score=chunk["score"],
                ticker=chunk["metadata"].get("ticker", ""),
                filing_type=chunk["metadata"].get("filing_type", ""),
                filing_date=chunk["metadata"].get("filing_date", ""),
                section_title=chunk["metadata"].get("section_title", ""),
            )
            for chunk in result.chunks
        ],
        total=len(result.chunks),
    )


@router.get("/stats", response_model=RetrievalStatsResponse)
async def get_stats() -> RetrievalStatsResponse:
    """Get vector store statistics."""
    retrieval_service = get_retrieval_service()
    health = await retrieval_service.health_check()

    return RetrievalStatsResponse(
        service=health["service"],
        healthy=health["healthy"],
        embedding_model=health["embedding_model"],
        document_count=health["vector_store"]["document_count"],
    )


@router.get("/stats/{ticker}")
async def get_ticker_stats(ticker: str) -> dict:
    """Get stats for a specific ticker."""
    vector_store = get_vector_store()
    count = vector_store.count_by_ticker(ticker.upper())

    return {
        "ticker": ticker.upper(),
        "document_count": count,
    }


@router.delete("/{ticker}")
async def delete_ticker(ticker: str) -> dict:
    """Delete all indexed documents for a ticker."""
    vector_store = get_vector_store()
    deleted = vector_store.delete_by_ticker(ticker.upper())

    return {
        "ticker": ticker.upper(),
        "deleted": deleted,
        "status": "completed",
    }


@router.post("/reset")
async def reset_vector_store() -> dict:
    """
    Reset the vector store by deleting and recreating the collection.

    Use this when embedding dimensions change or to clear all data.
    WARNING: This deletes all indexed documents!
    """
    vector_store = get_vector_store()
    old_count = vector_store.count()

    vector_store.reset_collection()

    return {
        "status": "reset_complete",
        "documents_deleted": old_count,
        "message": "Vector store has been reset. Re-index your documents.",
    }


@router.get("/health")
async def retrieval_health() -> dict:
    """Health check for retrieval service."""
    retrieval_service = get_retrieval_service()
    health = await retrieval_service.health_check()

    return {
        "service": health["service"],
        "healthy": health["healthy"],
        "embedding_model": health["embedding_model"],
        "vector_store": health["vector_store"],
    }
