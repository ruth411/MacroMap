"""Section-aware document chunking service for RAG."""

import hashlib
import logging
from typing import TYPE_CHECKING, Optional

from app.core.config import settings
from .models import Chunk, ChunkMetadata

if TYPE_CHECKING:
    from app.services.edgar.models import ParsedFiling, Section

logger = logging.getLogger(__name__)


class ChunkingService:
    """
    Section-aware document chunking for RAG.

    Features:
    - Respects section boundaries (won't split across items)
    - Configurable chunk size and overlap
    - Preserves metadata for each chunk
    - Generates unique chunk IDs
    """

    def __init__(
        self,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ):
        self.chunk_size = chunk_size or settings.chunk_size  # 1000
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap  # 200

    def chunk_filing(self, parsed_filing: "ParsedFiling") -> list[Chunk]:
        """
        Chunk a parsed filing into RAG-ready chunks.

        Args:
            parsed_filing: Parsed filing with sections

        Returns:
            List of Chunk objects with metadata
        """
        all_chunks: list[Chunk] = []

        for item_number, section in parsed_filing.sections.items():
            section_chunks = self.chunk_section(
                section=section,
                metadata=parsed_filing.metadata,
            )
            all_chunks.extend(section_chunks)

        logger.info(
            f"Created {len(all_chunks)} chunks from "
            f"{len(parsed_filing.sections)} sections"
        )
        return all_chunks

    def chunk_section(
        self,
        section: "Section",
        metadata,  # FilingMetadata
    ) -> list[Chunk]:
        """
        Chunk a single section.

        Args:
            section: Section to chunk
            metadata: Filing metadata

        Returns:
            List of Chunk objects
        """
        text = section.content
        if not text or len(text) < 50:
            return []

        # Split text into chunks
        text_chunks = self._split_text(text)

        chunks: list[Chunk] = []
        total_chunks = len(text_chunks)

        for i, chunk_text in enumerate(text_chunks):
            chunk_metadata = ChunkMetadata(
                ticker=metadata.ticker,
                company_name=metadata.company_name,
                filing_type=metadata.filing_type.value,
                filing_date=metadata.filing_date.isoformat(),
                accession_number=metadata.accession_number,
                section_item=section.item_number,
                section_title=section.title,
                chunk_index=i,
                total_chunks=total_chunks,
            )

            chunk_id = self._generate_chunk_id(
                metadata.accession_number,
                section.item_number,
                i
            )

            chunks.append(Chunk(
                id=chunk_id,
                text=chunk_text,
                metadata=chunk_metadata,
            ))

        return chunks

    def _split_text(self, text: str) -> list[str]:
        """
        Split text into chunks with overlap.

        Uses sentence-aware splitting when possible.
        """
        if len(text) <= self.chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0

        while start < len(text):
            # Determine end position
            end = start + self.chunk_size

            if end >= len(text):
                # Last chunk
                chunks.append(text[start:].strip())
                break

            # Try to find a sentence boundary near the end
            chunk_text = text[start:end]
            boundary = self._find_sentence_boundary(chunk_text)

            if boundary > self.chunk_size // 2:
                # Found a good boundary
                end = start + boundary
            else:
                # Fall back to word boundary
                word_boundary = self._find_word_boundary(chunk_text)
                if word_boundary > self.chunk_size // 2:
                    end = start + word_boundary

            chunks.append(text[start:end].strip())

            # Move start position with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = end

        return [c for c in chunks if c]  # Remove empty chunks

    def _find_sentence_boundary(self, text: str) -> int:
        """Find the last sentence boundary in text."""
        # Look for sentence endings (. ! ?) followed by space or end
        boundaries = []
        for i, char in enumerate(text):
            if char in ".!?" and i < len(text) - 1:
                next_char = text[i + 1] if i + 1 < len(text) else ""
                if next_char in " \n\t" or next_char == "":
                    boundaries.append(i + 1)

        return boundaries[-1] if boundaries else 0

    def _find_word_boundary(self, text: str) -> int:
        """Find the last word boundary in text."""
        # Find last space
        last_space = text.rfind(" ")
        return last_space if last_space > 0 else len(text)

    def _generate_chunk_id(
        self,
        accession_number: str,
        section_item: str,
        chunk_index: int
    ) -> str:
        """Generate a unique chunk ID."""
        # Create a deterministic ID based on content identifiers
        id_string = f"{accession_number}_{section_item}_{chunk_index}"
        hash_suffix = hashlib.md5(id_string.encode()).hexdigest()[:8]
        return f"chunk_{accession_number.replace('-', '')}_{section_item}_{chunk_index}_{hash_suffix}"


# Singleton instance
_chunking_service: Optional[ChunkingService] = None


def get_chunking_service() -> ChunkingService:
    """Get singleton ChunkingService instance."""
    global _chunking_service
    if _chunking_service is None:
        _chunking_service = ChunkingService()
    return _chunking_service
