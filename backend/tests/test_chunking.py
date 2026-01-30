"""Tests for chunking service."""

import pytest
from app.services.chunking.service import ChunkingService


class TestChunkingService:
    """Tests for document chunking."""

    @pytest.fixture
    def chunking_service(self):
        """Create a chunking service instance."""
        return ChunkingService(chunk_size=100, chunk_overlap=20)

    def test_service_initialization(self, chunking_service):
        """Service should initialize with correct settings."""
        assert chunking_service.chunk_size == 100
        assert chunking_service.chunk_overlap == 20

    def test_generate_chunk_id(self, chunking_service):
        """Chunk ID generation should be deterministic."""
        id1 = chunking_service._generate_chunk_id("doc1", "section1", 0)
        id2 = chunking_service._generate_chunk_id("doc1", "section1", 0)
        id3 = chunking_service._generate_chunk_id("doc1", "section1", 1)

        assert id1 == id2  # Same inputs = same ID
        assert id1 != id3  # Different chunk index = different ID
        assert id1.startswith("chunk_")

    def test_split_text_basic(self, chunking_service):
        """Text splitting should work for long text."""
        text = "This is a test sentence. " * 20  # ~500 chars
        chunks = chunking_service._split_text(text)
        assert len(chunks) >= 1
        # All chunks should be non-empty
        assert all(len(chunk.strip()) > 0 for chunk in chunks)

    def test_split_text_short(self, chunking_service):
        """Short text should not be split."""
        text = "Short text that fits in one chunk."
        chunks = chunking_service._split_text(text)
        assert len(chunks) == 1

    def test_split_text_empty(self, chunking_service):
        """Empty text should return minimal result."""
        chunks = chunking_service._split_text("")
        # Either empty list or list with empty string is acceptable
        assert len(chunks) <= 1

    def test_default_settings(self):
        """Default settings should be loaded from config."""
        service = ChunkingService()
        assert service.chunk_size > 0
        assert service.chunk_overlap >= 0
        assert service.chunk_overlap < service.chunk_size
