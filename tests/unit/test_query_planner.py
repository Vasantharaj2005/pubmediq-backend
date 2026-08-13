import pytest

from app.agents.nodes.query_planner import _build_keyword_query, query_planner_node
from app.infrastructure.pubmed.esearch import PUB_TYPE_MAP
from app.domain.enums import StudyType


def test_build_keyword_query_with_facets():
    """Test that facets are ORed internally, and ANDed together."""
    facets = {
        "condition": ["Alzheimer's disease", "Alzheimer disease", "dementia"],
        "intervention": ["Memantine", "Donepezil"],
    }
    
    query = _build_keyword_query(facets, filters={})
    
    assert '("Alzheimer\'s disease" OR "Alzheimer disease" OR dementia)' in query
    assert ' AND ' in query
    assert '(Memantine OR Donepezil)' in query


def test_build_keyword_query_single_facet():
    """Test that a single facet does not include an AND."""
    facets = {
        "condition": ["Alzheimer's disease", "dementia"],
    }
    
    query = _build_keyword_query(facets, filters={})
    
    assert query == '("Alzheimer\'s disease" OR dementia)'
    assert ' AND ' not in query


@pytest.mark.asyncio
async def test_query_planner_node_state_update():
    """Test that the query planner updates the state correctly using facets."""
    state = {
        "query": "treatments for Alzheimer's disease",
        "facets": {
            "condition": ["Alzheimer's disease"],
            "intervention": ["treatment"]
        },
        "mesh_terms": ["Alzheimer Disease"],
        "filters": {}
    }
    
    result = await query_planner_node(state)
    
    assert result["keyword_query"] == '("Alzheimer\'s disease") AND (treatment)'
    assert result["mesh_query"] == '"Alzheimer Disease"[MeSH]'
    assert result["semantic_query"] == "treatments for Alzheimer's disease"
    assert result["search_strategy"]["facets"] == state["facets"]


def test_pub_type_map():
    """Test that Enum values map to correct PubMed Publication Types."""
    assert PUB_TYPE_MAP[StudyType.RANDOMIZED_CONTROLLED_TRIAL] == "Randomized Controlled Trial"
    assert PUB_TYPE_MAP[StudyType.CLINICAL_TRIAL] == "Clinical Trial"
    assert PUB_TYPE_MAP[StudyType.SYSTEMATIC_REVIEW] == "Systematic Review"
