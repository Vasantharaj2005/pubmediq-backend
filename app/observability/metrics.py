from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SearchExecutionMetrics:
    session_id: str
    total_duration_ms: float
    retrieval_count: int
    quality_score: float
    refinement_count: int
    intent: str | None
    cached: bool = False

    def log(self) -> None:
        """Emits structured log for log-aggregation systems."""
        logger.info(
            "search_metrics",
            session_id=self.session_id,
            duration_ms=round(self.total_duration_ms, 2),
            retrieval_count=self.retrieval_count,
            quality_score=round(self.quality_score, 4),
            refinement_count=self.refinement_count,
            intent=self.intent,
            cached=self.cached,
        )


class MetricsTimer:
    """Context manager for measuring execution duration."""

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self.duration_ms = (self.end - self.start) * 1000
