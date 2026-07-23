"""
MediQ Streamlit application — entry point.

Wires together all UI components and delegates all logic to them.
This file contains no business logic — only page configuration,
state initialisation, and component orchestration.

Run with:
    streamlit run ui/app.py
"""

import sys
from pathlib import Path

# Make project root importable so 'ui.*' and 'src.*' resolve correctly
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

from ui import state
from ui.components import chat_history, chat_input, sidebar
from ui.config import APP_CAPTION, APP_TITLE, PAGE_ICON, PAGE_LAYOUT, PAGE_TITLE


def main() -> None:
    """
    Configure the page, initialise state, and render all UI components.

    Components are rendered in this fixed order:
        1. Sidebar      — settings panel and session controls (always visible).
        2. Header       — page title and caption.
        3. Chat history — past messages replayed from session state.
        4. Chat input   — input box, API call, and live response rendering.
    """
    st.set_page_config(
        page_title=PAGE_TITLE,
        page_icon=PAGE_ICON,
        layout=PAGE_LAYOUT,
    )

    state.init()

    settings = sidebar.render()

    st.title(APP_TITLE)
    st.caption(APP_CAPTION)
    st.divider()

    chat_history.render()
    chat_input.render(max_papers=settings["max_papers"])


if __name__ == "__main__":
    main()
