"""Main EDGAR service for filing ingestion."""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.services.chunking import ChunkingService, get_chunking_service, Chunk
from .client import EdgarClient, get_edgar_client, EdgarAPIError
from .parser import FilingParser, get_filing_parser
from .models import (
    FilingMetadata,
    ParsedFiling,
    IngestionTask,
    FilingType,
)

logger = logging.getLogger(__name__)


class EdgarService:
    """
    Main EDGAR service for filing ingestion.

    Coordinates between:
    - EdgarClient: Fetches filings from SEC
    - FilingParser: Parses HTML to extract sections
    - ChunkingService: Chunks sections for RAG
    - Storage: Persists raw and parsed filings
    """

    def __init__(
        self,
        client: Optional[EdgarClient] = None,
        parser: Optional[FilingParser] = None,
        chunking_service: Optional[ChunkingService] = None,
    ):
        self.client = client or get_edgar_client()
        self.parser = parser or get_filing_parser()
        self.chunking_service = chunking_service or get_chunking_service()

        # Storage paths
        self.filings_dir = settings.filings_dir
        self.parsed_dir = settings.parsed_dir

        # In-memory task tracking (would use database in production)
        self._tasks: dict[str, IngestionTask] = {}

    def _get_filing_path(self, filing: FilingMetadata) -> Path:
        """Get path for storing raw filing HTML."""
        return (
            self.filings_dir
            / filing.ticker
            / filing.filing_type.value
            / f"{filing.accession_number}.html"
        )

    def _get_parsed_path(self, filing: FilingMetadata) -> Path:
        """Get path for storing parsed filing JSON."""
        return (
            self.parsed_dir
            / filing.ticker
            / filing.filing_type.value
            / f"{filing.accession_number}.json"
        )

    async def _save_raw_filing(self, filing: FilingMetadata, content: str) -> Path:
        """Save raw HTML filing to disk."""
        path = self._get_filing_path(filing)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Saved raw filing to {path}")
        return path

    async def _save_parsed_filing(self, parsed: ParsedFiling) -> Path:
        """Save parsed filing to disk as JSON."""
        path = self._get_parsed_path(parsed.metadata)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(parsed.to_dict(), indent=2),
            encoding="utf-8"
        )
        logger.info(f"Saved parsed filing to {path}")
        return path

    async def _load_parsed_filing(self, filing: FilingMetadata) -> Optional[ParsedFiling]:
        """Load parsed filing from disk if it exists."""
        path = self._get_parsed_path(filing)
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return ParsedFiling.from_dict(data)
        return None

    def create_task(
        self,
        ticker: str,
        filing_types: list[str],
        years: int
    ) -> IngestionTask:
        """Create a new ingestion task."""
        task_id = f"ingest-{ticker.lower()}-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        task = IngestionTask(
            task_id=task_id,
            ticker=ticker.upper(),
            filing_types=filing_types,
            years=years,
            status="pending",
            started_at=datetime.now(),
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[IngestionTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def ingest_company(
        self,
        ticker: str,
        filing_types: list[str],
        years: int = 3,
        task: Optional[IngestionTask] = None,
    ) -> tuple[list[ParsedFiling], list[Chunk]]:
        """
        Ingest SEC filings for a company.

        Args:
            ticker: Stock ticker symbol
            filing_types: List of filing types (e.g., ["10-K", "10-Q"])
            years: Number of years to fetch
            task: Optional task for progress tracking

        Returns:
            Tuple of (parsed_filings, chunks)
        """
        if task:
            task.status = "processing"

        parsed_filings: list[ParsedFiling] = []
        all_chunks: list[Chunk] = []
        errors: list[str] = []

        try:
            # Get list of filings
            logger.info(f"Fetching filing list for {ticker}")
            filings = await self.client.get_company_filings(
                ticker=ticker,
                filing_types=filing_types,
                years=years,
            )

            if task:
                task.filings_found = len(filings)

            logger.info(f"Found {len(filings)} filings for {ticker}")

            # Process each filing
            for i, filing in enumerate(filings):
                try:
                    logger.info(
                        f"Processing filing {i+1}/{len(filings)}: "
                        f"{filing.filing_type.value} ({filing.filing_date})"
                    )

                    # Check if already parsed
                    parsed = await self._load_parsed_filing(filing)

                    if not parsed:
                        # Download and parse
                        html_content = await self.client.get_filing_document(filing)
                        await self._save_raw_filing(filing, html_content)

                        parsed = self.parser.parse(html_content, filing)
                        await self._save_parsed_filing(parsed)

                    parsed_filings.append(parsed)

                    # Chunk the filing
                    chunks = self.chunking_service.chunk_filing(parsed)
                    all_chunks.extend(chunks)

                    if task:
                        task.filings_processed += 1
                        task.chunks_created += len(chunks)

                except Exception as e:
                    error_msg = f"Error processing {filing.accession_number}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    if task:
                        task.errors.append(error_msg)

            if task:
                task.status = "completed"
                task.completed_at = datetime.now()

        except EdgarAPIError as e:
            error_msg = f"EDGAR API error: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
            if task:
                task.status = "failed"
                task.errors.append(error_msg)
                task.completed_at = datetime.now()

        return parsed_filings, all_chunks

    async def get_filing(
        self,
        ticker: str,
        accession_number: str
    ) -> Optional[ParsedFiling]:
        """Get a specific parsed filing."""
        # Check all filing types
        for filing_type in FilingType:
            path = (
                self.parsed_dir
                / ticker.upper()
                / filing_type.value
                / f"{accession_number}.json"
            )
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                return ParsedFiling.from_dict(data)
        return None

    async def list_filings(
        self,
        ticker: str,
        filing_type: Optional[str] = None
    ) -> list[dict]:
        """List all ingested filings for a company."""
        filings: list[dict] = []
        ticker_dir = self.parsed_dir / ticker.upper()

        if not ticker_dir.exists():
            return filings

        # Iterate through filing type directories
        for type_dir in ticker_dir.iterdir():
            if not type_dir.is_dir():
                continue

            if filing_type and type_dir.name != filing_type:
                continue

            # List JSON files
            for json_file in type_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    metadata = data.get("metadata", {})
                    filings.append({
                        "filing_type": metadata.get("filing_type"),
                        "filing_date": metadata.get("filing_date"),
                        "accession_number": metadata.get("accession_number"),
                        "company_name": metadata.get("company_name"),
                        "sections": list(data.get("sections", {}).keys()),
                    })
                except Exception as e:
                    logger.warning(f"Error reading {json_file}: {e}")

        # Sort by date descending
        filings.sort(key=lambda x: x.get("filing_date", ""), reverse=True)
        return filings

    async def health_check(self) -> dict:
        """Check service health."""
        edgar_healthy = await self.client.health_check()
        return {
            "service": "edgar",
            "healthy": edgar_healthy,
            "filings_dir": str(self.filings_dir),
            "parsed_dir": str(self.parsed_dir),
            "active_tasks": len([t for t in self._tasks.values() if t.status == "processing"]),
        }


# Singleton instance
_edgar_service: Optional[EdgarService] = None


def get_edgar_service() -> EdgarService:
    """Get singleton EdgarService instance."""
    global _edgar_service
    if _edgar_service is None:
        _edgar_service = EdgarService()
    return _edgar_service
