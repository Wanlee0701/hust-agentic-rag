"""
evaluate_tool.py — Tool đánh giá mức độ liên quan của tài liệu.

Logic 2 tầng:
  1. Tầng 1 (nhanh): Kiểm tra avg cosine similarity.
  2. Tầng 2 (chậm): Gọi LLM evaluate nếu avg_sim thấp.
"""
import json
import logging
import re
from typing import Any, Callable, Dict, List, Tuple

from src.agent.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_EVALUATE_PROMPT = """\
Bạn là trợ lý AI về quy chế đào tạo ĐHBK Hà Nội.

Câu hỏi của sinh viên: "{question}"

Dưới đây là các đoạn tài liệu tìm được:
{context}

Nhiệm vụ: Đánh giá xem tài liệu trên có ĐỀ CẬP đến chủ đề câu hỏi hay không.
Lưu ý:
- Tài liệu KHÔNG cần trả lời hoàn chỉnh 100%.
- Chỉ cần chứa thông tin liên quan là ĐỦ (relevant=true).
- Chỉ relevant=false nếu hoàn toàn khác chủ đề.

Trả về JSON duy nhất:
{{"relevant": true/false, "reason": "Lý do ngắn gọn"}}"""


class EvaluateTool(BaseTool):

    @property
    def name(self) -> str:
        return "evaluate_relevance"

    @property
    def description(self) -> str:
        return "Đánh giá mức độ liên quan của tài liệu tìm được."

    def execute(
        self,
        *,
        question: str,
        results: List[Tuple],
        min_avg_sim: float,
        llm_invoker: Callable[[str], str],
        top_k: int = 3,
        **kwargs,
    ) -> ToolResult:
        if not results:
            return ToolResult(
                success=True,
                data={"relevant": False, "avg_sim": 0.0, "reason": "Không có tài liệu"},
            )

        # ── Tầng 1: Avg-Similarity Check ──
        recent_scores = [score for _, score in results[:top_k]]
        avg_sim = sum(recent_scores) / max(len(recent_scores), 1)
        logger.info(
            f"[EvaluateTool] avg_sim={avg_sim:.3f} (ngưỡng: {min_avg_sim:.2f})"
        )

        if avg_sim >= min_avg_sim:
            return ToolResult(
                success=True,
                data={
                    "relevant": True,
                    "avg_sim": avg_sim,
                    "reason": f"avg_similarity={avg_sim:.2f} >= {min_avg_sim}",
                },
            )

        # ── Tầng 2: LLM Evaluate ──
        logger.info("[EvaluateTool] avg_sim thấp → gọi LLM evaluate")
        context = self._build_context(results[:top_k])
        is_relevant, reason = self._llm_evaluate(question, context, llm_invoker)
        return ToolResult(
            success=True,
            data={"relevant": is_relevant, "avg_sim": avg_sim, "reason": reason},
        )

    @staticmethod
    def _build_context(results: list) -> str:
        parts = []
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            source = meta.get("source_file") or meta.get("source") or "N/A"
            parts.append(
                f"--- Đoạn {i} | Nguồn: {source} | Score: {score:.1%} ---\n{content}"
            )
        return "\n\n".join(parts)

    @staticmethod
    def _llm_evaluate(
        question: str, context: str, llm_invoker: Callable
    ) -> Tuple[bool, str]:
        prompt = _EVALUATE_PROMPT.format(question=question, context=context[:2000])
        raw = ""
        try:
            raw = llm_invoker(prompt)
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                return (
                    bool(data.get("relevant", data.get("sufficient", True))),
                    data.get("reason", ""),
                )
        except Exception as e:
            logger.warning(f"[EvaluateTool] Parse error: {e}. Raw: {raw[:200]}")
        return True, "Không parse được kết quả đánh giá"
