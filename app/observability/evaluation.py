from __future__ import annotations

from typing import Any
from app.core.config import settings
from app.core.logging import get_logger
from app.observability.langsmith import get_langsmith_client

logger = get_logger(__name__)


def create_or_get_evaluation_dataset(dataset_name: str = "pubmediq-golden-dataset"):
    """Fetch or create a LangSmith dataset for offline evaluation."""
    client = get_langsmith_client()
    if not client:
        logger.warning("langsmith_not_available")
        return None

    if client.has_dataset(dataset_name=dataset_name):
        return client.read_dataset(dataset_name=dataset_name)

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description="Golden Q&A dataset for biomedical queries and PubMed citation grounding",
    )
    return dataset


async def evaluate_citation_groundedness(
    run_output: dict[str, Any],
    example: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Evaluator: Assesses whether every citation PMID in the answer 
    actually exists in the retrieved documents list.
    """
    answer = run_output.get("ai_summary", "")
    citations = run_output.get("citations", [])
    results = run_output.get("results", [])

    retrieved_pmids = {str(r.get("pmid")) for r in results if r.get("pmid")}
    valid_citations = [c for c in citations if str(c.get("pmid")) in retrieved_pmids]

    score = len(valid_citations) / len(citations) if citations else 1.0
    return {
        "key": "citation_groundedness",
        "score": score,
        "comment": f"{len(valid_citations)} of {len(citations)} citations are verified in retrieved papers.",
    }
