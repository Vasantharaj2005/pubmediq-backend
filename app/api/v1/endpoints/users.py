"""
PubMedIQ — History, Feedback, User Endpoints
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_optional_user, require_active_user
from app.application.services.feedback_service import FeedbackService
from app.application.services.history_service import HistoryService
from app.infrastructure.database.connection import get_db
from app.infrastructure.database.models.user import UserModel
from app.schemas.feedback import FeedbackRequest, FeedbackResponse
from app.schemas.user import UpdateUserRequest, UserProfile

# -------------------------------------------------------------------
# History router
# -------------------------------------------------------------------
history_router = APIRouter(prefix="/history", tags=["History"])


@history_router.get("", summary="Get search history")
async def get_history(
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return the authenticated user's search history (newest first).

    Each record includes:
    - Metadata (query, quality, timestamps)
    - Full paper results array (same structure as /search response)
    - AI-generated summary and citation list
    """
    service = HistoryService(db)
    records = await service.get_history(str(current_user.id), limit=limit)
    return [
        {
            "id": str(r.id),
            "query": r.query,
            "intent": r.intent,
            "search_strategy": r.search_strategy,
            "results_count": r.results_count,
            "quality_score": r.quality_score,
            "refined": r.refined,
            "refinement_count": r.refinement_count,
            "results": r.results or [],          # full paper list (None for old rows)
            "ai_summary": r.ai_summary,
            "citations": r.citations or [],
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@history_router.get("/{record_id}", summary="Get full detail of a single history record")
async def get_history_detail(
    record_id: str,
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return the full detail of a single past search including all papers and AI summary."""
    from fastapi import HTTPException, status
    from app.core.exceptions import HistoryNotFoundError, PermissionDeniedError
    service = HistoryService(db)
    try:
        r = await service.get_by_id(str(current_user.id), record_id)
    except HistoryNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="History record not found.")
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="You do not have access to this record.")
    return {
        "id": str(r.id),
        "query": r.query,
        "intent": r.intent,
        "search_strategy": r.search_strategy,
        "results_count": r.results_count,
        "quality_score": r.quality_score,
        "refined": r.refined,
        "refinement_count": r.refinement_count,
        "results": r.results or [],
        "ai_summary": r.ai_summary,
        "citations": r.citations or [],
        "created_at": r.created_at.isoformat(),
    }


@history_router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
async def delete_history(
    record_id: str,
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a specific history record (must belong to current user)."""
    service = HistoryService(db)
    await service.delete(str(current_user.id), record_id)


# -------------------------------------------------------------------
# Feedback router
# -------------------------------------------------------------------
feedback_router = APIRouter(prefix="/feedback", tags=["Feedback"])


@feedback_router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: UserModel | None = Depends(get_optional_user),
) -> FeedbackResponse:
    """Submit a rating and optional comment for a search session."""
    user_id = str(current_user.id) if current_user else None
    service = FeedbackService(db)
    return await service.submit(request, user_id=user_id)


# -------------------------------------------------------------------
# Users router
# -------------------------------------------------------------------
users_router = APIRouter(prefix="/users", tags=["Users"])


@users_router.get("/me", response_model=UserProfile, summary="Get current user profile")
async def get_profile(
    current_user: UserModel = Depends(require_active_user),
) -> UserProfile:
    """Return the full user profile for the authenticated user."""
    return UserProfile.model_validate(current_user)


@users_router.patch("/me", response_model=UserProfile, summary="Update user profile")
async def update_profile(
    request: UpdateUserRequest,
    current_user: UserModel = Depends(require_active_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfile:
    """Update mutable profile fields (currently: full_name)."""
    from app.infrastructure.database.repositories.user_repository import UserRepository
    repo = UserRepository(db)
    updated = await repo.update_profile(current_user.id, full_name=request.full_name)
    return UserProfile.model_validate(updated or current_user)
