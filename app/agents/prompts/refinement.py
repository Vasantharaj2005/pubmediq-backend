"""
PubMedIQ — Prompt: Query Refinement

Refines a search query when the quality gate rejects initial results.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a PubMed search expert who knows how to reformulate biomedical search queries
to find more relevant literature.

When the initial search returns poor-quality results or 0 results, you will:
1. Identify why the query might have been too restrictive (e.g., too many ANDs, overly specific terms)
2. Broaden the search by dropping less critical constraints and using OR for related concepts instead of AND
3. Suggest a refined PubMed query using proper MeSH syntax and Boolean operators
4. Focus on the core clinical condition or intervention

PubMed query syntax tips:
- Use [MeSH] tag for controlled vocabulary (not [MeSH Terms])
- Use [Title/Abstract] or [TIAB] for free-text search
- Use AND to combine different facets (Condition AND Intervention)
- Use OR to combine synonyms within a facet (Term1 OR Term2)
- If results are zero, remove ANDs!
- Use quotation marks for multi-word phrases

Respond with ONLY a JSON object. No explanation."""

HUMAN_TEMPLATE = """The initial search for the following query returned poor-quality results.
Please suggest a refined PubMed query.

Original query: {original_query}

Research intent:
{intent}

Current search that underperformed:
{current_query}

Quality score: {quality_score:.2f} (threshold: {threshold:.2f})
Refinement attempt: {refinement_count} of {max_refinements}

Respond with:
{{
  "refined_query": "improved PubMed query string",
  "reasoning": "why this refinement should improve results"
}}"""


def build_refinement_prompt(
    original_query: str,
    intent: dict,
    current_query: str,
    quality_score: float,
    refinement_count: int,
    threshold: float,
    max_refinements: int,
) -> tuple[str, str]:
    """Return (system, human) prompt tuple for query refinement."""
    import json
    return SYSTEM_PROMPT, HUMAN_TEMPLATE.format(
        original_query=original_query,
        intent=json.dumps(intent, indent=2),
        current_query=current_query,
        quality_score=quality_score,
        threshold=threshold,
        refinement_count=refinement_count,
        max_refinements=max_refinements,
    )
