#!/usr/bin/env python3
"""
Quick Re-indexing Script

Re-indexes existing parsed filings with new embeddings/chunk settings.
Faster than full ingestion since it skips SEC API calls.

Usage:
    python scripts/reindex.py [--clear]
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.services.chunking.service import ChunkingService
from app.services.retrieval.service import RetrievalService
from app.services.edgar.models import ParsedFiling

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def reindex_all() -> None:
    """Re-index all parsed filings with current settings."""

    parsed_dir = settings.parsed_dir
    if not parsed_dir.exists():
        logger.error(f"Parsed directory not found: {parsed_dir}")
        return

    # Initialize services
    chunking_service = ChunkingService()
    retrieval_service = RetrievalService()

    # Find all parsed filings
    all_filings = list(parsed_dir.glob("**/*.json"))
    logger.info(f"Found {len(all_filings)} parsed filings to re-index")

    total_chunks = 0
    processed = 0
    errors = 0

    for filing_path in all_filings:
        try:
            # Load parsed filing
            data = json.loads(filing_path.read_text(encoding="utf-8"))
            parsed = ParsedFiling.from_dict(data)

            # Chunk with new settings
            chunks = chunking_service.chunk_filing(parsed)

            # Index into vector store
            if chunks:
                count = await retrieval_service.index_chunks(chunks)
                total_chunks += count

            processed += 1
            ticker = parsed.metadata.ticker
            filing_type = parsed.metadata.filing_type.value

            if processed % 10 == 0:
                logger.info(f"Progress: {processed}/{len(all_filings)} filings, {total_chunks} chunks")

        except Exception as e:
            errors += 1
            logger.error(f"Error processing {filing_path}: {e}")

    logger.info("=" * 60)
    logger.info("RE-INDEXING COMPLETE")
    logger.info(f"  Filings processed: {processed}")
    logger.info(f"  Total chunks indexed: {total_chunks}")
    logger.info(f"  Errors: {errors}")


async def clear_index() -> None:
    """Clear the existing vector store."""
    import shutil

    chroma_dir = settings.chroma_dir
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
        logger.info(f"Cleared vector store at {chroma_dir}")

    chroma_dir.mkdir(parents=True, exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Re-index parsed filings")
    parser.add_argument(
        "--clear", action="store_true",
        help="Clear existing index before re-indexing"
    )

    args = parser.parse_args()

    if args.clear:
        logger.info("Clearing existing index...")
        asyncio.run(clear_index())

    logger.info("Starting re-indexing with new settings...")
    logger.info(f"  Chunk size: {settings.chunk_size}")
    logger.info(f"  Chunk overlap: {settings.chunk_overlap}")

    asyncio.run(reindex_all())


if __name__ == "__main__":
    main()
