"""
Schemas package — re-exports all Pydantic models from input/ and output/ subfolders.

Always import from here:
    from src.schemas import PubMedPaper, QueryRequest, QueryResponse
"""

from src.schemas.input.request import QueryRequest
from src.schemas.output.agent import AgentStep, AgentTrace, SearchPlan
from src.schemas.output.pubmed import Citation, PubMedPaper
from src.schemas.output.response import (
    ConversationTurn,
    HealthResponse,
    HistoryResponse,
    QueryResponse,
)

__all__ = [
    # Input
    "QueryRequest",
    # Output — agent
    "AgentStep",
    "AgentTrace",
    "SearchPlan",
    # Output — pubmed
    "Citation",
    "PubMedPaper",
    # Output — response
    "ConversationTurn",
    "HealthResponse",
    "HistoryResponse",
    "QueryResponse",
]
