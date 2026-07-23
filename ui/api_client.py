"""
HTTP client for the MediQ FastAPI backend.

Wraps all network calls in typed functions so components never construct
raw requests. URL paths, timeout, and error propagation all live here —
callers only deal with Python dicts and documented exceptions.
"""

import requests

from ui.config import API_BASE_URL, API_TIMEOUT_SECONDS


def ask_question(question: str, session_id: str, max_papers: int) -> dict:
    """
    POST /query — run the full agent pipeline for a medical question.

    Args:
        question: Medical question submitted by the user.
        session_id: Active session ID for conversation continuity.
        max_papers: Maximum number of PubMed papers to retrieve (1–20).

    Returns:
        dict: Parsed JSON response containing:
            - 'answer'    (str)  — synthesized medical answer.
            - 'citations' (list) — list of citation dicts with
                                   'pubmed_id', 'title', and 'url'.

    Raises:
        requests.exceptions.ConnectionError: If the API server is unreachable.
        requests.exceptions.HTTPError: If the API returns a 4xx or 5xx status.
        requests.exceptions.Timeout: If the request exceeds API_TIMEOUT_SECONDS.
    """
    response = requests.post(
        f"{API_BASE_URL}/query",
        json={
            "question": question,
            "session_id": session_id,
            "max_papers": max_papers,
        },
        timeout=API_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()
