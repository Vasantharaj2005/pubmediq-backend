"""
PubMedIQ — Pinecone Vector Store Client

Manages semantic vector index operations for PubMed article embeddings.
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class PineconeMatch:
    """A single result from a Pinecone query."""

    def __init__(self, id: str, score: float, metadata: dict) -> None:
        self.id = id
        self.score = score
        self.metadata = metadata
        self.pmid = metadata.get("pmid", id)


class PineconeClient:
    """
    Async-compatible Pinecone client for article vector operations.

    Index structure:
      - Vector ID: PMID string
      - Dimension: 768 (S-PubMedBert)
      - Metric: cosine
      - Metadata: pmid, title, journal, year, mesh_terms, pub_types
    """

    def __init__(self) -> None:
        self._index = None
        self._available = False

    def connect(self) -> None:
        """Initialize Pinecone connection. Called during app lifespan."""
        api_key = settings.PINECONE_API_KEY
        if not api_key:
            logger.warning("pinecone_no_api_key", msg="Pinecone disabled — semantic search unavailable")
            return

        try:
            from pinecone import Pinecone

            pc = Pinecone(api_key=api_key)
            self._index = pc.Index(settings.PINECONE_INDEX_NAME)
            self._available = True
            logger.info("pinecone_connected", index=settings.PINECONE_INDEX_NAME)
        except Exception as e:
            logger.error("pinecone_connect_failed", error=str(e))
            self._available = False

    async def query(
        self,
        vector: list[float],
        top_k: int = 20,
        filter: dict | None = None,
        namespace: str | None = None,
    ) -> list[PineconeMatch]:
        """
        Semantic vector search.

        Args:
            vector: Query embedding (dim=768).
            top_k: Number of results to return.
            filter: Optional metadata filter (e.g., {"year": {"$gte": 2020}}).
            namespace: Pinecone namespace (default from settings).

        Returns:
            List of PineconeMatch objects sorted by score descending.
        """
        if not self._available or self._index is None:
            logger.warning("pinecone_unavailable_query", fallback="empty")
            return []

        ns = namespace or settings.PINECONE_NAMESPACE
        try:
            kwargs: dict[str, Any] = {
                "vector": vector,
                "top_k": top_k,
                "include_metadata": True,
                "namespace": ns,
            }
            if filter:
                kwargs["filter"] = filter

            response = self._index.query(**kwargs)
            matches = response.get("matches", [])
            return [
                PineconeMatch(
                    id=m["id"],
                    score=float(m.get("score", 0.0)),
                    metadata=m.get("metadata", {}),
                )
                for m in matches
            ]
        except Exception as e:
            logger.error("pinecone_query_failed", error=str(e))
            return []

    async def upsert(
        self,
        vectors: list[tuple[str, list[float], dict]],
        namespace: str | None = None,
        batch_size: int = 100,
    ) -> int:
        """
        Upsert article vectors into Pinecone.

        Args:
            vectors: List of (id, vector, metadata) tuples.
            namespace: Pinecone namespace.
            batch_size: Vectors per upsert batch.

        Returns:
            Number of vectors successfully upserted.
        """
        if not self._available or self._index is None:
            return 0

        ns = namespace or settings.PINECONE_NAMESPACE
        total = 0

        for i in range(0, len(vectors), batch_size):
            batch = vectors[i : i + batch_size]
            pinecone_vecs = [
                {"id": vid, "values": vec, "metadata": meta}
                for vid, vec, meta in batch
            ]
            try:
                self._index.upsert(vectors=pinecone_vecs, namespace=ns)
                total += len(batch)
                logger.debug("pinecone_upsert_batch", count=len(batch), total=total)
            except Exception as e:
                logger.error("pinecone_upsert_failed", batch_start=i, error=str(e))

        return total

    async def fetch(self, ids: list[str], namespace: str | None = None) -> dict:
        """Fetch specific vectors by ID."""
        if not self._available or self._index is None:
            return {}
        ns = namespace or settings.PINECONE_NAMESPACE
        try:
            return self._index.fetch(ids=ids, namespace=ns)
        except Exception as e:
            logger.error("pinecone_fetch_failed", error=str(e))
            return {}

    async def ping(self) -> bool:
        """Health check."""
        return self._available

    def create_index_if_not_exists(self) -> None:
        """Create the Pinecone index if it doesn't already exist."""
        if not settings.PINECONE_API_KEY:
            return
        try:
            from pinecone import Pinecone, ServerlessSpec

            pc = Pinecone(api_key=settings.PINECONE_API_KEY)
            existing = [idx.name for idx in pc.list_indexes()]

            if settings.PINECONE_INDEX_NAME not in existing:
                pc.create_index(
                    name=settings.PINECONE_INDEX_NAME,
                    dimension=settings.EMBEDDING_DIMENSION,
                    metric="cosine",
                    spec=ServerlessSpec(
                        cloud="aws",
                        region="us-east-1",
                    ),
                )
                logger.info("pinecone_index_created", name=settings.PINECONE_INDEX_NAME)
            else:
                logger.info("pinecone_index_exists", name=settings.PINECONE_INDEX_NAME)
        except Exception as e:
            logger.error("pinecone_create_index_failed", error=str(e))


# Module-level singleton — connected during app lifespan
pinecone_client = PineconeClient()
