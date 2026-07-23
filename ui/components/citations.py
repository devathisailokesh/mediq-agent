"""
Citations component for the MediQ Streamlit application.

Renders a collapsible expander containing clickable PubMed links.
Isolated in its own module so the citation display format can be
updated without touching the chat history or input components.
"""

from typing import List

import streamlit as st


def render(citations: List[dict]) -> None:
    """
    Render a collapsible citations expander below an assistant message.

    Silently does nothing when the citations list is empty or None,
    so callers do not need to guard against missing citations.

    Args:
        citations: List of citation dicts, each containing:
            - 'pubmed_id' (str) — PubMed article ID.
            - 'title'     (str) — Article title (used as link text).
            - 'url'       (str) — Full PubMed article URL.
    """
    if not citations:
        return

    with st.expander(f"📚 {len(citations)} citation(s)"):
        for citation in citations:
            st.markdown(
                f"- **[{citation['title']}]({citation['url']})** "
                f"`PMID: {citation['pubmed_id']}`"
            )
