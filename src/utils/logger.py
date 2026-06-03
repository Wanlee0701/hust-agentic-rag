"""
Logger Setup — Cấu hình logging thống nhất cho toàn hệ thống
"""
import logging
import sys
from pathlib import Path
from typing import Optional

# Tránh circular import — dùng literal path thay vì import từ config
LOGS_DIR = Path(__file__).parent.parent.parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Registry lưu loggers đã tạo (tránh duplicate handlers)
_loggers: dict = {}


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = "chatbot.log",
) -> logging.Logger:
    """
    Tạo hoặc lấy logger đã tồn tại.

    Args:
        name: Tên logger (thường là __name__ của module)
        level: Log level (DEBUG/INFO/WARNING/ERROR)
        log_file: Tên file log trong logs/ (None = không ghi file)

    Returns:
        logging.Logger
    """
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Tránh duplicate nếu logger cha đã có handler
    if logger.handlers:
        _loggers[name] = logger
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(formatter)
    console.setLevel(logging.DEBUG)
    logger.addHandler(console)

    # File handler (optional)
    if log_file:
        fh = logging.FileHandler(LOGS_DIR / log_file, encoding="utf-8")
        fh.setFormatter(formatter)
        fh.setLevel(logging.DEBUG)
        logger.addHandler(fh)

    logger.propagate = False
    _loggers[name] = logger
    return logger


def get_logger(name: str) -> logging.Logger:
    """Lấy logger đã tạo, hoặc tạo mới với cài đặt mặc định"""
    return _loggers.get(name) or setup_logger(name)
