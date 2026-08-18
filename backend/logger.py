import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Resolve Project Root Directory (one level up from backend/ directory)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOGS_DIR = PROJECT_ROOT / "logs"
LOG_FILE_PATH = LOGS_DIR / "app.log"

# Default Log Format: Date, Time, Log Level, File Name with Line Number, Function Name, Message
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_is_configured = False


def setup_logger(log_level: int = logging.INFO) -> None:
    """Initializes centralized logging configuration with both file and console handlers."""
    global _is_configured
    if _is_configured:
        return

    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)

    # Base Root Logger
    root_logger = logging.getLogger()
    
    # Read LOG_LEVEL from environment if provided
    env_level = os.getenv("LOG_LEVEL", "").upper()
    if env_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        log_level = getattr(logging, env_level)
    
    root_logger.setLevel(log_level)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    # 1. Rotating File Handler (10MB per file, up to 5 backups)
    file_handler = RotatingFileHandler(
        str(LOG_FILE_PATH),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    # 2. Console Stream Handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # Clear existing handlers to prevent duplicate entries
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    root_logger.addHandler(file_handler)
    root_logger.addHandler(stream_handler)

    _is_configured = True


def get_logger(name: str = None) -> logging.Logger:
    """Returns a configured logger instance for the given module name."""
    if not _is_configured:
        setup_logger()
    return logging.getLogger(name if name else "app")


# Initialize default logger instance
logger = get_logger("app")
