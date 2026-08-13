"""
PubMedIQ — Core Configuration
Loads all settings from environment variables via pydantic-settings.
"""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Centralised application settings loaded from environment variables.
    All values can be overridden via .env file or shell environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "PubMedIQ"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production-must-be-at-least-32-chars!!"

    # ------------------------------------------------------------------
    # Server
    # ------------------------------------------------------------------
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    RELOAD: bool = True

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    CORS_ALLOW_CREDENTIALS: bool = True

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    # ------------------------------------------------------------------
    # PostgreSQL
    # ------------------------------------------------------------------
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "pubmediq"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/pubmediq"
    )

    # ------------------------------------------------------------------
    # Redis
    # ------------------------------------------------------------------
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_URL: str = "redis://localhost:6379/0"

    CACHE_TTL_SEARCH: int = 3600
    CACHE_TTL_ARTICLE: int = 86400
    CACHE_TTL_SESSION: int = 1800

    # ------------------------------------------------------------------
    # JWT Authentication
    # ------------------------------------------------------------------
    JWT_SECRET_KEY: str = "change-me-jwt-secret-must-be-at-least-32-chars!!!"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # LLM Providers
    # ------------------------------------------------------------------
    DEFAULT_LLM_PROVIDER: str = "groq"  # gemini | openai | groq | auto

    # Google Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"
    GEMINI_PRO_MODEL: str = "gemini-1.5-pro"

    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Groq (free tier)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    GROQ_FAST_MODEL: str = "llama-3.1-8b-instant"

    # ------------------------------------------------------------------
    # Embeddings — Local HuggingFace (free, open-source)
    # ------------------------------------------------------------------
    EMBEDDING_MODEL: str = "pritamdeka/S-PubMedBert-MS-MARCO"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DIMENSION: int = 768

    # ------------------------------------------------------------------
    # Reranker — Local Cross-Encoder (free, open-source)
    # ------------------------------------------------------------------
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_DEVICE: str = "cpu"
    RERANKER_TOP_K: int = 10

    # ------------------------------------------------------------------
    # Pinecone
    # ------------------------------------------------------------------
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    PINECONE_INDEX_NAME: str = "pubmediq-articles"
    PINECONE_NAMESPACE: str = "pubmed"

    # ------------------------------------------------------------------
    # NCBI PubMed API
    # ------------------------------------------------------------------
    NCBI_API_KEY: str = ""
    NCBI_EMAIL: str = "pubmediq@example.com"
    PUBMED_BASE_URL: str = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    PUBMED_RATE_LIMIT: int = 3  # 3/s without key, 10/s with key

    # ------------------------------------------------------------------
    # LangSmith
    # ------------------------------------------------------------------
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "pubmediq-hackathon"
    LANGCHAIN_ENDPOINT: str = "https://api.smith.langchain.com"

    # ------------------------------------------------------------------
    # Search Configuration
    # ------------------------------------------------------------------
    MAX_REFINEMENTS: int = 2
    QUALITY_THRESHOLD: float = 0.65
    DEFAULT_TOP_K: int = 20
    MAX_TOP_K: int = 100
    PUBMED_MAX_RESULTS: int = 100

    # ------------------------------------------------------------------
    # Rate Limiting
    # ------------------------------------------------------------------
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_SEARCH: int = 20

    # ------------------------------------------------------------------
    # Computed helpers
    # ------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def pubmed_rate_limit_effective(self) -> int:
        """Returns 10/s if API key present, else 3/s."""
        return 10 if self.NCBI_API_KEY else 3

    @property
    def langsmith_enabled(self) -> bool:
        return self.LANGCHAIN_TRACING_V2 and bool(self.LANGCHAIN_API_KEY)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()


# Convenience alias used across the application
settings = get_settings()
