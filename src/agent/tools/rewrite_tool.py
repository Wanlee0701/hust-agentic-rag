"""
rewrite_tool.py — Tool viết lại câu hỏi với thuật ngữ chính xác hơn.
"""
import logging
from typing import Callable

from src.agent.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_REWRITE_PROMPT = """\
Bạn là chuyên gia về quy chế đào tạo ĐHBK Hà Nội.

=== LỊCH SỬ HỘI THOẠI GẦN ĐÂY ===
{memory_context}

=== CÂU HỎI HIỆN TẠI ===
"{question}"

Lý do tìm kiếm chưa đủ: "{reason}"

Hãy viết lại câu hỏi dùng thuật ngữ pháp lý/học thuật chính xác hơn.
QUAN TRỌNG: Dựa vào LỊCH SỬ HỘI THOẠI để hiểu ngữ cảnh. Nếu các turn trước đang nói về chủ đề A, thì câu hỏi hiện tại cũng về A.
Chỉ trả về 1 câu duy nhất, KHÔNG giải thích.

Ví dụ:
- "trượt 14 tín" → "cảnh cáo học tập tín chỉ nợ không đạt"
- "bị đuổi học" → "buộc thôi học do điểm tích lũy thấp"

Câu viết lại:"""


class RewriteTool(BaseTool):

    @property
    def name(self) -> str:
        return "rewrite_query"

    @property
    def description(self) -> str:
        return "Viết lại câu hỏi để cải thiện retrieval."

    def __init__(self, llm_invoker: Callable[[str], str]):
        self._llm_invoker = llm_invoker

    def execute(self, *, question: str, reason: str = "", memory_context: str = "", **kwargs) -> ToolResult:
        prompt = _REWRITE_PROMPT.format(
            question=question,
            reason=reason,
            memory_context=memory_context if memory_context else "(Không có lịch sử)",
        )
        try:
            rewritten = self._llm_invoker(prompt).strip().strip("\"'")
            if rewritten and rewritten != question:
                logger.info(f"[RewriteTool] '{question[:40]}' -> '{rewritten[:60]}'")
                return ToolResult(
                    success=True, data=rewritten, message=f"Query mới: {rewritten}"
                )
            return ToolResult(
                success=False, data=question, message="Không tạo được query mới"
            )
        except Exception as e:
            logger.warning(f"[RewriteTool] Error: {e}")
            return ToolResult(success=False, data=question, message=f"Lỗi: {e}")
