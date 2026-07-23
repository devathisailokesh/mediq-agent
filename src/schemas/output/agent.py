"""Agent trace and planner output schemas."""

from datetime import datetime, timezone
from typing import List
from pydantic import BaseModel, Field


class AgentStep(BaseModel):
    """A single step in the agent reasoning chain."""

    agent: str = Field(..., description="Agent name: planner | researcher | summarizer")
    action: str = Field(..., description="What the agent did")
    input: str = Field(..., description="Input given to the agent")
    output: str = Field(..., description="Output produced by the agent")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class AgentTrace(BaseModel):
    """Full reasoning trace for one user query."""

    session_id: str = Field(..., description="Unique session identifier")
    query: str = Field(..., description="Original user question")
    steps: List[AgentStep] = Field(default_factory=list)
    papers_retrieved: int = Field(default=0, description="Number of PubMed papers fetched")
    total_duration_seconds: float = Field(default=0.0)


class SearchPlan(BaseModel):
    """Structured output produced by the Planner agent."""

    search_queries: List[str] = Field(
        ...,
        min_length=1,
        description="PubMed search queries to run",
    )
    reasoning: str = Field(..., description="Planner's chain-of-thought")
    medical_domain: str = Field(..., description="Detected medical domain/specialty")
