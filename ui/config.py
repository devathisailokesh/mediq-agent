"""
UI configuration constants for the MediQ Streamlit application.

All hard-coded values (API URL, page settings, slider bounds) live here
so they can be changed in one place without touching any component logic.
"""

# ── API ───────────────────────────────────────────────────────────────────────
# Reads from env var so Docker can point it at the 'api' service by name.
# Falls back to localhost for local development.
import os
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
API_TIMEOUT_SECONDS: int = 60

# ── Page ──────────────────────────────────────────────────────────────────────
PAGE_TITLE: str = "MediQ"
PAGE_ICON: str = "🩺"
PAGE_LAYOUT: str = "centered"

# ── Header ────────────────────────────────────────────────────────────────────
APP_TITLE: str = "🩺 MediQ — Medical Research Assistant"
APP_CAPTION: str = "Powered by PubMed + Groq LLM"

# ── Sidebar controls ──────────────────────────────────────────────────────────
MAX_PAPERS_MIN: int = 1
MAX_PAPERS_MAX: int = 20
MAX_PAPERS_DEFAULT: int = 5
