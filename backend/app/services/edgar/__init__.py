"""SEC EDGAR filing ingestion service."""

from .service import EdgarService, get_edgar_service
from .client import EdgarClient, get_edgar_client, EdgarAPIError, FilingNotFoundError
from .parser import FilingParser, get_filing_parser
from .models import (
    FilingType,
    FilingMetadata,
    Section,
    ParsedFiling,
    IngestionTask,
    Chunk,
)

__all__ = [
    # Service
    "EdgarService",
    "get_edgar_service",
    # Client
    "EdgarClient",
    "get_edgar_client",
    "EdgarAPIError",
    "FilingNotFoundError",
    # Parser
    "FilingParser",
    "get_filing_parser",
    # Models
    "FilingType",
    "FilingMetadata",
    "Section",
    "ParsedFiling",
    "IngestionTask",
    "Chunk",
]
