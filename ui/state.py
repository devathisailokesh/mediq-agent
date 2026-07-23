"""
Session state management for the MediQ Streamlit application.

Centralises all st.session_state reads and writes so no component
ever accesses state keys directly. This prevents key typos and means
any rename only touches this file.
"""

import uuid
from typing import Optional

import streamlit as st


def init() -> None:
    """
    Initialise all session state keys on first run.

    Idempotent — safe to call at the top of every Streamlit rerun
    because it only sets keys that do not already exist.
    """
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state.messages = []


def reset() -> None:
    """
    Generate a new session ID and clear the conversation history.

    Called when the user clicks the 'New session' button in the sidebar.
    """
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []


def get_session_id() -> str:
    """
    Return the active session UUID string.

    Returns:
        str: Current session ID.
    """
    return st.session_state.session_id


def get_messages() -> list:
    """
    Return the full conversation message list.

    Returns:
        list: List of message dicts, each with 'role', 'content',
              and an optional 'citations' key on assistant messages.
    """
    return st.session_state.messages


def append_message(
    role: str,
    content: str,
    citations: Optional[list] = None,
) -> None:
    """
    Append a single message to the conversation history.

    Args:
        role: Speaker — either 'user' or 'assistant'.
        content: Message text (markdown supported for assistant).
        citations: Optional list of citation dicts (assistant messages only).
    """
    msg: dict = {"role": role, "content": content}
    if citations is not None:
        msg["citations"] = citations
    st.session_state.messages.append(msg)
