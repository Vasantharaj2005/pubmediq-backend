"""
PubMedIQ — PubMed Base HTTP Client

Wraps httpx.AsyncClient with:
  - Configurable rate limiting (3 req/s without key, 10 req/s with NCBI key)
  - Exponential backoff retry on transient errors
  - NCBI API key injection
  - Shared session management
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.pubmed.exceptions import PubMedAPIError, PubMedRateLimitError

logger = get_logger(__name__)

# NCBI E-Utils base URL
_BASE_URL = settings.PUBMED_BASE_URL


class PubMedClient:
    """
    Async HTTP client for NCBI E-Utils API.

    Rate limiting:
      - Without API key: 3 requests/second
      - With API key: 10 requests/second

    Usage:
        client = PubMedClient()
        async with client:
            pmids = await client.get("/esearch.fcgi", params={...})
    """

    def __init__(self) -> None:
        self._api_key = settings.NCBI_API_KEY
        self._email = settings.NCBI_EMAIL
        self._rate = settings.pubmed_rate_limit_effective
        self._semaphore = asyncio.Semaphore(self._rate)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "PubMedClient":
        self._client = httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=httpx.Timeout(30.0, connect=10.0),
            headers={"User-Agent": f"PubMedIQ/0.1 ({self._email})"},
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    def _build_params(self, params: dict) -> dict:
        """Inject NCBI credentials into every request."""
        base = {"tool": "pubmediq", "email": self._email}
        if self._api_key:
            base["api_key"] = self._api_key
        base.update(params)
        return base

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError, PubMedRateLimitError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def get(self, endpoint: str, params: dict) -> dict:
        """
        Perform a rate-limited GET request to the E-Utils API.

        Args:
            endpoint: E.g. "/esearch.fcgi"
            params: Query parameters (without api_key/tool/email).

        Returns:
            Parsed JSON response as a dict.

        Raises:
            PubMedRateLimitError: On HTTP 429.
            PubMedAPIError: On other HTTP errors.
        """
        if self._client is None:
            raise RuntimeError("PubMedClient must be used as async context manager.")

        full_params = self._build_params(params)

        async with self._semaphore:
            try:
                response = await self._client.get(endpoint, params=full_params)
            except httpx.TimeoutException as e:
                logger.warning("pubmed_timeout", endpoint=endpoint)
                raise PubMedAPIError(detail=f"PubMed request timed out: {e}") from e
            except httpx.HTTPError as e:
                logger.error("pubmed_http_error", endpoint=endpoint, error=str(e))
                raise

        if response.status_code == 429:
            logger.warning("pubmed_rate_limited")
            raise PubMedRateLimitError()

        if response.status_code != 200:
            logger.error(
                "pubmed_error_response",
                status=response.status_code,
                endpoint=endpoint,
            )
            raise PubMedAPIError(
                detail=f"PubMed API returned HTTP {response.status_code}."
            )

        try:
            return response.json()
        except Exception as e:
            # Return raw text for XML responses (efetch)
            return {"_raw": response.text}

    async def get_raw(self, endpoint: str, params: dict) -> str:
        """Return raw response text (for XML efetch responses)."""
        if self._client is None:
            raise RuntimeError("PubMedClient must be used as async context manager.")

        full_params = self._build_params(params)
        async with self._semaphore:
            try:
                response = await self._client.get(endpoint, params=full_params)
            except httpx.HTTPError as e:
                raise PubMedAPIError(detail=str(e)) from e

        if response.status_code == 429:
            raise PubMedRateLimitError()
        if response.status_code != 200:
            raise PubMedAPIError(detail=f"HTTP {response.status_code}")

        return response.text


# Module-level singleton for dependency injection
_shared_client: PubMedClient | None = None


def get_pubmed_client() -> PubMedClient:
    """Return a new PubMedClient instance (use as async context manager)."""
    return PubMedClient()
