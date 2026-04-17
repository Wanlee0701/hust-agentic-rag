"""
Utilities for configuration, logging, and constants
"""
import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any

# Paths
BASE_DIR = Path(__file__).parent
DOCS_DIR = BASE_DIR / "docs"
SRC_DIR = BASE_DIR / "src"
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
MODELS_DIR = BASE_DIR / "models"
KB_DIR = BASE_DIR / "knowledge_base"

# Create directories if not exist
for directory in [LOGS_DIR, MODELS_DIR, DATA_DIR / "chroma"]:
    directory.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Load and manage configuration"""
    
    @staticmethod
    def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
        """Load YAML configuration file"""
        config_file = BASE_DIR / config_path
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        return config


class LoggerSetup:
    """Configure logging"""
    
    @staticmethod
    def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
        """Setup logger with file and console handlers"""
        logger = logging.getLogger(name)
        logger.setLevel(getattr(logging, level.upper()))
        
        # Format
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = LOGS_DIR / "chatbot.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger


# Load configuration
try:
    CONFIG = ConfigManager.load_config()
except FileNotFoundError:
    print("Warning: config.yaml not found. Using defaults.")
    CONFIG = {}

# Setup main logger
logger = LoggerSetup.setup_logger(__name__, CONFIG.get("logging", {}).get("level", "INFO"))


class Constants:
    """Application constants"""
    
    # Model dimensions
    EMBEDDING_DIM = 768
    
    # Retrieval
    DEFAULT_TOP_K = 5
    DEFAULT_SIMILARITY_THRESHOLD = 0.5
    SEMANTIC_WEIGHT = 0.6
    KEYWORD_WEIGHT = 0.4
    
    # Agent
    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_CONFIDENCE_THRESHOLD = 0.75
    
    # Timeouts
    LLM_TIMEOUT_SECONDS = 30
    RETRIEVAL_TIMEOUT_SECONDS = 10
    
    # Text processing
    DEFAULT_CHUNK_SIZE = 1000
    DEFAULT_CHUNK_OVERLAP = 100


if __name__ == "__main__":
    logger.info("Configuration loaded successfully")
    logger.info(f"Base directory: {BASE_DIR}")
    logger.info(f"Data directory: {DATA_DIR}")
