"""
Backend client for the MediQ Streamlit application.

Calls MediQAgent directly — no FastAPI server needed for the UI.
The FastAPI layer (src/api/) can be run independently to showcase
or share the REST API separately.
"""

import sys
from pathlib import Path

# Add project root so src.agents imports resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.agents.agent import MediQAgent

# Initialised once at import time — avoids creating a new Groq client per question
_agent = MediQAgent()


def ask_question(question: str, session_id: str, max_papers: int) -> dict:
    """
    Run the full agent pipeline for a medical question.

    Args:
        question: Medical question submitted by the user.
        session_id: Active session ID for conversation continuity.
        max_papers: Maximum number of PubMed papers to retrieve (1–20).

    Returns:
        dict: Response containing:
            - 'answer'    (str)  — synthesized medical answer.
            - 'citations' (list) — list of dicts with 'pubmed_id', 'title', 'url'.

    Raises:
        RuntimeError: If the agent pipeline fails.
    """
    result = _agent.run(
        query=question,
        session_id=session_id,
        max_papers=max_papers,
    )
    return {
        "answer": result["answer"],
        "citations": [
            {
                "pubmed_id": c["pubmed_id"],
                "title": c["title"],
                "url": c["url"],
            }
            for c in result["citations"]
        ],
    }
