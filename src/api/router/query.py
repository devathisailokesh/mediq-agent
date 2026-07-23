"""
Query router — POST /query

Entry point for the full agent pipeline:
  Planner → Researcher (PubMed RAG) → Summarizer → Response
"""

import uuid

from fastapi import APIRouter, HTTPException

from logs.logger import get_logger
from src.agents.agent import MediQAgent
from src.schemas import (
    Citation,
    QueryRequest,
    QueryResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/query", tags=["Query"])

_agent = MediQAgent()


@router.post("", response_model=QueryResponse, summary="Ask a medical question")
def ask_question(request: QueryRequest) -> QueryResponse:
    """
    Run the full MediQ agent pipeline for a medical question.

    Pipeline steps:
        1. Planner — produces PubMed search queries (chain-of-thought).
        2. Researcher — fetches papers and extracts findings (RAG).
        3. Summarizer — synthesizes the final answer (self-critique).

    Args:
        request: Validated QueryRequest with question and optional session_id.

    Returns:
        QueryResponse: Final answer, citations, and full reasoning trace.

    Raises:
        HTTPException: 500 on any unhandled agent or API failure.
    """
    session_id = request.session_id or str(uuid.uuid4())

    logger.info(
        "New query | session_id=%s | question='%s'",
        session_id,
        request.question[:80],
    )

    try:
        result = _agent.run(
            query=request.question,
            session_id=session_id,
            max_papers=request.max_papers,
        )

        citations = [
            Citation(pubmed_id=c["pubmed_id"], title=c["title"], url=c["url"])
            for c in result["citations"]
        ]

        logger.info("Query complete | session_id=%s", session_id)

        return QueryResponse(
            session_id=session_id,
            answer=result["answer"],
            citations=citations,
        )

    except Exception as exc:
        logger.error("Pipeline failed | session_id=%s | error=%s", session_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(exc)}")
