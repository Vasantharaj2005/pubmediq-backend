import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.application.services.research_service import ResearchService
from app.schemas.research import AskRequest

@pytest.mark.asyncio
async def test_ask_question_no_session_found():
    """Test that ask() returns the correct error when the session is not found in history."""
    db_mock = AsyncMock()
    
    with patch("app.infrastructure.database.repositories.history_repository.HistoryRepository.get_by_id_for_user", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        
        service = ResearchService(db=db_mock)
        request = AskRequest(session_id="fake-session", question="What is the outcome?")
        
        response = await service.ask(request, user_id="user123")
        
        assert response.answer == "No search session found. Please run a search first."
        assert response.citations == []
        mock_get.assert_called_once_with("fake-session", "user123")

@pytest.mark.asyncio
async def test_ask_question_no_papers_found():
    """Test that ask() returns a specific error when the session is found but has no papers."""
    db_mock = AsyncMock()
    
    history_record = MagicMock()
    history_record.results = []
    
    with patch("app.infrastructure.database.repositories.history_repository.HistoryRepository.get_by_id_for_user", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = history_record
        
        service = ResearchService(db=db_mock)
        request = AskRequest(session_id="fake-session", question="What is the outcome?")
        
        response = await service.ask(request, user_id="user123")
        
        assert response.answer == "No papers found in this search session."
        assert response.citations == []

@pytest.mark.asyncio
async def test_ask_question_success():
    """Test that ask() calls the LLM with correctly formatted evidence when session has papers."""
    db_mock = AsyncMock()
    
    history_record = MagicMock()
    history_record.results = [
        {
            "pmid": "12345",
            "title": "Test Paper",
            "authors": "John Doe",
            "journal": "Test Journal",
            "year": "2024",
            "abstract": "This is a test abstract."
        }
    ]
    
    with patch("app.infrastructure.database.repositories.history_repository.HistoryRepository.get_by_id_for_user", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = history_record
        
        service = ResearchService(db=db_mock)
        
        # Mock LLM Client
        service._llm.invoke = AsyncMock(return_value="The outcome is positive. [PMID: 12345]")
        
        request = AskRequest(session_id="fake-session", question="What is the outcome?")
        
        response = await service.ask(request, user_id="user123")
        
        assert "The outcome is positive" in response.answer
        assert "12345" in response.citations
