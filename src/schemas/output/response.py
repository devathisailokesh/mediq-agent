"""API response (output) schemas — payloads returned by FastAPI endpoints."""

from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field

from src.schemas.output.pubmed import Citation


class QueryResponse(BaseModel):
    """Response payload returned by POST /query."""

    session_id: str = Field(..., description="Session ID (echoed or newly created)")
    answer: str = Field(..., description="Final synthesized medical answer")
    citations: List[Citation] = Field(
        default_factory=list, description="Papers used to generate the answer"
    )


class ConversationTurn(BaseModel):
    """A single question-answer pair stored in memory."""

    session_id: str
    question: str
    answer: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class HistoryResponse(BaseModel):
    """Response payload returned by GET /history/{session_id}."""

    session_id: str
    turns: List[ConversationTurn] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Response payload returned by GET /health."""

    status: str = Field(default="ok")
    model: str = Field(..., description="LLM model in use")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
