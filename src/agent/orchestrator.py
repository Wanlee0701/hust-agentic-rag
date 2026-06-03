"""
Orchestrator - Agent chính thực hiện ReACT pattern
Sửa lỗi: confidence scoring, source metadata mapping
"""
import logging
import re
from typing import Dict, Any, Optional, List
import yaml

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler

from src.agent.state import AgentState
from src.agent.prompts import get_react_prompt, REACT_SYSTEM_PROMPT
from src.agent.tools import AgentTools, create_agent_tools
from src.embeddings.vector_db import VectorDatabaseManager

logger = logging.getLogger(__name__)


class AgentCallbackHandler(BaseCallbackHandler):
    """Callback để track agent activity"""

    def __init__(self, agent_state: AgentState):
        self.agent_state = agent_state

    def on_tool_start(self, serialized: Dict, input_str: str, **kwargs):
        logger.info(f"🔧 Tool started: {serialized.get('name', 'Unknown')}")

    def on_tool_end(self, output: str, **kwargs):
        logger.info(f"✅ Tool output received ({len(output)} chars)")

    def on_agent_action(self, action, **kwargs):
        logger.info(f"→ Agent action: {action}")


class StudentRegulationAgent:
    """
    Agent chính cho hệ thống trả lời câu hỏi về quy định sinh viên ĐHBK Hà Nội.
    Sử dụng ReACT pattern (Reasoning + Acting).
    """

    def __init__(self, config_path: str = "./config.yaml"):
        """
        Khởi tạo Agent

        Args:
            config_path: Đường dẫn tới file config.yaml
        """
        self.config = self._load_config(config_path)
        self.llm = None
        self.vector_db_manager = None
        self.tools = None
        self._tools_list = []

        self._initialize()

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Đọc file config"""
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            logger.info(f"✅ Config loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"❌ Config file not found: {config_path}")
            raise

    def _initialize(self):
        """Khởi tạo các thành phần của agent"""
        logger.info("🚀 Initializing StudentRegulationAgent...")

        self._initialize_llm()
        self._initialize_vector_db()
        self._initialize_tools()

        logger.info("✅ Agent initialization completed!")

    def _initialize_llm(self):
        """Khởi tạo LLM (Ollama)"""
        llm_config = self.config.get("llm", {})
        try:
            self.llm = OllamaLLM(
                model=llm_config.get("model_name", "mistral"),
                base_url=llm_config.get("base_url", "http://localhost:11434"),
                temperature=llm_config.get("temperature", 0.3),
                timeout=llm_config.get("timeout_seconds", 60),
            )
            logger.info(f"✅ LLM initialized: {llm_config.get('model_name')}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            raise

    def _initialize_vector_db(self):
        """Khởi tạo Vector Database Manager"""
        try:
            from src.embeddings.model import EmbeddingModelManager

            embedding_manager = EmbeddingModelManager(config_path="./config.yaml")
            embeddings = embedding_manager.get_model()

            self.vector_db_manager = VectorDatabaseManager(
                embeddings=embeddings,
                config_path="./config.yaml",
            )
            logger.info("✅ Vector Database initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vector DB: {e}")
            raise

    def _initialize_tools(self):
        """Khởi tạo Tools sử dụng factory function"""
        try:
            self.tools = AgentTools(
                vector_db_manager=self.vector_db_manager,
                config=self.config,
            )
            self._tools_list = self.tools.get_tools_list()
            logger.info(f"✅ Tools initialized: {len(self._tools_list)} tools available")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Tools: {e}")
            raise

    # ------------------------------------------------------------------ #
    # Core: answer_question với ReACT loop                                #
    # ------------------------------------------------------------------ #
    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        Trả lời câu hỏi sử dụng ReACT pattern: Retrieve → Reason → Answer.

        Args:
            question: Câu hỏi từ user

        Returns:
            {
                "answer": str,
                "confidence": float (0-1),
                "success": bool,
                "state": AgentState,
            }
        """
        logger.info(f"📝 Processing: {question}")

        agent_config = self.config.get("agent", {})
        max_iter = agent_config.get("max_iterations", 5)
        conf_threshold = agent_config.get("confidence_threshold", 0.75)

        state = AgentState(query=question, max_iterations=max_iter)

        try:
            # ---- ITERATION 1: Retrieve --------------------------------
            results = self._retrieve_with_fallback(question, state)

            if not results:
                # Không tìm thấy gì — trả lời xin lỗi
                answer = self._generate_no_result_answer(question)
                state.set_answer(answer, confidence=0.1, success=False)
                return {
                    "answer": answer,
                    "confidence": 0.1,
                    "success": False,
                    "state": state,
                }

            # ---- Build context ----------------------------------------
            context = self._build_context(results)

            # Thu thập sources từ metadata đúng field
            for doc, _ in results:
                if hasattr(doc, "metadata"):
                    # Ưu tiên source_file (theo cấu trúc chunks JSON)
                    source = (
                        doc.metadata.get("source_file")
                        or doc.metadata.get("source")
                        or "Không rõ nguồn"
                    )
                    state.add_source(source)

            # ---- ITERATION 2: Generate answer -------------------------
            state.add_iteration(
                thought="Đã tìm được tài liệu liên quan, đang tổng hợp câu trả lời",
                action="GenerateAnswer",
                action_input=question,
                observation=f"Tìm được {len(results)} đoạn tài liệu",
            )

            answer = self._generate_answer(question, context)

            # ---- Calculate real confidence ----------------------------
            confidence = self._calculate_confidence(
                results=results,
                answer=answer,
                iterations=state.iterations,
            )

            state.set_answer(answer, confidence=confidence, success=True)

            logger.info(f"✅ Done — confidence: {confidence:.1%}")
            return {
                "answer": answer,
                "confidence": confidence,
                "success": True,
                "state": state,
            }

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            state.set_error(str(e), confidence=0.0)
            return {
                "answer": f"❌ Lỗi hệ thống: {str(e)}",
                "confidence": 0.0,
                "success": False,
                "state": state,
            }

    def _retrieve_with_fallback(self, question: str, state: AgentState) -> list:
        """
        Retrieve với fallback: nếu lần 1 không đủ kết quả, hạ threshold và thử lại.
        """
        retrieval_cfg = self.config.get("retrieval", {})
        top_k = retrieval_cfg.get("top_k", 3)
        threshold = retrieval_cfg.get("similarity_threshold", 0.5)

        state.add_iteration(
            thought=f"Cần tìm thông tin về: '{question}'",
            action="Retrieve",
            action_input=question,
            observation="Đang tìm kiếm trong Chroma DB...",
        )

        results = self.vector_db_manager.search_similar(
            query=question, k=top_k, score_threshold=threshold
        )

        # Fallback: Hạ threshold nếu không tìm thấy đủ
        if len(results) < 2 and threshold > 0.3:
            logger.info("Fallback: hạ similarity threshold xuống 0.3")
            state.add_iteration(
                thought=f"Kết quả ít ({len(results)}), thử hạ threshold",
                action="Retrieve",
                action_input=f"{question} [threshold=0.3]",
                observation="Mở rộng tìm kiếm...",
            )
            results = self.vector_db_manager.search_similar(
                query=question, k=top_k + 2, score_threshold=0.3
            )

        # Cập nhật observation
        if state.observations:
            state.observations[-1] = f"Tìm được {len(results)} đoạn tài liệu"

        return results

    def _build_context(self, results: list) -> str:
        """Tạo context string từ retrieved documents"""
        parts = []
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)

            source = meta.get("source_file") or meta.get("source") or "Không rõ"
            chapter = meta.get("chapter_title", "")
            article = meta.get("article_title", "")

            part = f"--- Tài liệu {i} (nguồn: {source}, độ liên quan: {score:.1%}) ---"
            if chapter:
                part += f"\nChương: {chapter}"
            if article:
                part += f"\nĐiều: {article}"
            part += f"\nNội dung:\n{content}"
            parts.append(part)

        return "\n\n".join(parts)

    def _generate_answer(self, question: str, context: str) -> str:
        """Gọi LLM sinh câu trả lời từ context"""
        prompt = f"""{REACT_SYSTEM_PROMPT}

Dựa trên các tài liệu sau từ cơ sở dữ liệu quy chế ĐHBK Hà Nội, hãy trả lời câu hỏi bằng tiếng Việt.

=== TÀI LIỆU THAM KHẢO ===
{context}

=== CÂU HỎI ===
{question}

=== YÊU CẦU TRẢ LỜI ===
- Trả lời trực tiếp, rõ ràng, đúng trọng tâm
- Trích dẫn cụ thể số Điều, Chương nếu có trong tài liệu
- Nêu rõ nguồn văn bản (tên file)
- Nếu thông tin không đủ, nêu rõ giới hạn của câu trả lời
- KHÔNG bịa đặt thông tin không có trong tài liệu

=== CÂU TRẢ LỜI ==="""

        try:
            answer = self.llm.invoke(prompt)
            return answer.strip() if isinstance(answer, str) else str(answer).strip()
        except Exception as e:
            logger.error(f"LLM generate error: {e}")
            raise

    def _generate_no_result_answer(self, question: str) -> str:
        """Sinh câu trả lời khi không tìm thấy tài liệu"""
        return (
            f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi: '{question}' "
            f"trong cơ sở dữ liệu quy chế hiện tại.\n\n"
            f"Bạn có thể:\n"
            f"• Thử hỏi lại với từ khóa khác (ví dụ: tên Chương, Điều cụ thể)\n"
            f"• Liên hệ Phòng Đào tạo hoặc Phòng Công tác Sinh viên ĐHBK Hà Nội\n"
            f"• Tra cứu trực tiếp tại: https://hust.edu.vn"
        )

    def _calculate_confidence(
        self, results: list, answer: str, iterations: int
    ) -> float:
        """
        Tính toán độ tin cậy thực sự của câu trả lời.
        Score tổng hợp từ 3 yếu tố độc lập, mỗi yếu tố đóng góp phần riêng.

        Returns:
            float: Confidence score trong [0.0, 1.0]
        """
        score = 0.0

        # Yếu tố 1: Số lượng tài liệu tìm được (tối đa 0.30)
        doc_count = len(results)
        if doc_count >= 3:
            score += 0.30
        elif doc_count == 2:
            score += 0.20
        elif doc_count == 1:
            score += 0.10
        # 0 docs → +0

        # Yếu tố 2: Chất lượng câu trả lời (tối đa 0.40)
        if answer:
            answer_lower = answer.lower()
            # Có số liệu cụ thể
            has_numbers = any(c.isdigit() for c in answer)
            # Có từ khóa pháp lý
            has_legal = any(t in answer for t in [
                "điều", "khoản", "chương", "tín chỉ", "gpa", "cpa",
                "%", "học kỳ", "năm học", "quyết định",
            ])
            # Có trích dẫn nguồn
            has_source = any(t in answer_lower for t in [
                "pdf", "quy chế", "quyết định", "hướng dẫn", "theo điều",
            ])
            # Không thể hiện không biết
            is_negative = any(t in answer_lower for t in [
                "không biết", "không tìm thấy", "không có thông tin",
            ])

            if is_negative:
                score += 0.0
            elif has_numbers and has_legal:
                score += 0.40
            elif has_numbers or has_legal:
                score += 0.25
            elif len(answer) > 100:
                score += 0.15

        # Yếu tố 3: Hiệu quả (ít lần lặp hơn = tốt hơn) (tối đa 0.30)
        if iterations <= 2:
            score += 0.30
        elif iterations <= 3:
            score += 0.20
        elif iterations <= 4:
            score += 0.10
        # >= 5 iterations → +0

        return round(min(max(score, 0.0), 1.0), 2)

    # ------------------------------------------------------------------ #
    # Batch & Utility                                                     #
    # ------------------------------------------------------------------ #
    def batch_answer_questions(self, questions: List[str]) -> List[Dict[str, Any]]:
        """Trả lời nhiều câu hỏi"""
        results = []
        for i, question in enumerate(questions, 1):
            logger.info(f"Processing {i}/{len(questions)}: {question[:50]}")
            results.append(self.answer_question(question))
        return results

    def print_answer_summary(self, result: Dict[str, Any]):
        """In tóm tắt kết quả"""
        state = result.get("state")
        if state:
            state.print_summary()
        else:
            print(
                f"\n📝 Question: {result.get('query', 'N/A')}\n"
                f"📊 Confidence: {result.get('confidence', 0.0):.1%}\n"
                f"✅ Success: {result.get('success', False)}\n"
                f"💬 Answer: {result.get('answer', 'N/A')}"
            )
