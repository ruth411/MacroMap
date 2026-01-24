"""Data models for text chunking."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChunkMetadata:
    """Metadata for a text chunk."""
    ticker: str
    company_name: str
    filing_type: str
    filing_date: str
    accession_number: str
    section_item: str
    section_title: str
    chunk_index: int
    total_chunks: int

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "filing_type": self.filing_type,
            "filing_date": self.filing_date,
            "accession_number": self.accession_number,
            "section_item": self.section_item,
            "section_title": self.section_title,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
        }


@dataclass
class Chunk:
    """A text chunk for RAG retrieval."""
    id: str
    text: str
    metadata: ChunkMetadata

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata.to_dict(),
        }

    def to_chroma_format(self) -> tuple[str, str, dict]:
        """Convert to ChromaDB format (id, document, metadata)."""
        return (
            self.id,
            self.text,
            self.metadata.to_dict(),
        )
