"""
generate_tool.py — Tool tổng hợp câu trả lời từ tài liệu.
"""
import logging
from typing import Callable, List, Tuple

from src.agent.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

_ANSWER_PROMPT = """\
{system_prompt}

Dựa trên các đoạn tài liệu quy chế dưới đây, hãy trả lời câu hỏi.
Hãy phát hiện ngôn ngữ của câu hỏi và trả lời bằng ĐÚNG ngôn ngữ đó.

=== TÀI LIỆU THAM KHẢO ===
{context}

=== CÂU HỎI ===
{question}

=== YÊU CẦU ===
- Trả lời trực tiếp, rõ ràng, đúng trọng tâm
- Trích dẫn cụ thể số Điều, Chương, tên văn bản nếu có
- KHÔNG bịa đặt thông tin ngoài tài liệu
- Nếu thông tin không đủ, thừa nhận giới hạn

=== CÂU TRẢ LỜI ==="""


class GenerateTool(BaseTool):

    @property
    def name(self) -> str:
        return "generate_answer"

    @property
    def description(self) -> str:
        return "Tổng hợp câu trả lời cuối cùng từ tài liệu."

    def __init__(self, llm_invoker: Callable[[str], str], system_prompt: str):
        self._llm_invoker = llm_invoker
        self._system_prompt = system_prompt

    def execute(self, *, question: str, results: List[Tuple], **kwargs) -> ToolResult:
        context = self._build_context(results)
        prompt = _ANSWER_PROMPT.format(
            system_prompt=self._system_prompt,
            context=context,
            question=question,
        )
        try:
            answer = self._llm_invoker(prompt)
            logger.info(f"[GenerateTool] Generated {len(answer)} chars")
            return ToolResult(success=True, data=answer, message="Đã tổng hợp")
        except Exception as e:
            logger.error(f"[GenerateTool] Error: {e}")
            return ToolResult(success=False, data="", message=f"Lỗi: {e}")

    @staticmethod
    def _build_context(results: list) -> str:
        parts = []
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            source = meta.get("source_file") or meta.get("source") or "N/A"
            chapter = meta.get("chapter_title", "")
            article = meta.get("article_title", "")
            header = f"--- Đoạn {i} | Nguồn: {source} | Độ liên quan: {score:.1%} ---"
            if chapter:
                header += f"\nChương: {chapter}"
            if article:
                header += f"\nĐiều: {article}"
            parts.append(f"{header}\n{content}")
        return "\n\n".join(parts)

    def update_system_prompt(self, new_prompt: str):
        """Cập nhật system prompt (ví dụ từ SchemaLoader)."""
        self._system_prompt = new_prompt
