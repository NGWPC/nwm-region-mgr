"""Logging configuration."""

import logging
from pathlib import Path
from typing import Iterable, Optional, Union


def setup_logging(
    level: int = logging.INFO,
    target_packages: Iterable[str] = ("utils",),
    log_file: Optional[Union[str, Path]] = None,
    file_level: Optional[int] = None,
):
    """Configure logging for specific packages with optional file output.

    Args:
        level: Logging level for console output (default: INFO).
        target_packages: Iterable of package names to configure logging for.
        log_file: Optional path to a file where logs will be written.
        file_level: Logging level for file output (default: same as console level).

    """
    # Set root logger to WARNING to suppress noisy external logs
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)

    # Remove existing handlers to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Formatter shared by all handlers
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Optional file handler
    file_handler = None
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode="w")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(file_level or level)

    # Apply handlers to each target package
    for pkg in target_packages:
        logger = logging.getLogger(pkg)
        logger.setLevel(min(level, file_level or level))  # Allow lower thresholds
        logger.addHandler(console_handler)
        if file_handler:
            logger.addHandler(file_handler)
        logger.propagate = False  # Prevent duplication through root logger
