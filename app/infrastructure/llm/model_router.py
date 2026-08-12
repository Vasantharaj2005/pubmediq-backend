"""
PubMedIQ — LLM Model Router

Supports multiple free-tier LLM providers:
  - Groq       (free tier: llama3-8b, gemma2-9b, mixtral) ← default
  - Google Gemini (free tier: gemini-1.5-flash)
  - OpenAI     (gpt-4o-mini, cost-effective)

Selection strategy:
  1. Use DEFAULT_LLM_PROVIDER from settings
  2. Auto-fallback to next available provider if primary fails
  3. Raise LLMError only if all providers are exhausted

Usage:
    router = get_model_router()
    response = await router.ainvoke(messages, task="intent_extraction")
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage

from app.core.config import settings
from app.core.exceptions import LLMError, LLMRateLimitError
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMProvider(str, Enum):
    GROQ = "groq"
    GEMINI = "gemini"
    OPENAI = "openai"
    AUTO = "auto"


class ModelTask(str, Enum):
    """Task types used to select the right model tier."""
    FAST = "fast"           # intent extraction, concept mapping (small/fast model)
    REASONING = "reasoning" # answer generation, complex analysis (larger model)
    STRUCTURED = "structured"  # structured output extraction


# ---------------------------------------------------------------------------
# Provider factories
# ---------------------------------------------------------------------------

def _build_groq(task: ModelTask) -> BaseChatModel | None:
    """Build a Groq chat model (free tier, very fast)."""
    if not settings.GROQ_API_KEY:
        return None
    try:
        from langchain_groq import ChatGroq

        model_name = (
            settings.GROQ_FAST_MODEL if task == ModelTask.FAST
            else settings.GROQ_MODEL
        )
        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=model_name,
            temperature=0.1,
            max_tokens=2048,
        )
    except ImportError:
        logger.warning("groq_not_installed")
        return None
    except Exception as e:
        logger.warning("groq_init_failed", error=str(e))
        return None


def _build_gemini(task: ModelTask) -> BaseChatModel | None:
    """Build a Google Gemini chat model (free tier available)."""
    if not settings.GOOGLE_API_KEY:
        return None
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI

        model_name = (
            settings.GEMINI_MODEL if task in (ModelTask.FAST, ModelTask.STRUCTURED)
            else settings.GEMINI_PRO_MODEL
        )
        return ChatGoogleGenerativeAI(
            google_api_key=settings.GOOGLE_API_KEY,
            model=model_name,
            temperature=0.1,
            max_output_tokens=2048,
        )
    except ImportError:
        logger.warning("gemini_not_installed")
        return None
    except Exception as e:
        logger.warning("gemini_init_failed", error=str(e))
        return None


def _build_openai(task: ModelTask) -> BaseChatModel | None:
    """Build an OpenAI chat model (gpt-4o-mini is cost-effective)."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=0.1,
            max_tokens=2048,
        )
    except ImportError:
        logger.warning("openai_not_installed")
        return None
    except Exception as e:
        logger.warning("openai_init_failed", error=str(e))
        return None


# Provider priority order for AUTO mode
_PROVIDER_ORDER = [LLMProvider.GROQ, LLMProvider.GEMINI, LLMProvider.OPENAI]
_BUILDER_MAP = {
    LLMProvider.GROQ: _build_groq,
    LLMProvider.GEMINI: _build_gemini,
    LLMProvider.OPENAI: _build_openai,
}


class ModelRouter:
    """
    Intelligent LLM model router with fallback support.

    Architecture note:
    - LLM calls belong in agent nodes (query_understanding, answer_generator, etc.)
    - This router selects the right provider and handles fallback transparently
    - Endpoints NEVER call the LLM directly
    """

    def __init__(self) -> None:
        self._default_provider = LLMProvider(settings.DEFAULT_LLM_PROVIDER)

    def get_model(self, task: ModelTask = ModelTask.FAST) -> BaseChatModel:
        """
        Get a chat model for the given task.

        Args:
            task: The type of LLM task (FAST, REASONING, STRUCTURED).

        Returns:
            A LangChain chat model.

        Raises:
            LLMError: If no provider is available.
        """
        if self._default_provider == LLMProvider.AUTO:
            providers = _PROVIDER_ORDER
        else:
            # Try default first, then fallbacks
            others = [p for p in _PROVIDER_ORDER if p != self._default_provider]
            providers = [self._default_provider, *others]

        for provider in providers:
            builder = _BUILDER_MAP.get(provider)
            if builder is None:
                continue
            model = builder(task)
            if model is not None:
                logger.debug("llm_provider_selected", provider=provider, task=task)
                return model

        raise LLMError(
            detail="No LLM provider is available. Set GROQ_API_KEY, GOOGLE_API_KEY, or OPENAI_API_KEY."
        )

    def get_fast_model(self) -> BaseChatModel:
        """Small/fast model for intent extraction and concept mapping."""
        return self.get_model(ModelTask.FAST)

    def get_reasoning_model(self) -> BaseChatModel:
        """Larger model for answer generation and complex synthesis."""
        return self.get_model(ModelTask.REASONING)

    def get_structured_model(self) -> BaseChatModel:
        """Model configured for structured output extraction."""
        return self.get_model(ModelTask.STRUCTURED)

    async def ainvoke(
        self,
        messages: list[BaseMessage],
        task: ModelTask = ModelTask.FAST,
    ) -> str:
        """
        Invoke the LLM asynchronously with automatic provider fallback.

        Args:
            messages: LangChain message list.
            task: Task type for model selection.

        Returns:
            Model response content as a string.

        Raises:
            LLMError: If all providers fail.
        """
        if self._default_provider == LLMProvider.AUTO:
            providers = _PROVIDER_ORDER
        else:
            others = [p for p in _PROVIDER_ORDER if p != self._default_provider]
            providers = [self._default_provider, *others]

        last_error: Exception | None = None

        for provider in providers:
            builder = _BUILDER_MAP.get(provider)
            if builder is None:
                continue
            model = builder(task)
            if model is None:
                continue
            try:
                response = await model.ainvoke(messages)
                content = response.content
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", "") if isinstance(c, dict) else str(c)
                        for c in content
                    )
                logger.debug("llm_invoked", provider=provider, task=task)
                return str(content)
            except Exception as e:
                error_str = str(e).lower()
                if "rate" in error_str or "429" in error_str:
                    logger.warning("llm_rate_limited", provider=provider, fallback=True)
                else:
                    logger.warning("llm_invoke_failed", provider=provider, error=str(e))
                last_error = e
                continue

        raise LLMError(
            detail=f"All LLM providers failed. Last error: {last_error}"
        )


# Module-level singleton
_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    """Return the shared ModelRouter singleton."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
