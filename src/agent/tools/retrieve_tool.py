"""
retrieve_tool.py — Tool tìm kiếm tài liệu từ Vector Database.
"""
import logging
from typing import Any, Dict

from src.agent.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class RetrieveTool(BaseTool):

    @property
    def name(self) -> str:
        return "retrieve_documents"

    @property
    def description(self) -> str:
        return "Tìm kiếm tài liệu liên quan từ ChromaDB."

    def __init__(self, vector_db_manager, config: Dict[str, Any]):
        retrieval_cfg = config.get("retrieval", {})
        self._vector_db = vector_db_manager
        self._top_k = retrieval_cfg.get("top_k", 3)
        self._threshold = retrieval_cfg.get("similarity_threshold", 0.35)

    def execute(self, *, query: str, **kwargs) -> ToolResult:
        try:
            results = self._vector_db.search_similar(
                query=query, k=self._top_k, score_threshold=self._threshold
            )
            if len(results) < 2 and self._threshold > 0.25:
                logger.info(
                    f"[RetrieveTool] Fallback: {len(results)} docs, lower threshold"
                )
                results = self._vector_db.search_similar(
                    query=query, k=self._top_k + 2, score_threshold=0.25,
                )
            logger.info(f"[RetrieveTool] '{query[:50]}' -> {len(results)} docs")
            return ToolResult(
                success=len(results) > 0,
                data=results,
                message=f"Tìm được {len(results)} đoạn tài liệu",
            )
        except Exception as e:
            logger.error(f"[RetrieveTool] Error: {e}")
            return ToolResult(success=False, data=[], message=f"Lỗi: {e}")
