"""
Application settings loaded from environment variables via Pydantic BaseSettings.

All configuration lives here — no hard-coded values anywhere else in the codebase.
Add a field here and expose it in .env.example whenever a new env var is needed.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration for MediQ Agent.

    Values are read from the .env file (or actual environment variables).
    Pydantic validates types and raises on missing required fields at startup.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Groq LLM ──────────────────────────────────────────────────────────────
    groq_api_key: str = Field(..., description="Groq API key (required)")
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model ID to use for all agents",
    )
    temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=2.0,
        description="LLM sampling temperature",
    )
    max_tokens: int = Field(
        default=2048,
        gt=0,
        description="Maximum tokens per LLM response",
    )
    # ── Retry Settings ───────────────────────────────────────────────────────
    max_retries: int = Field(
        default=3,
        ge=1,
        description="Number of retry attempts on API failure",
    )
    retry_delay: float = Field(
        default=2.0,
        ge=0.0,
        description="Seconds to wait between retries",
    )

    # ── PubMed ────────────────────────────────────────────────────────────────
    pubmed_api_key: str = Field(
        default="",
        description="NCBI API key — optional, raises rate limit from 3 to 10 req/s",
    )
    pubmed_base_url: str = Field(
        default="https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
        description="NCBI E-utilities base URL",
    )
    pubmed_max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Max PubMed papers to retrieve per query",
    )

    # ── Memory ────────────────────────────────────────────────────────────────
    db_path: str = Field(
        default="memory.db",
        description="Path to the SQLite database for conversation memory",
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: str = Field(
        default="INFO",
        description="Logging level: DEBUG | INFO | WARNING | ERROR",
    )

    # ── Groq timeout ──────────────────────────────────────────────────────────
    groq_timeout: float = Field(
        default=60.0,
        gt=0,
        description="Seconds before a Groq API call times out",
    )

    # ── Context guard ─────────────────────────────────────────────────────────
    max_context_chars: int = Field(
        default=12000,
        gt=0,
        description="Max characters of PubMed abstracts injected into LLM context",
    )

    # ── API ───────────────────────────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", description="FastAPI host")
    api_port: int = Field(default=8000, description="FastAPI port")


settings = Settings()
