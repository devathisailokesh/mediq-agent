"""
Chat input component for the MediQ Streamlit application.

Handles user input, API calls, error display, and session state updates.
Renders both the user bubble and the assistant response bubble before
persisting messages to session state — so on rerun, chat_history.py
replays them correctly.
"""

import requests
import streamlit as st

from ui import api_client, state
from ui.components import citations as citations_component


def render(max_papers: int) -> None:
    """
    Render the chat input box and handle a submitted question end-to-end.

    Flow on submission:
        1. User question is appended to state and rendered immediately.
        2. API is called under a spinner inside the assistant bubble.
        3. Answer and citations are rendered and persisted to state.

    Does nothing when the input box is empty (no submission).

    Args:
        max_papers: PubMed paper limit forwarded to the backend request.
    """
    question = st.chat_input("Ask a medical question...")

    if not question:
        return

    state.append_message("user", question)
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Searching PubMed and generating answer..."):
            _fetch_and_render(question, max_papers)


def _fetch_and_render(question: str, max_papers: int) -> None:
    """
    Call the backend API, render the response, and persist it to state.

    All error cases (connection failure, HTTP error, timeout, unexpected
    exception) display a user-facing error message instead of a traceback.

    Args:
        question: Medical question to send to the API.
        max_papers: PubMed paper retrieval limit to include in the request.
    """
    try:
        data = api_client.ask_question(
            question=question,
            session_id=state.get_session_id(),
            max_papers=max_papers,
        )

        answer = data["answer"]
        citations = data.get("citations", [])

        st.markdown(answer)
        citations_component.render(citations)

        state.append_message("assistant", answer, citations=citations)

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to the API. Make sure the server is running:\n"
            "```\npython -m uvicorn src.api.main:app --reload\n```"
        )
    except requests.exceptions.HTTPError as exc:
        detail = exc.response.json().get("detail", str(exc))
        st.error(f"API error: {detail}")
    except requests.exceptions.Timeout:
        st.error(
            "Request timed out. Try reducing the number of papers or try again."
        )
    except Exception as exc:
        st.error(f"Unexpected error: {exc}")
