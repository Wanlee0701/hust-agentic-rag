"""
src/utils.py — Backward compatibility shim
Import từ đây vẫn hoạt động, nhưng ưu tiên dùng:
  from src.utils.config import ConfigManager, load_config
  from src.utils.logger import setup_logger, get_logger
"""
from src.utils.config import (
    ConfigManager,
    load_config,
    ROOT_DIR,
    DATA_DIR,
    LOGS_DIR,
    MODELS_DIR,
    KB_DIR,
)
from src.utils.logger import setup_logger, get_logger

# Alias cũ để không phá vỡ code cũ
class LoggerSetup:
    setup_logger = staticmethod(setup_logger)

# Load config mặc định
try:
    CONFIG = ConfigManager.load()
except FileNotFoundError:
    CONFIG = {}

logger = get_logger(__name__)

__all__ = [
    "ConfigManager", "LoggerSetup", "load_config", "setup_logger", "get_logger",
    "CONFIG", "logger",
    "ROOT_DIR", "DATA_DIR", "LOGS_DIR", "MODELS_DIR", "KB_DIR",
]
