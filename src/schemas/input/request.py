"""API request (input) schemas — payloads accepted by FastAPI endpoints."""

from typing import Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request payload for POST /query."""

    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Medical question to research and answer",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID for conversation continuity; generated if omitted",
    )
    max_papers: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of PubMed papers to retrieve (1–20)",
    )
