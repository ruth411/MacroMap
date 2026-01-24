"""Pydantic models for EDGAR API endpoints."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    """Request to ingest SEC filings for a company."""
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Stock ticker symbol (e.g., AAPL)",
        json_schema_extra={"example": "AAPL"}
    )
    filing_types: list[str] = Field(
        default=["10-K", "10-Q"],
        description="Filing types to ingest",
        json_schema_extra={"example": ["10-K", "10-Q"]}
    )
    years: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Number of years of filings to fetch"
    )


class IngestResponse(BaseModel):
    """Response after starting an ingestion task."""
    task_id: str = Field(..., description="Unique task identifier")
    ticker: str = Field(..., description="Stock ticker")
    status: str = Field(..., description="Task status: pending, processing, completed, failed")
    message: str = Field(..., description="Status message")


class IngestionStatusResponse(BaseModel):
    """Status of an ingestion task."""
    task_id: str
    ticker: str
    filing_types: list[str]
    years: int
    status: str
    filings_found: int = 0
    filings_processed: int = 0
    chunks_created: int = 0
    errors: list[str] = []
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class FilingInfo(BaseModel):
    """Information about a single filing."""
    filing_type: str
    filing_date: str
    accession_number: str
    company_name: Optional[str] = None
    sections: list[str] = []


class FilingListResponse(BaseModel):
    """List of filings for a company."""
    ticker: str
    filings: list[FilingInfo]
    total: int


class SectionContent(BaseModel):
    """Content of a filing section."""
    item_number: str
    title: str
    content: str


class ParsedFilingResponse(BaseModel):
    """Full parsed filing response."""
    ticker: str
    company_name: str
    filing_type: str
    filing_date: str
    accession_number: str
    sections: dict[str, SectionContent]
    parse_errors: list[str] = []


class EdgarHealthResponse(BaseModel):
    """EDGAR service health status."""
    service: str = "edgar"
    healthy: bool
    filings_dir: str
    parsed_dir: str
    active_tasks: int = 0
