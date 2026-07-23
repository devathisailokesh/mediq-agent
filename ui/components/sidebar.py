"""
Sidebar component for the MediQ Streamlit application.

Renders session controls (new-session button, session ID display) and
query settings (max-papers slider). Returns selected settings as a plain
dict so the caller is not coupled to any Streamlit widget internals.
"""

import streamlit as st

from ui import state
from ui.config import MAX_PAPERS_DEFAULT, MAX_PAPERS_MAX, MAX_PAPERS_MIN


def render() -> dict:
    """
    Render the settings sidebar and return the selected configuration.

    The 'New session' button is handled internally — it resets state
    and triggers a Streamlit rerun, so the caller does not need to
    react to it explicitly.

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

    return {"max_papers": max_papers}
