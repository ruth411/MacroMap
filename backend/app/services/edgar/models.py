"""Data models for SEC EDGAR filings."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional


class FilingType(str, Enum):
    """SEC filing types."""
    FORM_10K = "10-K"
    FORM_10Q = "10-Q"
    FORM_8K = "8-K"

    @classmethod
    def from_string(cls, value: str) -> "FilingType":
        """Convert string to FilingType, handling variations."""
        normalized = value.upper().replace(" ", "").replace("_", "-")
        for filing_type in cls:
            if filing_type.value == normalized:
                return filing_type
        raise ValueError(f"Unknown filing type: {value}")


@dataclass
class FilingMetadata:
    """Metadata for a single SEC filing."""
    cik: str
    ticker: str
    company_name: str
    filing_type: FilingType
    filing_date: date
    accession_number: str
    primary_document: str

    @property
    def accession_number_formatted(self) -> str:
        """Return accession number without dashes for URL construction."""
        return self.accession_number.replace("-", "")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "cik": self.cik,
            "ticker": self.ticker,
            "company_name": self.company_name,
            "filing_type": self.filing_type.value,
            "filing_date": self.filing_date.isoformat(),
            "accession_number": self.accession_number,
            "primary_document": self.primary_document,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "FilingMetadata":
        """Create from dictionary."""
        return cls(
            cik=data["cik"],
            ticker=data["ticker"],
            company_name=data["company_name"],
            filing_type=FilingType.from_string(data["filing_type"]),
            filing_date=date.fromisoformat(data["filing_date"]),
            accession_number=data["accession_number"],
            primary_document=data["primary_document"],
        )


@dataclass
class Section:
    """A section extracted from a filing."""
    item_number: str  # "1", "1A", "7", etc.
    title: str  # "Business", "Risk Factors", etc.
    content: str  # Cleaned text content

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "item_number": self.item_number,
            "title": self.title,
            "content": self.content,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Section":
        """Create from dictionary."""
        return cls(
            item_number=data["item_number"],
            title=data["title"],
            content=data["content"],
        )


@dataclass
class ParsedFiling:
    """A fully parsed SEC filing."""
    metadata: FilingMetadata
    sections: dict[str, Section] = field(default_factory=dict)
    raw_text: str = ""
    parse_errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "metadata": self.metadata.to_dict(),
            "sections": {k: v.to_dict() for k, v in self.sections.items()},
            "raw_text": self.raw_text,
            "parse_errors": self.parse_errors,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ParsedFiling":
        """Create from dictionary."""
        return cls(
            metadata=FilingMetadata.from_dict(data["metadata"]),
            sections={k: Section.from_dict(v) for k, v in data.get("sections", {}).items()},
            raw_text=data.get("raw_text", ""),
            parse_errors=data.get("parse_errors", []),
        )


@dataclass
class IngestionTask:
    """Tracks the status of an ingestion task."""
    task_id: str
    ticker: str
    filing_types: list[str]
    years: int
    status: str = "pending"  # pending, processing, completed, failed
    filings_found: int = 0
    filings_processed: int = 0
    chunks_created: int = 0
    errors: list[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "task_id": self.task_id,
            "ticker": self.ticker,
            "filing_types": self.filing_types,
            "years": self.years,
            "status": self.status,
            "filings_found": self.filings_found,
            "filings_processed": self.filings_processed,
            "chunks_created": self.chunks_created,
            "errors": self.errors,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class Chunk:
    """A text chunk for RAG."""
    id: str
    text: str
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata,
        }
