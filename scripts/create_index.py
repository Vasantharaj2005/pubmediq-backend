"""
PubMedIQ — Create Pinecone Index

Creates the Pinecone vector index with correct configuration.

Usage:
    python scripts/create_index.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.vectorstore.pinecone_client import PineconeClient

logger = get_logger(__name__)


def main() -> None:
    configure_logging()

    if not settings.PINECONE_API_KEY:
        print("❌ PINECONE_API_KEY not set. Check your .env file.")
        sys.exit(1)

    print(f"Creating Pinecone index: {settings.PINECONE_INDEX_NAME}")
    print(f"  Dimension: {settings.EMBEDDING_DIMENSION}")
    print(f"  Metric: cosine")
    print(f"  Model: {settings.EMBEDDING_MODEL}")

    pc = PineconeClient()
    pc.create_index_if_not_exists()
    print(f"✅ Pinecone index '{settings.PINECONE_INDEX_NAME}' is ready.")


if __name__ == "__main__":
    main()
