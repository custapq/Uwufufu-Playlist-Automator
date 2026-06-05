"""
logger.py — Logging configuration for Uwufufu-Automator
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(
    name: str = "uwufufu",
    log_dir: str = "logs",
    level: int = logging.INFO,
) -> logging.Logger:
    """Create a logger that writes to both stdout and a timestamped log file.

    Args:
        name:    Logger name (used as the root for all child loggers).
        log_dir: Directory where log files are written (created if absent).
        level:   Minimum log level for the console handler.

    Returns:
        Configured Logger instance.
    """
    Path(log_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"automation_{timestamp}.log"

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(message)s"))

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)-8s] %(name)s: %(message)s")
    )

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger
