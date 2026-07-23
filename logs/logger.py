"""
Centralized logger for the MediQ Agent.

Every module imports get_logger(__name__) so log lines show
the exact file, function, and line number that produced them.
"""

import logging


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger that discards all output.

    Usage in any module:
        from logs.logger import get_logger
        logger = get_logger(__name__)

    Args:
        name: Typically __name__ of the calling module.

    Returns:
        logging.Logger: Silent logger — no file, no console output.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.addHandler(logging.NullHandler())
        logger.propagate = False

    return logger
