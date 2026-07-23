"""
Chat history component for the MediQ Streamlit application.

Replays all messages stored in session state as a scrollable chat view.
Kept separate from the input component so each concern has a single file.
"""

import streamlit as st

from ui import state
from ui.components import citations as citations_component


def render() -> None:
    """
    Render all past messages from session state as chat bubbles.

    User messages are displayed as plain markdown.
    Assistant messages are displayed as markdown followed by a
    citations expander when citation data is present.

    Iterates over state.get_messages() — does nothing on an empty history.
    """
    for message in state.get_messages():
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant":
                citations_component.render(message.get("citations", []))
