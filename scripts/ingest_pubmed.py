"""
PubMedIQ — Ingestion Script

Fetches PubMed articles by query, generates embeddings, and indexes in Pinecone.

Usage:
    python scripts/ingest_pubmed.py --query "alzheimer biomarkers" --max 500
    python scripts/ingest_pubmed.py --query "depression exercise elderly" --max 200
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.pubmed.efetch import efetch
from app.infrastructure.pubmed.esearch import esearch
from app.infrastructure.vectorstore.embeddings import EmbeddingService
from app.infrastructure.vectorstore.indexer import ArticleIndexer
from app.infrastructure.vectorstore.pinecone_client import PineconeClient

logger = get_logger(__name__)


async def ingest(query: str, max_results: int = 500, batch_size: int = 50) -> None:
    """
    Full ingestion pipeline: PubMed → Embeddings → Pinecone.

    Args:
        query: PubMed search query.
        max_results: Maximum articles to ingest.
        batch_size: Articles per embedding/upsert batch.
    """
    configure_logging()
    logger.info("ingestion_start", query=query, max_results=max_results)

    # 1. Search PubMed for PMIDs
    logger.info("searching_pubmed", query=query)
    pmids = await esearch(query, retmax=max_results)
    logger.info("pubmed_search_complete", pmid_count=len(pmids))

    if not pmids:
        logger.warning("no_pmids_found")
        return

    # 2. Connect Pinecone
    pc = PineconeClient()
    pc.connect()

    # 3. Initialize indexer
    embedder = EmbeddingService()
    indexer = ArticleIndexer(embedding_service=embedder, pinecone_client=pc)

    # 4. Process in batches
    total_indexed = 0
    for i in range(0, len(pmids), batch_size):
        batch_pmids = pmids[i : i + batch_size]
        logger.info("fetching_batch", start=i, size=len(batch_pmids))

        articles = await efetch(batch_pmids)
        if not articles:
            continue

        indexed = await indexer.index_articles(articles)
        total_indexed += indexed
        logger.info("batch_indexed", indexed=indexed, total=total_indexed)

    logger.info("ingestion_complete", total_indexed=total_indexed)
    print(f"\n✅ Ingestion complete: {total_indexed}/{len(pmids)} articles indexed into Pinecone")


def main() -> None:
    parser = argparse.ArgumentParser(description="PubMedIQ Article Ingestion")
    parser.add_argument("--query", "-q", required=True, help="PubMed search query")
    parser.add_argument("--max", "-m", type=int, default=500, help="Maximum articles (default: 500)")
    parser.add_argument("--batch", "-b", type=int, default=50, help="Batch size (default: 50)")
    args = parser.parse_args()

    asyncio.run(ingest(query=args.query, max_results=args.max, batch_size=args.batch))


if __name__ == "__main__":
    main()
