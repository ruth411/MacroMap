#!/usr/bin/env python3
"""
Reset the ChromaDB vector store.

Use this script when:
- Embedding dimensions have changed (e.g., 1536 -> 3072)
- You want to clear all indexed documents
- The vector store is corrupted

After running this, you'll need to re-index your documents.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


def reset_vector_store():
    """Delete and recreate the ChromaDB collection."""
    print(f"ChromaDB directory: {settings.chroma_dir}")
    print(f"Collection name: {settings.chroma_collection_name}")

    # Initialize client
    client = chromadb.PersistentClient(
        path=str(settings.chroma_dir),
        settings=ChromaSettings(anonymized_telemetry=False),
    )

    # Try to get existing collection
    try:
        collection = client.get_collection(settings.chroma_collection_name)
        old_count = collection.count()
        print(f"Found existing collection with {old_count} documents")

        # Delete it
        client.delete_collection(settings.chroma_collection_name)
        print(f"Deleted collection: {settings.chroma_collection_name}")
    except Exception as e:
        print(f"No existing collection found or error: {e}")
        old_count = 0

    # Create fresh collection with correct settings
    collection = client.create_collection(
        name=settings.chroma_collection_name,
        metadata={"hnsw:space": "cosine"},
    )
    print(f"Created new collection: {settings.chroma_collection_name}")
    print(f"\nVector store reset complete!")
    print(f"Documents deleted: {old_count}")
    print(f"\nNext steps:")
    print(f"  1. Start the backend server")
    print(f"  2. Re-index your documents via POST /api/v1/retrieval/index-all")


if __name__ == "__main__":
    reset_vector_store()
