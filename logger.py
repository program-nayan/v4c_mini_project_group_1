import sys
import os

# Ensure backend package is on path
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "backend"))
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)

from backend.logger import get_logger, setup_logger, logger, LOG_FILE_PATH, LOGS_DIR

__all__ = ["get_logger", "setup_logger", "logger", "LOG_FILE_PATH", "LOGS_DIR"]
