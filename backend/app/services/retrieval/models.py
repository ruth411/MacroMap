"""Data models for retrieval service."""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class RetrievalQuery:
    """Query parameters for retrieval."""
    query: str
    top_k: int = 5
    ticker: Optional[str] = None
    filing_type: Optional[str] = None  # "10-K", "10-Q"
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    section_items: Optional[list[str]] = None  # ["1A", "7", "7A"]


@dataclass
class Citation:
    """A citation reference for a retrieved chunk."""
    chunk_id: str
    ticker: str
    company_name: str
    filing_type: str
    filing_date: str
    section_item: str
    section_title: str
    relevance_score: float

    def format_short(self) -> str:
        """Format as inline citation, e.g., [AAPL 10-K 2024, Item 1A]."""
        year = self.filing_date[:4] if self.filing_date else "N/A"
        return f"[{self.ticker} {self.filing_type} {year}, Item {self.section_item}]"

    def format_full(self) -> str:
        """Format as full citation for reference section."""
        return (
            f"{self.company_name} ({self.ticker}) - {self.filing_type} "
            f"filed {self.filing_date}, {self.section_title} (Item {self.section_item})"
        )


@dataclass
class RetrievalResult:
    """Result from a retrieval query."""
    chunks: list[dict] = field(default_factory=list)  # List of {text, metadata, score}
    citations: list[Citation] = field(default_factory=list)
    formatted_context: str = ""
    total_tokens_estimate: int = 0

    @property
    def has_results(self) -> bool:
        """Check if any results were found."""
        return len(self.chunks) > 0


@dataclass
class EmbeddingResult:
    """Result from embedding operation."""
    embeddings: list[list[float]]
    model: str
    token_count: int = 0
