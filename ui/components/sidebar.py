"""
Sidebar component for the MediQ Streamlit application.

Renders session controls (new-session button, session ID display),
query settings (max-papers slider), and past conversation history
loaded from the SQLite memory store.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.memory.store import MemoryStore
from ui import state
from ui.config import MAX_PAPERS_DEFAULT, MAX_PAPERS_MAX, MAX_PAPERS_MIN

_store = MemoryStore()


def render() -> dict:
    """
    Render the settings sidebar and return the selected configuration.

    Sections:
        - Settings: max-papers slider.
        - Session: new-session button and current session ID.
        - History: past Q&A turns from SQLite for the active session.

    Returns:
        dict: Selected settings:
            - 'max_papers' (int) — number of PubMed papers to retrieve.
    """
    with st.sidebar:
        st.header("⚙️ Settings")
        st.divider()

        max_papers = st.slider(
            "Max PubMed papers",
            min_value=MAX_PAPERS_MIN,
            max_value=MAX_PAPERS_MAX,
            value=MAX_PAPERS_DEFAULT,
            help="Higher values improve answer quality but increase response time.",
        )

        st.divider()

        if st.button("🔄 New session", use_container_width=True):
            state.reset()
            st.rerun()

        st.caption(f"Session: `{state.get_session_id()[:8]}...`")

        st.divider()

        if st.button("🔃 Refresh history", use_container_width=True):
            st.rerun()

        _render_history()

    return {"max_papers": max_papers}


def _render_history() -> None:
    """
    Render past conversation turns from SQLite for the active session.

    Shows each past question as an expander containing the answer.
    Silently renders nothing if no history exists for this session.
    """
    st.subheader("🕓 History")

    turns = _store.get_history(state.get_session_id(), limit=20)

    if not turns:
        st.caption("No history yet for this session.")
        return

    for turn in reversed(turns):
        with st.expander(f"Q: {turn.question[:50]}{'...' if len(turn.question) > 50 else ''}"):
            st.markdown(turn.answer)
