"""
History router — GET /history/{session_id}

Returns past conversation turns for a given session from SQLite memory.
"""

from fastapi import APIRouter, HTTPException

from logs.logger import get_logger
from src.memory.store import MemoryStore
from src.schemas import HistoryResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/history", tags=["History"])
_store = MemoryStore()


@router.get("/{session_id}", response_model=HistoryResponse, summary="Get conversation history")
def get_history(session_id: str, limit: int = 10) -> HistoryResponse:
    """
    Retrieve conversation history for a session.

    Args:
        session_id: The session identifier to look up.
        limit: Maximum number of past turns to return (default 10).

    Returns:
        HistoryResponse: Session ID and list of past Q&A turns.

    Raises:
        HTTPException: 404 if session has no recorded history.
        HTTPException: 500 on unexpected errors.
    """
    try:
        logger.info("History requested | session_id=%s | limit=%d", session_id, limit)
        turns = _store.get_history(session_id, limit=limit)

        if not turns:
            raise HTTPException(
                status_code=404,
                detail=f"No history found for session '{session_id}'",
            )

        return HistoryResponse(session_id=session_id, turns=turns)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(
            "get_history failed | session_id=%s | error=%s", session_id, exc, exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"History retrieval error: {exc}")
