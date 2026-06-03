"""
Tools - Các công cụ mà Agent có thể sử dụng
Refactored: @tool decorator phải dùng với standalone function, không phải instance method
"""
import logging
from typing import List, Dict, Any
from langchain.tools import tool

logger = logging.getLogger(__name__)


def create_agent_tools(vector_db_manager, config: Dict[str, Any] = None):
    """
    Factory function tạo danh sách tools cho Agent.
    Dùng closure để truyền vector_db_manager vào các tool functions.

    Args:
        vector_db_manager: VectorDatabaseManager instance
        config: Cấu hình từ config.yaml

    Returns:
        List[BaseTool]: Danh sách tools sẵn sàng dùng với LangChain Agent
    """
    cfg = config or {}
    retrieval_cfg = cfg.get("retrieval", {})
    top_k = retrieval_cfg.get("top_k", 3)
    similarity_threshold = retrieval_cfg.get("similarity_threshold", 0.5)
    llm_cfg = cfg.get("llm", {})

    # ------------------------------------------------------------------ #
    # Tool 1: Retrieve Documents                                           #
    # ------------------------------------------------------------------ #
    @tool
    def retrieve_documents(query: str) -> str:
        """
        Tìm kiếm tài liệu liên quan từ cơ sở dữ liệu vector (Chroma DB).
        Sử dụng khi cần tra cứu thông tin về quy định, chính sách sinh viên ĐHBK Hà Nội.

        Args:
            query: Câu hỏi hoặc từ khóa cần tìm kiếm

        Returns:
            Các đoạn tài liệu liên quan kèm metadata nguồn gốc
        """
        try:
            results = vector_db_manager.search_similar(
                query=query,
                k=top_k,
                score_threshold=similarity_threshold,
            )

            if not results:
                return (
                    "❌ Không tìm thấy tài liệu phù hợp. "
                    "Hãy thử viết lại câu hỏi với từ khóa cụ thể hơn."
                )

            formatted = f"✅ Tìm thấy {len(results)} đoạn tài liệu liên quan:\n\n"
            for i, (doc, score) in enumerate(results, 1):
                meta = doc.metadata if hasattr(doc, "metadata") else {}
                content = doc.page_content if hasattr(doc, "page_content") else str(doc)

                # Ưu tiên source_file, fallback sang source
                source = meta.get("source_file") or meta.get("source") or "Không rõ nguồn"
                chapter = meta.get("chapter_title", "")
                article = meta.get("article_title", "")
                doc_type = meta.get("doc_type", "")
                is_table = meta.get("is_table", False)

                formatted += f"📄 [{i}] Nguồn: {source}"
                if doc_type:
                    formatted += f" ({doc_type})"
                formatted += f"\n    Độ liên quan: {score:.1%}\n"
                if chapter:
                    formatted += f"    Chương: {chapter[:80]}\n"
                if article:
                    formatted += f"    Điều: {article[:80]}\n"
                if is_table:
                    formatted += "    [Đây là bảng biểu]\n"
                formatted += f"    Nội dung: {content[:400]}\n\n"

            logger.info(f"Retrieved {len(results)} docs for: {query[:50]}")
            return formatted

        except Exception as e:
            logger.error(f"retrieve_documents error: {e}")
            return f"❌ Lỗi khi tìm kiếm: {str(e)}"

    # ------------------------------------------------------------------ #
    # Tool 2: Refine Query (dùng LLM sinh query alternatives)              #
    # ------------------------------------------------------------------ #
    @tool
    def refine_query(original_query: str) -> str:
        """
        Viết lại câu hỏi thành 3 cách diễn đạt khác nhau để cải thiện kết quả tìm kiếm.
        Sử dụng khi kết quả retrieve lần đầu không đủ tốt hoặc không tìm thấy gì.

        Args:
            original_query: Câu hỏi gốc cần viết lại

        Returns:
            3 câu hỏi thay thế để dùng thay cho retrieve_documents
        """
        try:
            from langchain_ollama import OllamaLLM

            llm = OllamaLLM(
                model=llm_cfg.get("model_name", "mistral"),
                base_url=llm_cfg.get("base_url", "http://localhost:11434"),
                temperature=0.5,
                timeout=20,
            )

            prompt = f"""Bạn là chuyên gia về quy chế đào tạo Đại học Bách khoa Hà Nội (HUST).

Câu hỏi gốc: "{original_query}"

Hãy tạo 3 cách diễn đạt khác nhau để tìm kiếm thông tin này trong cơ sở dữ liệu văn bản quy chế.
Mỗi cách phải dùng từ khóa/thuật ngữ khác nhau.

Trả lời theo định dạng:
1. [câu hỏi cách 1]
2. [câu hỏi cách 2]  
3. [câu hỏi cách 3]"""

            response = llm.invoke(prompt)
            logger.info(f"Query refined for: {original_query[:50]}")
            return f"🔄 Các cách diễn đạt thay thế:\n{response}"

        except Exception as e:
            logger.warning(f"refine_query LLM failed ({e}), dùng heuristic fallback")
            # Fallback heuristic nếu LLM lỗi
            alternatives = [
                f"Quy định về: {original_query}",
                f"Điều khoản liên quan đến: {original_query}",
                f"Chính sách sinh viên ĐHBK: {original_query}",
            ]
            return "🔄 Các cách diễn đạt thay thế:\n" + "\n".join(
                f"{i+1}. {a}" for i, a in enumerate(alternatives)
            )

    # ------------------------------------------------------------------ #
    # Tool 3: Verify Answer Quality                                        #
    # ------------------------------------------------------------------ #
    @tool
    def verify_answer(answer: str) -> str:
        """
        Kiểm tra xem câu trả lời đã đủ chất lượng để trả cho người dùng chưa.
        Sử dụng sau khi đã có câu trả lời để xác nhận trước khi kết thúc.

        Args:
            answer: Câu trả lời cần kiểm tra

        Returns:
            Đánh giá về chất lượng câu trả lời (sufficient/insufficient + lý do)
        """
        try:
            issues = []
            score = 0.0

            # Tiêu chí 1: Độ dài hợp lý (≥ 80 ký tự)
            if len(answer) >= 80:
                score += 0.4
            elif len(answer) >= 30:
                score += 0.2
                issues.append("Câu trả lời khá ngắn")
            else:
                issues.append("Câu trả lời quá ngắn (< 30 ký tự)")

            # Tiêu chí 2: Không thể hiện không biết
            negative_kw = ["không biết", "không tìm thấy", "không có thông tin",
                           "tôi không", "i don't know", "không rõ"]
            if any(kw in answer.lower() for kw in negative_kw):
                issues.append("Câu trả lời thể hiện thiếu thông tin")
            else:
                score += 0.3

            # Tiêu chí 3: Có số liệu / điều khoản cụ thể
            has_numbers = any(c.isdigit() for c in answer)
            has_legal_terms = any(t in answer for t in ["Điều", "Khoản", "điều", "tín chỉ", "%", "GPA", "CPA"])
            if has_numbers or has_legal_terms:
                score += 0.3
            else:
                issues.append("Thiếu số liệu/điều khoản cụ thể")

            score = min(score, 1.0)
            sufficient = score >= 0.6

            result = f"{'✅ ĐỦ CHẤT LƯỢNG' if sufficient else '⚠️ CẦN CẢI THIỆN'}\n"
            result += f"Điểm đánh giá: {score:.0%}\n"
            if issues:
                result += f"Vấn đề: {'; '.join(issues)}\n"
            if not sufficient:
                result += "→ Nên thử retrieve thêm tài liệu hoặc dùng refine_query."

            logger.info(f"Answer verified: score={score:.0%}, sufficient={sufficient}")
            return result

        except Exception as e:
            logger.error(f"verify_answer error: {e}")
            return f"❌ Lỗi khi kiểm tra: {str(e)}"

    return [retrieve_documents, refine_query, verify_answer]


# ------------------------------------------------------------------ #
# Backward-compatible class wrapper (giữ lại API cũ)                  #
# ------------------------------------------------------------------ #
class AgentTools:
    """Wrapper class để tương thích với code cũ"""

    def __init__(self, vector_db_manager=None, config: Dict[str, Any] = None):
        self.vector_db_manager = vector_db_manager
        self.config = config or {}
        self._tools = create_agent_tools(vector_db_manager, config)

    def get_tools_list(self) -> List:
        """Trả về danh sách tools"""
        return self._tools


class ToolRegistry:
    """Quản lý đăng ký và sử dụng tools"""

    def __init__(self):
        self.tools = {}

    def register(self, name: str, tool_func):
        self.tools[name] = tool_func

    def get_tool(self, name: str):
        return self.tools.get(name)

    def get_all_tools(self) -> List:
        return list(self.tools.values())

    def list_tools(self) -> List[str]:
        return list(self.tools.keys())
