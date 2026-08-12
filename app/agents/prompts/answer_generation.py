"""
PubMedIQ — Prompt: Answer Generation

Synthesizes an evidence-grounded answer from retrieved PubMed papers.
Requires PMID citations for every factual claim.
"""
from __future__ import annotations

SYSTEM_PROMPT = """You are a biomedical research assistant providing evidence-based answers.

CRITICAL RULES:
1. Use ONLY the evidence provided — do NOT use external knowledge or invent facts
2. Cite the PMID for every factual claim using the format [PMID: 12345678]
3. Clearly state when evidence is limited or conflicting
4. Distinguish between study types (RCT, observational, review)
5. Mention sample sizes and effect sizes when available
6. Do NOT make clinical recommendations — present findings only
7. If no relevant evidence is found in the provided papers, say so clearly

Structure your answer:
- Start with a direct answer to the research question (2-3 sentences)
- Summarize key findings with citations
- Note limitations in the evidence
- End with a conclusion

Your response should be scientifically accurate and appropriately cautious."""

HUMAN_TEMPLATE = """Answer the following research question using ONLY the evidence below.

Research Question: {query}

Evidence Papers:
{evidence}

Instructions:
- Cite each paper you reference as [PMID: <number>]
- If papers conflict, note the disagreement
- Be specific about populations, interventions, and outcomes
- Mention study quality when relevant"""


def build_answer_prompt(query: str, papers: list[dict]) -> tuple[str, str]:
    """
    Return (system, human) prompt tuple for answer generation.

    Args:
        query: Original research question.
        papers: List of paper dicts with pmid, title, abstract, authors, year, journal.
    """
    evidence_parts = []
    for i, paper in enumerate(papers[:10], 1):  # max 10 papers
        pmid = paper.get("pmid", "unknown")
        title = paper.get("title", "No title")
        abstract = (paper.get("abstract", "") or "")[:800]  # truncate
        year = paper.get("year", "")
        journal = paper.get("journal", "")
        pub_types = ", ".join(paper.get("pub_types", [])[:2])

        evidence_parts.append(
            f"[{i}] PMID: {pmid}\n"
            f"Title: {title}\n"
            f"Journal: {journal} ({year})\n"
            f"Study type: {pub_types or 'Not specified'}\n"
            f"Abstract: {abstract}\n"
        )

    evidence = "\n---\n".join(evidence_parts) if evidence_parts else "No papers available."
    return SYSTEM_PROMPT, HUMAN_TEMPLATE.format(query=query, evidence=evidence)
