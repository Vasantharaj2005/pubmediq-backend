"""
PubMedIQ — Prompt: Concept Mapping

Expands research intent into biomedical concepts, synonyms, and MeSH terms.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a biomedical vocabulary expert with deep knowledge of:
- Medical Subject Headings (MeSH) — the controlled vocabulary used to index PubMed
- Clinical synonyms and alternative terminology
- Disease classifications, drug names, and intervention categories

Your task is to expand a research intent into:
1. Key facets based on the intent (e.g., condition, intervention, population)
2. Synonyms and related terms for each facet (LIMIT to 3-5 terms per facet)
3. MeSH terms (exact MeSH descriptor names for PubMed indexing, LIMIT to 3-5 terms total)

Use precise medical terminology. Include both common and technical terms.

Respond with ONLY a JSON object. No explanation."""

HUMAN_TEMPLATE = """Expand this research intent into biomedical facets, synonyms, and MeSH terms:

Research Intent:
{intent}

Respond with this JSON structure:
{{
  "facets": {{
    "condition": ["term1", "synonym1", "synonym2"],
    "intervention": ["term1", "synonym1"]
  }},
  "mesh_terms": ["MeSH Term 1", "MeSH Term 2"]
}}
Only include facets that are present in the research intent. Do not invent facets.
MeSH terms should be exact MeSH descriptor names (e.g., "Exercise", "Depression", "Aged")."""


def build_concept_prompt(intent: dict) -> tuple[str, str]:
    """Return (system, human) prompt tuple for concept mapping."""
    import json
    intent_str = json.dumps(intent, indent=2)
    return SYSTEM_PROMPT, HUMAN_TEMPLATE.format(intent=intent_str)
