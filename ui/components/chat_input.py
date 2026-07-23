"""
Chat input component for the MediQ Streamlit application.

Handles user input, agent calls, error display, and session state updates.
Renders both the user bubble and the assistant response bubble before
persisting messages to session state — so on rerun, chat_history.py
replays them correctly.
"""

import streamlit as st

from ui import api_client, state
from ui.components import citations as citations_component


def render(max_papers: int) -> None:
    """
    Render the chat input box and handle a submitted question end-to-end.

    Flow on submission:
        1. User question is appended to state and rendered immediately.
        2. Agent is called under a spinner inside the assistant bubble.
        3. Answer and citations are rendered and persisted to state.

    Does nothing when the input box is empty (no submission).

    Args:
        max_papers: PubMed paper limit passed to the agent.
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
    Call the agent, render the response, and persist it to state.

    Args:
        question: Medical question to run through the agent pipeline.
        max_papers: PubMed paper retrieval limit.
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

    except Exception as exc:
        st.error(f"Something went wrong: {exc}")
