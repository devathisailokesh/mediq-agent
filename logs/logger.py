"""
Centralized logger for the MediQ Agent.

Writes to a daily rotating log file only — no console output so the
terminal stays clean when running Streamlit or uvicorn.

Every module imports get_logger(__name__) so log lines show
the exact file, function, and line number that produced them.
"""

import logging
import os
from datetime import datetime
from pathlib import Path


LOG_DIR = Path(__file__).parent
LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | "
    "%(filename)s:%(funcName)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger that writes to a daily log file.

    Logs go to logs/mediq_YYYY-MM-DD.log only — no console output.
    Log level is controlled by the LOG_LEVEL environment variable
    (default: INFO).

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Clear any existing handlers (e.g. stale NullHandler from old runs)
    logger.handlers.clear()

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(log_level)

    # Console handler — visible in Streamlit Cloud logs tab and local terminal
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
    logger.addHandler(console_handler)

    # File handler — local only (skipped if logs/ dir is not writable)
    try:
        log_file = LOG_DIR / f"mediq_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
        logger.addHandler(file_handler)
    except OSError:
        pass

    logger.propagate = False

    return logger
