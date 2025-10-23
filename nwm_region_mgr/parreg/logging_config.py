"""Logging configuration."""

import logging


def setup_logging(level=logging.INFO):
    """Configure logging."""
    root_logger = logging.getLogger()

    if not root_logger.hasHandlers():
        # No handlers found: set up basic configuration
        logging.basicConfig(
            level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
