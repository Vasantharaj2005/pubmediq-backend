"""
PubMedIQ — LLM Embeddings Adapter

LangChain-compatible embedding wrapper that delegates to our local
sentence-transformers EmbeddingService. Used where LangChain APIs
expect a LangChain Embeddings object.
"""
from __future__ import annotations

from langchain_core.embeddings import Embeddings

from app.infrastructure.vectorstore.embeddings import EmbeddingService, embedding_service


class LocalBiomedicalEmbeddings(Embeddings):
    """
    LangChain Embeddings implementation backed by the local
    S-PubMedBert model via sentence-transformers.
    """

    def __init__(self, service: EmbeddingService | None = None) -> None:
        self._service = service or embedding_service

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Synchronous embedding for LangChain compatibility."""
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self._service.embed_documents(texts)
            )
        finally:
            loop.close()

    def embed_query(self, text: str) -> list[float]:
        """Synchronous single query embedding for LangChain compatibility."""
        import asyncio

        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                self._service.embed_query(text)
            )
        finally:
            loop.close()

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._service.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return await self._service.embed_query(text)
