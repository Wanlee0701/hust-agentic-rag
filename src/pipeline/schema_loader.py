"""
schema_loader.py — Load intent schema và university metadata.

Hỗ trợ 2 nguồn schema:
  1. university_schema.yaml (ưu tiên — auto-discovery, tái dùng cho bất kỳ trường nào)
  2. config.yaml['intents'] (fallback — tương thích ngược hệ thống hiện tại)
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

logger = logging.getLogger(__name__)

_DEFAULT_SCHEMA_PATH = Path("./university_schema.yaml")


class SchemaLoader:
    """
    Load schema cho IntentClassifier.

    - Đọc university_schema.yaml nếu tồn tại (dynamic schema).
    - Fallback về config.yaml['intents'] nếu không có schema riêng.
    - Cung cấp university info để build system prompt động.
    """

    def __init__(self, config: Dict[str, Any], schema_path: str = None):
        """
        Args:
            config: Dict toàn bộ config từ config.yaml.
            schema_path: Đường dẫn tới university_schema.yaml (mặc định: ./university_schema.yaml).
        """
        self._config = config
        self._schema_path = Path(schema_path) if schema_path else _DEFAULT_SCHEMA_PATH
        self._schema: Optional[Dict[str, Any]] = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Thử load university_schema.yaml. Không raise nếu file không tồn tại."""
        if self._schema_path.exists():
            try:
                with open(self._schema_path, "r", encoding="utf-8") as f:
                    self._schema = yaml.safe_load(f) or {}
                logger.info(
                    f"[SchemaLoader] Loaded schema from {self._schema_path}"
                )
            except Exception as e:
                logger.warning(
                    f"[SchemaLoader] Không parse được {self._schema_path}: {e}. "
                    "Sẽ dùng fallback config.yaml."
                )
                self._schema = None
        else:
            logger.info(
                "[SchemaLoader] university_schema.yaml chưa tồn tại. "
                "Dùng config.yaml['intents'] làm fallback."
            )

    def schema_exists(self) -> bool:
        """Kiểm tra university_schema.yaml có tồn tại và parse thành công không."""
        return self._schema is not None

    def load_university_info(self) -> Dict[str, Any]:
        """
        Trả về thông tin trường đại học từ schema.

        Returns:
            Dict với keys: 'name' (str), 'source_documents' (list[str]).
            Trả về dict rỗng nếu không có schema.
        Example:
            {
                "name": "Đại học Bách Khoa Hà Nội",
                "source_documents": ["Quy chế đào tạo", "Quy chế CTSV", ...]
            }
        """
        if not self._schema:
            return {}
        uni = self._schema.get("university", {})
        return {
            "name": uni.get("name", ""),
            "source_documents": uni.get("source_documents", []),
        }

    def load(self) -> Dict[str, Any]:
        """
        Trả về intent config để khởi tạo IntentClassifier.

        - Nếu có university_schema.yaml → trả về intents từ đó.
        - Nếu không → fallback về config.yaml['intents'].

        Returns:
            Dict intent config, hoặc dict rỗng nếu không tìm thấy gì.
        """
        if self._schema and "intents" in self._schema:
            intents = self._schema["intents"]
            logger.info(
                f"[SchemaLoader] Loaded {len(intents)} intents from university_schema.yaml"
            )
            return intents

        # Fallback về config.yaml
        fallback = self._config.get("intents", {})
        if fallback:
            logger.info(
                f"[SchemaLoader] Fallback: Loaded {len(fallback)} intents from config.yaml"
            )
        else:
            logger.warning(
                "[SchemaLoader] Không tìm thấy intent schema nào. "
                "IntentClassifier sẽ dùng GENERAL_REGULATION mặc định."
            )
        return fallback

    def load_domain_entities(self) -> Dict[str, Any]:
        """
        Trả về domain_entities schema (entity definitions động).

        - Nếu có university_schema.yaml → trả về từ đó.
        - Nếu không → trả về dict rỗng (IntentClassifier sẽ dùng _default_entities).

        Returns:
            Dict với key = entity_name, value = {description, examples, clarification_prompt}.
        """
        if self._schema and "domain_entities" in self._schema:
            entities = self._schema["domain_entities"]
            logger.info(
                f"[SchemaLoader] Loaded {len(entities)} domain entities from schema"
            )
            return entities
        return {}
