"""
PubMedIQ — Article Indexer

Combines embedding generation + Pinecone upsert into a single pipeline.
Used by ingestion scripts and the ingestion worker.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.pubmed.models import PubMedArticle
from app.infrastructure.vectorstore.embeddings import EmbeddingService
from app.infrastructure.vectorstore.pinecone_client import PineconeClient

logger = get_logger(__name__)


class ArticleIndexer:
    """
    Pipeline: PubMedArticle → Embedding → Pinecone upsert.

    Usage:
        indexer = ArticleIndexer(embedding_service, pinecone_client)
        count = await indexer.index_articles(articles)
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        pinecone_client: PineconeClient,
    ) -> None:
        self._embedder = embedding_service
        self._pinecone = pinecone_client

    async def index_articles(self, articles: list[PubMedArticle]) -> int:
        """
        Embed and index a list of PubMed articles into Pinecone.

        Args:
            articles: List of PubMedArticle objects to index.

        Returns:
            Number of articles successfully indexed.
        """
        if not articles:
            return 0

        logger.info("indexer_start", article_count=len(articles))

        # Filter articles with at least title or abstract
        valid = [a for a in articles if a.title or a.abstract]
        if len(valid) < len(articles):
            logger.warning(
                "indexer_skipping_empty",
                skipped=len(articles) - len(valid),
            )

        # Generate embeddings
        texts = [a.full_text_for_embedding for a in valid]
        try:
            embeddings = await self._embedder.embed_documents(texts)
        except Exception as e:
            logger.error("indexer_embed_failed", error=str(e))
            return 0

        # Build Pinecone vectors
        vectors = []
        for article, embedding in zip(valid, embeddings):
            metadata = {
                "pmid": article.pmid,
                "title": (article.title or "")[:500],   # Pinecone metadata limit
                "journal": (article.journal or "")[:200],
                "year": article.year or 0,
                "mesh_terms": article.mesh_terms[:10],  # limit list size
                "pub_types": article.pub_types[:5],
                "has_abstract": bool(article.abstract),
                "author": article.author_string[:200],
                "doi": article.doi or "",
            }
            vectors.append((article.pmid, embedding, metadata))

        # Upsert to Pinecone
        upserted = await self._pinecone.upsert(vectors)
        logger.info("indexer_complete", indexed=upserted)
        return upserted
