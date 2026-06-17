"""
schema_loader.py — Trung gian đọc schema intent cho IntentClassifier.

Ưu tiên theo thứ tự:
  1. university_schema.yaml (auto-generated bởi SchemaDiscoveryEngine)
  2. config.yaml['intents'] (hardcoded — chỉ dùng làm fallback)

Thiết kế này cho phép hệ thống hoạt động ngay cả khi chưa chạy
discover_schema.py, đồng thời sẵn sàng chuyển sang schema động khi đã có.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  SchemaLoader
# ---------------------------------------------------------------------------

class SchemaLoader:
    """
    Load intent schema từ university_schema.yaml hoặc fallback về config.yaml.

    Cung cấp interface thống nhất cho IntentClassifier bất kể nguồn schema.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Args:
            config: Dict đầy đủ từ config.yaml (toàn bộ file).
        """
        self._config = config
        self._schema_cfg = config.get("schema", {})
        self._auto_discovery = self._schema_cfg.get("auto_discovery", True)
        self._schema_path = Path(
            self._schema_cfg.get("schema_path", "./university_schema.yaml")
        )
        self._fallback = self._schema_cfg.get("fallback_to_config_intents", True)

    # ----------------------------------------------------------------------- #
    #  Public API                                                               #
    # ----------------------------------------------------------------------- #

    def load(self) -> Dict[str, Any]:
        """
        Nạp và trả về dict intent config hợp lệ cho IntentClassifier.

        Returns:
            Dict có cấu trúc giống config.yaml['intents']:
            {
                "INTENT_NAME": {
                    "description": str,
                    "requires_entities": bool,
                    "required_fields": List[str],
                    "clarification_template": str,
                    "examples": List[str],
                },
                ...
            }
        """
        # Thử load university_schema.yaml trước
        if self._auto_discovery and self._schema_path.exists():
            try:
                schema = self._load_university_schema()
                if schema:
                    logger.info(
                        f"[SchemaLoader] ✅ Loaded from university_schema.yaml "
                        f"({len(schema)} intents)"
                    )
                    return schema
            except Exception as e:
                logger.warning(
                    f"[SchemaLoader] Không đọc được university_schema.yaml: {e}. "
                    f"Fallback về config.yaml."
                )

        # Fallback về config.yaml['intents']
        if self._fallback:
            config_intents = self._config.get("intents", {})
            if config_intents:
                logger.info(
                    f"[SchemaLoader] ⚠️  Fallback: dùng intents từ config.yaml "
                    f"({len(config_intents)} intents). "
                    f"Chạy 'python scripts/discover_schema.py' để sinh schema tự động."
                )
                return config_intents

        logger.error("[SchemaLoader] ❌ Không tìm thấy intent schema nào.")
        return {}

    def load_domain_entities(self) -> Dict[str, Any]:
        """
        Trả về domain_entities từ university_schema.yaml.
        Dùng để inject vào prompt động (entity names, ví dụ, câu hỏi làm rõ).

        Returns:
            Dict {entity_name: {description, examples, clarification_prompt, ...}}
            Trả về {} nếu không có schema hoặc schema không có domain_entities.
        """
        if self._auto_discovery and self._schema_path.exists():
            try:
                raw = self._read_yaml(self._schema_path)
                return raw.get("domain_entities", {})
            except Exception as e:
                logger.warning(f"[SchemaLoader] load_domain_entities error: {e}")
        return {}

    def load_university_info(self) -> Dict[str, Any]:
        """
        Trả về thông tin trường đại học từ university_schema.yaml.

        Returns:
            Dict {name, generated_at, document_list, ...}
        """
        if self._auto_discovery and self._schema_path.exists():
            try:
                raw = self._read_yaml(self._schema_path)
                return raw.get("university", {})
            except Exception as e:
                logger.warning(f"[SchemaLoader] load_university_info error: {e}")
        return {
            "name": self._config.get("system", {}).get("name", "University Chatbot"),
            "document_list": [],
        }

    def schema_exists(self) -> bool:
        """Kiểm tra university_schema.yaml đã được sinh chưa."""
        return self._schema_path.exists()

    # ----------------------------------------------------------------------- #
    #  Private helpers                                                          #
    # ----------------------------------------------------------------------- #

    def _load_university_schema(self) -> Dict[str, Any]:
        """Đọc university_schema.yaml và trả về section intents."""
        raw = self._read_yaml(self._schema_path)
        intents = raw.get("intents", {})
        if not intents:
            logger.warning("[SchemaLoader] university_schema.yaml không có section 'intents'.")
        return intents

    @staticmethod
    def _read_yaml(path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
