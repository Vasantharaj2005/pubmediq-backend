"""
PubMedIQ — Local Biomedical Embedding Service

Uses pritamdeka/S-PubMedBert-MS-MARCO via sentence-transformers.
This is a free, open-source biomedical-specific model.

Biomedical advantage over general-purpose models:
  - Trained on PubMed + MARCO retrieval data
  - Understands medical terminology, drug names, disease concepts
  - Better semantic alignment for "exercise" ↔ "physical activity"

Model dimensions: 768 (BERT-base)
"""
from __future__ import annotations

import asyncio
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """
    Local embedding service using sentence-transformers.

    Model: pritamdeka/S-PubMedBert-MS-MARCO
    Device: CPU (configurable via EMBEDDING_DEVICE setting)
    """

    def __init__(self) -> None:
        self._model = None
        self._model_name = settings.EMBEDDING_MODEL
        self._device = settings.EMBEDDING_DEVICE
        self._batch_size = settings.EMBEDDING_BATCH_SIZE

    def _load_model(self):
        """Lazy-load the model on first use (avoids startup delay)."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                logger.info(
                    "embedding_model_loading",
                    model=self._model_name,
                    device=self._device,
                )
                self._model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                )
                logger.info("embedding_model_loaded", model=self._model_name)
            except Exception as e:
                logger.error("embedding_model_load_failed", error=str(e))
                raise RuntimeError(f"Failed to load embedding model: {e}") from e
        return self._model

    async def embed_query(self, text: str) -> list[float]:
        """
        Embed a single query string.

        Runs in a thread pool to avoid blocking the async event loop.

        Args:
            text: The query or document text.

        Returns:
            Embedding vector as a list of floats (dim=768).
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._embed_sync, [text], True)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple documents in batches.

        Args:
            texts: List of strings to embed.

        Returns:
            List of embedding vectors.
        """
        if not texts:
            return []
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._embed_sync_batch, texts)
        return result

    def _embed_sync(self, texts: list[str], normalize: bool = True) -> list[float]:
        """Synchronous embedding for a single query (run in executor)."""
        model = self._load_model()
        embedding = model.encode(
            texts,
            normalize_embeddings=normalize,
            batch_size=self._batch_size,
            show_progress_bar=False,
        )
        return embedding[0].tolist()

    def _embed_sync_batch(self, texts: list[str]) -> list[list[float]]:
        """Synchronous batch embedding (run in executor)."""
        model = self._load_model()
        embeddings = model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=self._batch_size,
            show_progress_bar=len(texts) > 50,
        )
        return [e.tolist() for e in embeddings]

    @property
    def dimension(self) -> int:
        return settings.EMBEDDING_DIMENSION


# Module-level singleton
embedding_service = EmbeddingService()
