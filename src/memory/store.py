"""
SQLite-backed conversation memory store.

Persists question-answer pairs per session so agents can reference
prior turns when answering follow-up questions.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List

from logs.logger import get_logger
from src.config.settings import settings
from src.schemas import ConversationTurn

logger = get_logger(__name__)


class MemoryStore:
    """
    Lightweight conversation memory backed by SQLite.

    Thread-safety note: each call opens and closes its own connection,
    which is safe for single-threaded FastAPI with default workers.
    """

    def __init__(self) -> None:
        """Initialise the store and ensure the schema exists."""
        self._db_path = settings.db_path
        self._init_db()
        logger.info("MemoryStore initialised | db=%s", self._db_path)

    def _connect(self) -> sqlite3.Connection:
        """
        Open a SQLite connection with row factory set to dict-like rows.

        Returns:
            sqlite3.Connection: Open database connection.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """
        Create the conversations table if it does not already exist.

        Raises:
            RuntimeError: If database schema creation fails.
        """
        try:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id          INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id  TEXT NOT NULL,
                        question    TEXT NOT NULL,
                        answer      TEXT NOT NULL,
                        created_at  TEXT NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_session ON conversations(session_id)"
                )
            logger.debug("Database schema verified")
        except sqlite3.Error as exc:
            logger.error("Failed to initialise database: %s", exc, exc_info=True)
            raise RuntimeError(f"Database initialisation failed: {exc}") from exc

    def save_turn(self, session_id: str, question: str, answer: str) -> None:
        """
        Persist a single conversation turn to the database.

        Args:
            session_id: Unique identifier for the conversation session.
            question: User's question.
            answer: Agent's answer.

        Raises:
            RuntimeError: If the database write fails.
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO conversations (session_id, question, answer, created_at) VALUES (?, ?, ?, ?)",
                    (session_id, question, answer, now),
                )
            logger.info("Saved turn | session_id=%s", session_id)
        except sqlite3.Error as exc:
            logger.error("Failed to save turn | session_id=%s | error=%s", session_id, exc, exc_info=True)
            raise RuntimeError(f"Memory save failed: {exc}") from exc

    def get_history(self, session_id: str, limit: int = 10) -> List[ConversationTurn]:
        """
        Retrieve the most recent conversation turns for a session.

        Args:
            session_id: Session to retrieve history for.
            limit: Maximum number of past turns to return.

        Returns:
            List[ConversationTurn]: Ordered list of past turns, empty list on failure.
        """
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT session_id, question, answer, created_at
                    FROM conversations
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                ).fetchall()

            turns = [
                ConversationTurn(
                    session_id=row["session_id"],
                    question=row["question"],
                    answer=row["answer"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
                for row in reversed(rows)
            ]
            logger.debug("Retrieved %d turns for session %s", len(turns), session_id)
            return turns
        except sqlite3.Error as exc:
            logger.error("Failed to get history | session_id=%s | error=%s", session_id, exc, exc_info=True)
            return []

    def format_history_for_prompt(self, session_id: str, limit: int = 5) -> str:
        """
        Format recent history as a plain-text block for injection into prompts.

        Args:
            session_id: Session to format history for.
            limit: Number of prior turns to include.

        Returns:
            str: Formatted history string, or 'No prior conversation.' if empty or on error.
        """
        try:
            turns = self.get_history(session_id, limit=limit)
            if not turns:
                return "No prior conversation."

            lines = []
            for turn in turns:
                lines.append(f"User: {turn.question}")
                lines.append(f"Assistant: {turn.answer}")
            return "\n".join(lines)
        except Exception as exc:
            logger.warning("Could not format history, defaulting to empty: %s", exc)
            return "No prior conversation."
