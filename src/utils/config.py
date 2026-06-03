"""
Config Manager — Đọc và quản lý cấu hình từ config.yaml
"""
from pathlib import Path
from typing import Dict, Any
import yaml

# Đường dẫn gốc dự án (2 cấp lên từ src/utils/)
ROOT_DIR = Path(__file__).parent.parent.parent

# Các thư mục chuẩn
DOCS_DIR        = ROOT_DIR / "docs"
SRC_DIR         = ROOT_DIR / "src"
DATA_DIR        = ROOT_DIR / "data"
RAW_JSON_DIR    = ROOT_DIR / "data" / "raw_json"
CHUNKS_DIR      = ROOT_DIR / "data" / "chunks"
CHROMA_DIR      = ROOT_DIR / "data" / "chroma"
LOGS_DIR        = ROOT_DIR / "logs"
MODELS_DIR      = ROOT_DIR / "models"
KB_DIR          = ROOT_DIR / "knowledge_base"
SCRIPTS_DIR     = ROOT_DIR / "scripts"
NOTEBOOKS_DIR   = ROOT_DIR / "notebooks"
TESTS_DIR       = ROOT_DIR / "tests"

# Tạo thư mục bắt buộc nếu chưa có
for _dir in [LOGS_DIR, MODELS_DIR, CHROMA_DIR, CHUNKS_DIR, RAW_JSON_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


class ConfigManager:
    """Load và cache cấu hình từ config.yaml"""

    _cache: Dict[str, Any] = {}

    @staticmethod
    def load(config_path: str = "config.yaml") -> Dict[str, Any]:
        """Đọc file YAML và trả về dict config"""
        if config_path in ConfigManager._cache:
            return ConfigManager._cache[config_path]

        config_file = ROOT_DIR / config_path
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")

        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Override từ biến môi trường (Environment Variables) cho Docker
        import os
        llm_url = os.getenv("LLM_SERVICE_URL")
        if llm_url and "llm" in config:
            config["llm"]["base_url"] = llm_url

        ConfigManager._cache[config_path] = config
        return config

    @staticmethod
    def get(section: str, key: str = None, default=None, config_path: str = "config.yaml"):
        """Lấy một section hoặc key cụ thể từ config"""
        config = ConfigManager.load(config_path)
        section_data = config.get(section, {})
        if key is None:
            return section_data
        return section_data.get(key, default)


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """Shorthand function để load config"""
    return ConfigManager.load(config_path)
