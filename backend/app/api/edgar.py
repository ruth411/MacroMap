"""API endpoints for SEC EDGAR filing ingestion."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks

from app.models.edgar import (
    IngestRequest,
    IngestResponse,
    IngestionStatusResponse,
    FilingListResponse,
    FilingInfo,
    ParsedFilingResponse,
    SectionContent,
    EdgarHealthResponse,
)
from app.services.edgar import get_edgar_service, EdgarAPIError, FilingNotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/edgar", tags=["edgar"])


async def _run_ingestion(task_id: str, ticker: str, filing_types: list[str], years: int):
    """Background task for running ingestion."""
    edgar_service = get_edgar_service()
    task = edgar_service.get_task(task_id)

    if task:
        await edgar_service.ingest_company(
            ticker=ticker,
            filing_types=filing_types,
            years=years,
            task=task,
        )


@router.post("/ingest", response_model=IngestResponse)
async def ingest_filings(
    request: IngestRequest,
    background_tasks: BackgroundTasks
) -> IngestResponse:
    """
    Start background ingestion of SEC filings for a company.

    Returns immediately with a task_id to check status.

    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT, GOOGL)
    - **filing_types**: List of filing types to ingest (default: 10-K, 10-Q)
    - **years**: Number of years of filings to fetch (default: 3)
    """
    edgar_service = get_edgar_service()

    # Validate ticker format
    ticker = request.ticker.upper().strip()
    if not ticker.isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid ticker format. Use alphanumeric characters only."
        )

    # Create task
    task = edgar_service.create_task(
        ticker=ticker,
        filing_types=request.filing_types,
        years=request.years,
    )

    # Start background ingestion
    background_tasks.add_task(
        _run_ingestion,
        task.task_id,
        ticker,
        request.filing_types,
        request.years,
    )

    return IngestResponse(
        task_id=task.task_id,
        ticker=ticker,
        status=task.status,
        message=f"Ingestion started for {ticker}. Use /status/{task.task_id} to check progress.",
    )


@router.get("/status/{task_id}", response_model=IngestionStatusResponse)
async def get_ingestion_status(task_id: str) -> IngestionStatusResponse:
    """
    Check the status of an ingestion task.

    - **task_id**: The task ID returned from /ingest
    """
    edgar_service = get_edgar_service()
    task = edgar_service.get_task(task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail=f"Task not found: {task_id}"
        )

    return IngestionStatusResponse(
        task_id=task.task_id,
        ticker=task.ticker,
        filing_types=task.filing_types,
        years=task.years,
        status=task.status,
        filings_found=task.filings_found,
        filings_processed=task.filings_processed,
        chunks_created=task.chunks_created,
        errors=task.errors,
        started_at=task.started_at,
        completed_at=task.completed_at,
    )


@router.get("/filings/{ticker}", response_model=FilingListResponse)
async def list_filings(
    ticker: str,
    filing_type: Optional[str] = None
) -> FilingListResponse:
    """
    List all ingested filings for a company.

    - **ticker**: Stock ticker symbol
    - **filing_type**: Optional filter by filing type (10-K, 10-Q, 8-K)
    """
    edgar_service = get_edgar_service()

    filings = await edgar_service.list_filings(
        ticker=ticker.upper(),
        filing_type=filing_type,
    )

    return FilingListResponse(
        ticker=ticker.upper(),
        filings=[
            FilingInfo(
                filing_type=f.get("filing_type", ""),
                filing_date=f.get("filing_date", ""),
                accession_number=f.get("accession_number", ""),
                company_name=f.get("company_name"),
                sections=f.get("sections", []),
            )
            for f in filings
        ],
        total=len(filings),
    )


@router.get("/filings/{ticker}/{accession_number}", response_model=ParsedFilingResponse)
async def get_filing(ticker: str, accession_number: str) -> ParsedFilingResponse:
    """
    Get a specific parsed filing.

    - **ticker**: Stock ticker symbol
    - **accession_number**: SEC accession number (e.g., 0000320193-23-000106)
    """
    edgar_service = get_edgar_service()

    parsed = await edgar_service.get_filing(
        ticker=ticker.upper(),
        accession_number=accession_number,
    )

    if not parsed:
        raise HTTPException(
            status_code=404,
            detail=f"Filing not found: {ticker}/{accession_number}"
        )

    return ParsedFilingResponse(
        ticker=parsed.metadata.ticker,
        company_name=parsed.metadata.company_name,
        filing_type=parsed.metadata.filing_type.value,
        filing_date=parsed.metadata.filing_date.isoformat(),
        accession_number=parsed.metadata.accession_number,
        sections={
            k: SectionContent(
                item_number=v.item_number,
                title=v.title,
                content=v.content[:5000] + "..." if len(v.content) > 5000 else v.content,
            )
            for k, v in parsed.sections.items()
        },
        parse_errors=parsed.parse_errors,
    )


@router.get("/health", response_model=EdgarHealthResponse)
async def edgar_health() -> EdgarHealthResponse:
    """Health check for EDGAR service."""
    edgar_service = get_edgar_service()
    health = await edgar_service.health_check()

    return EdgarHealthResponse(
        service=health["service"],
        healthy=health["healthy"],
        filings_dir=health["filings_dir"],
        parsed_dir=health["parsed_dir"],
        active_tasks=health["active_tasks"],
    )
