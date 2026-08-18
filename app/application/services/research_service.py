"""
PubMedIQ — Research Service

Advanced research operations: summarize, compare, gap analysis, follow-up questions.
All operations use retrieved PubMed papers as evidence.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.cache.cache_service import CacheService
from app.infrastructure.llm.client import LLMClient
from app.infrastructure.llm.model_router import ModelTask
from app.infrastructure.pubmed.efetch import efetch
from app.schemas.research import (
    AskRequest,
    CompareRequest,
    GapAnalysisRequest,
    ResearchResponse,
    SummarizeRequest,
)

from app.observability.langsmith import trace

class ResearchService:
    ...
    @trace(name="research_summarize", tags=["research", "summarize"])
    async def summarize(self, request: SummarizeRequest) -> ResearchResponse:
        ...

    @trace(name="research_compare", tags=["research", "compare"])
    async def compare(self, request: CompareRequest) -> ResearchResponse:
        ...

    @trace(name="research_gap_analysis", tags=["research", "gap_analysis"])
    async def gap_analysis(self, request: GapAnalysisRequest) -> ResearchResponse:
        ...

logger = get_logger(__name__)

_SUMMARIZE_SYSTEM = """You are a systematic review expert. Summarize the provided PubMed papers
concisely, focusing on key findings, methodologies, and clinical significance.
Cite each paper with [PMID: number]. Be objective and evidence-based."""

_COMPARE_SYSTEM = """You are a biomedical researcher expert at comparing studies.
Compare the provided papers across key dimensions: study design, sample size,
interventions, outcomes, and quality of evidence.
Use a structured format. Cite each paper with [PMID: number]."""

_GAP_SYSTEM = """You are a research gap analyst. Review the provided papers and identify:
1. What questions remain unanswered
2. Methodological limitations in current evidence
3. Populations/settings understudied
4. Conflicting findings that need resolution
Cite papers with [PMID: number]."""

_ASK_SYSTEM = """You are a biomedical research assistant. Answer the follow-up question
using ONLY the papers provided as context. Cite each source with [PMID: number].
If the question cannot be answered from the provided papers, say so clearly."""


class ResearchService:
    """Advanced multi-paper research analysis service."""

    def __init__(self, db: AsyncSession, cache: CacheService | None = None) -> None:
        self._db = db
        self._cache = cache
        self._llm = LLMClient()

    async def _fetch_papers(self, pmids: list[str]) -> list[dict]:
        """Fetch and format papers for LLM context."""
        articles = await efetch(pmids)
        return [
            {
                "pmid": a.pmid,
                "title": a.title,
                "abstract": a.abstract,
                "authors": a.author_string,
                "journal": a.journal,
                "year": a.year,
                "pub_types": a.pub_types,
            }
            for a in articles
        ]

    def _format_evidence(self, papers: list[dict]) -> str:
        """Format papers as numbered evidence for LLM context."""
        parts = []
        for i, p in enumerate(papers, 1):
            parts.append(
                f"[{i}] PMID: {p['pmid']}\n"
                f"Title: {p.get('title', 'N/A')}\n"
                f"Authors: {p.get('authors', 'N/A')}\n"
                f"Journal: {p.get('journal', 'N/A')} ({p.get('year', 'N/A')})\n"
                f"Abstract: {(p.get('abstract', '') or '')[:600]}"
            )
        return "\n\n---\n\n".join(parts)

    async def summarize(self, request: SummarizeRequest) -> ResearchResponse:
        """Summarize multiple PubMed articles."""
        papers = await self._fetch_papers(request.pmids)
        evidence = self._format_evidence(papers)
        focus = f" Focus on: {request.focus}." if request.focus else ""

        answer = await self._llm.invoke(
            system=_SUMMARIZE_SYSTEM,
            human=f"Summarize these papers.{focus}\n\nPapers:\n{evidence}",
            task=ModelTask.REASONING,
        )
        import re
        citations = list(dict.fromkeys(re.findall(r"\[PMID:\s*(\d+)\]", answer)))
        return ResearchResponse(answer=answer, citations=citations, pmids_used=request.pmids)

    async def compare(self, request: CompareRequest) -> ResearchResponse:
        """Compare multiple PubMed articles."""
        papers = await self._fetch_papers(request.pmids)
        evidence = self._format_evidence(papers)
        aspect = f" Specifically compare: {request.aspect}." if request.aspect else ""

        answer = await self._llm.invoke(
            system=_COMPARE_SYSTEM,
            human=f"Compare these papers.{aspect}\n\nPapers:\n{evidence}",
            task=ModelTask.REASONING,
        )
        import re
        citations = list(dict.fromkeys(re.findall(r"\[PMID:\s*(\d+)\]", answer)))
        return ResearchResponse(answer=answer, citations=citations, pmids_used=request.pmids)

    async def gap_analysis(self, request: GapAnalysisRequest) -> ResearchResponse:
        """Identify research gaps across a set of papers."""
        papers = await self._fetch_papers(request.pmids)
        evidence = self._format_evidence(papers)

        answer = await self._llm.invoke(
            system=_GAP_SYSTEM,
            human=f"Identify research gaps in these papers.\n\nPapers:\n{evidence}",
            task=ModelTask.REASONING,
        )
        import re
        citations = list(dict.fromkeys(re.findall(r"\[PMID:\s*(\d+)\]", answer)))
        return ResearchResponse(answer=answer, citations=citations, pmids_used=request.pmids)

    async def ask(self, request: AskRequest, cache: CacheService | None = None) -> ResearchResponse:
        """Answer a follow-up question using session context."""
        # Retrieve session state
        session_state = {}
        if cache:
            session_state = await cache.get_cached_session(request.session_id) or {}

        papers = session_state.get("results", [])[:10]
        if not papers:
            return ResearchResponse(
                answer="No search session found. Please run a search first.",
                citations=[],
            )

        evidence = self._format_evidence(papers)
        answer = await self._llm.invoke(
            system=_ASK_SYSTEM,
            human=f"Question: {request.question}\n\nContext papers:\n{evidence}",
            task=ModelTask.FAST,
        )
        import re
        citations = list(dict.fromkeys(re.findall(r"\[PMID:\s*(\d+)\]", answer)))
        return ResearchResponse(answer=answer, citations=citations)
