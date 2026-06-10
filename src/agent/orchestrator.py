"""
Orchestrator - Agent chính thực hiện ReACT pattern (Multi-hop)
Cải tiến:
  - Vòng lặp Evaluate → QueryRewrite → Retrieve thực sự
  - Hỗ trợ Ollama và Google Gemini
  - Trả về retrieved_chunks để UI hiển thị văn bản gốc
  - [v3] Hybrid Intent Classification (YAML + LLM)
  - [v3] Conversation Memory (Sliding Window)
"""
import json
import logging
import os
import re
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from src.agent.state import AgentState
from src.agent.prompts import REACT_SYSTEM_PROMPT, QUERY_REFINEMENT_PROMPT
from src.agent.intent_classifier import IntentClassifier
from src.agent.memory_manager import get_memory
from src.embeddings.vector_db import VectorDatabaseManager

logger = logging.getLogger(__name__)


# ================================================================== #
#  LLM Factory                                                        #
# ================================================================== #

def _build_llm(llm_config: Dict[str, Any]):
    """
    Khởi tạo LLM dựa theo provider trong config.
    Hỗ trợ: 'ollama' | 'gemini'
    """
    provider = llm_config.get("provider", "ollama").lower()

    if provider == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError:
            raise ImportError(
                "Cần cài thêm gói: pip install langchain-google-genai"
            )

        # Lấy API key từ env hoặc từ config
        api_key_env = llm_config.get("api_key_env", "GEMINI_API_KEY")
        api_key = os.environ.get(api_key_env) or llm_config.get("api_key", "")
        if not api_key:
            raise ValueError(
                f"Không tìm thấy Gemini API key. "
                f"Hãy set biến môi trường '{api_key_env}' hoặc thêm 'api_key' vào config.yaml"
            )

        llm = ChatGoogleGenerativeAI(
            model=llm_config.get("model_name", "gemini-2.5-flash"),
            google_api_key=api_key,
            temperature=llm_config.get("temperature", 0.3),
            max_output_tokens=llm_config.get("max_tokens", 2048)
        )
        logger.info(f"✅ LLM (Gemini) initialized: {llm_config.get('model_name')}")
        return llm, provider

    else:  # default: ollama
        try:
            from langchain_ollama import OllamaLLM
        except ImportError:
            raise ImportError("Cần cài: pip install langchain-ollama")

        llm = OllamaLLM(
            model=llm_config.get("model_name", "mistral"),
            base_url=llm_config.get("base_url", "http://localhost:11434"),
            temperature=llm_config.get("temperature", 0.3),
            timeout=llm_config.get("timeout_seconds", 120),
        )
        logger.info(f"✅ LLM (Ollama) initialized: {llm_config.get('model_name')}")
        return llm, provider


def _invoke_llm(llm, provider: str, prompt: str) -> str:
    """Gọi LLM và trả về plain text, tương thích cả Ollama lẫn Gemini."""
    if provider == "gemini":
        # Streamlit chạy các component trên các luồng con không có asyncio loop.
        # SDK google-genai mới (v2) sử dụng httpx async bên dưới và sẽ gây deadlock.
        # Giải pháp: Ép tạo và sử dụng một event loop cụ thể cho luồng này.
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
    response = llm.invoke(prompt)
    # Gemini trả về AIMessage, Ollama trả về str
    if hasattr(response, "content"):
        return response.content.strip()
    return str(response).strip()


# ================================================================== #
#  Prompts nội bộ                                                     #
# ================================================================== #

# [FIX v2] Đổi tiêu chí: chỉ hỏi "có LIÊN QUAN không?"
# Không hỏi "đã đủ để trả lời hoàn hảo chưa?" vì LLM sẽ luôn trả false.
_EVALUATE_PROMPT = """\
Bạn là trợ lý AI về quy chế đào tạo ĐHBK Hà Nội.

Câu hỏi của sinh viên: "{question}"

Dưới đây là các đoạn tài liệu tìm được:
{context}

Nhiệm vụ: Đánh giá xem tài liệu trên có ĐỀ CẬP đến chủ đề câu hỏi hay không.
Lưu ý quan trọng:
- Tài liệu KHÔNG cần trả lời hoàn chỉnh 100%.
- Chỉ cần tài liệu có chứa thông tin liên quan đến chủ đề câu hỏi là ĐỦ (relevant=true).
- Chỉ trả về relevant=false nếu tài liệu hoàn toàn nói về chủ đề khác, không liên quan gì.

Trả về JSON duy nhất (KHÔNG giải thích thêm bên ngoài JSON):
{{"relevant": true/false, "reason": "Lý do ngắn gọn"}}"""

# _INTENT_CHECK_PROMPT đã được xóa (dead code — thay thế bởi IntentClassifier v3)

_REWRITE_PROMPT = """\
Bạn là chuyên gia về quy chế đào tạo ĐHBK Hà Nội.

Câu hỏi gốc của sinh viên: "{question}"
Lý do tìm kiếm chưa đủ: "{reason}"

Hãy viết lại câu hỏi dưới 1 cách diễn đạt khác, dùng thuật ngữ pháp lý/học thuật chính xác hơn để tìm trong văn bản quy chế.
Chỉ trả về 1 câu duy nhất, KHÔNG giải thích.

Ví dụ:
- Gốc: "trượt 14 tín" → Viết lại: "cảnh cáo học tập tín chỉ nợ không đạt yêu cầu"
- Gốc: "bị đuổi học vì học kém" → Viết lại: "xử lý học vụ buộc thôi học do điểm trung bình tích lũy thấp"

Câu viết lại:"""

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


# ================================================================== #
#  Agent                                                              #
# ================================================================== #

class StudentRegulationAgent:
    """
    AgenticRAG v4 — Luồng thống nhất:
      [Intent Gate] → Retrieve → [Avg-Sim Check / QueryRewrite] → GenerateAnswer → [Confidence Gate]
    """

    MAX_RETRIEVAL_HOPS = 2

    # Confidence Gate (đọc từ config, giá trị mặc định dùng khi không có config)
    _HIGH_CONF_DEFAULT = 0.65   # ≥ high → trả lời bình thường
    _LOW_CONF_DEFAULT  = 0.35   # < low  → từ chối (không đủ thông tin)
    _MIN_AVG_SIM_DEFAULT = 0.45  # avg similarity để skip rewrite ở hop 1

    def __init__(self, config_path: str = "./config.yaml"):
        self.config = self._load_config(config_path)
        self.llm = None
        self._provider = "ollama"
        self.vector_db_manager = None
        self.intent_classifier: Optional[IntentClassifier] = None
        self.memory = None
        self._initialize()

    # -------------------------------------------------------------- #
    #  Khởi tạo                                                       #
    # -------------------------------------------------------------- #

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        logger.info(f"✅ Config loaded from {config_path}")
        return config

    def _initialize(self):
        logger.info("🚀 Initializing StudentRegulationAgent...")
        llm_config = self.config.get("llm", {})
        self.llm, self._provider = _build_llm(llm_config)
        self._initialize_vector_db()
        self._initialize_intent_classifier()
        self._initialize_memory()
        logger.info("✅ Agent ready.")

    def _initialize_vector_db(self):
        from src.embeddings.model import EmbeddingModelManager
        embedding_manager = EmbeddingModelManager(config_path="./config.yaml")
        embeddings = embedding_manager.get_model()
        self.vector_db_manager = VectorDatabaseManager(
            embeddings=embeddings,
            config_path="./config.yaml",
        )
        logger.info("✅ Vector Database initialized")

    def _initialize_intent_classifier(self):
        """Khởi tạo IntentClassifier với YAML config và LLM invoker."""
        intent_config = self.config.get("intents", {})
        if not intent_config:
            logger.warning(
                "[Orchestrator] Không tìm thấy section 'intents' trong config.yaml. "
                "IntentClassifier sẽ không hoạt động."
            )
            self.intent_classifier = None
            return

        def llm_invoker(prompt: str) -> str:
            return _invoke_llm(self.llm, self._provider, prompt)

        self.intent_classifier = IntentClassifier(
            intent_config=intent_config,
            llm_invoker=llm_invoker,
        )
        logger.info("✅ IntentClassifier initialized")

    def _initialize_memory(self):
        """Khởi tạo ConversationMemory từ cấu hình."""
        mem_cfg = self.config.get("memory", {})
        if not mem_cfg.get("enabled", True):
            logger.info("[Orchestrator] Memory bị tắt trong config.")
            self.memory = None
            return
        self.memory = get_memory(
            window_size=mem_cfg.get("window_size", 5),
            max_context_chars=mem_cfg.get("max_context_chars", 1500),
        )
        logger.info("✅ ConversationMemory initialized")


    # -------------------------------------------------------------- #
    #  Public API                                                     #
    # -------------------------------------------------------------- #

    def answer_question(
        self,
        question: str,
        session_id: str = "default",
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Trả lời câu hỏi qua vòng lặp ReACT Multi-hop.
        [v3] Bước 0: Hybrid Intent Classification (YAML + LLM + Memory).

        Args:
            question: Câu hỏi của người dùng.
            session_id: ID phiên làm việc (dùng để quản lý memory).
            status_callback: Hàm callback để cập nhật trạng thái UI.

        Returns dict:
          answer, confidence, success, state, retrieved_chunks,
          needs_clarification, clarification_question, intent_name, entities
        """
        def notify(msg: str):
            logger.info(msg)
            if status_callback:
                status_callback(msg)

        logger.info(f"📝 Processing (session='{session_id}'): {question}")

        # ============================================================
        # BƯỚC 0: HYBRID INTENT CLASSIFICATION
        # LLM bóc tách intent + entities, YAML kiểm tra required_fields,
        # Memory bổ sung entity từ lịch sử hội thoại.
        # ============================================================
        notify("🔎 Đang phân loại câu hỏi...")

        intent_result = None
        if self.intent_classifier:
            # Lấy ngữ cảnh và entity từ memory
            memory_context = self.memory.get_context(session_id) if self.memory else ""
            memory_entities = self.memory.get_entities_from_memory(session_id) if self.memory else {}
            
            # [NEW] Lấy previous_intent nếu turn trước cần clarification
            previous_intent = None
            if self.memory:
                previous_intent = self.memory.get_last_clarification_intent(session_id)

            intent_result = self.intent_classifier.classify(
                question=question,
                memory_context=memory_context,
                memory_entities=memory_entities,
                previous_intent=previous_intent,  # ← Pass hint
            )

            if intent_result.needs_clarification:
                logger.info(
                    f"❓ Intent='{intent_result.intent_name}' | "
                    f"Missing: {intent_result.missing_fields} | Clarification triggered."
                )
                state = AgentState(query=question, max_iterations=1)
                state.add_iteration(
                    thought=f"Intent '{intent_result.intent_name}' cần entity: {intent_result.missing_fields}",
                    action="Clarify",
                    action_input=question,
                    observation=f"Thiếu: {intent_result.missing_fields}",
                )
                
                # [NEW] Lưu clarification state vào memory (thêm turn nhưng với answer = clarification_question)
                if self.memory:
                    self.memory.add_turn(
                        session_id=session_id,
                        question=question,
                        answer=intent_result.clarification_question,
                        entities=intent_result.entities,
                        intent_name=intent_result.intent_name,
                        needs_clarification=True,  # ← Flag: turn này cần clarification
                    )
                
                return {
                    "answer": intent_result.clarification_question,
                    "confidence": 0.0,
                    "success": False,
                    "needs_clarification": True,
                    "clarification_question": intent_result.clarification_question,
                    "intent_name": intent_result.intent_name,
                    "entities": intent_result.entities,
                    "state": state,
                    "retrieved_chunks": [],
                }
            else:
                logger.info(
                    f"✅ Intent='{intent_result.intent_name}' | "
                    f"Entities={intent_result.entities} | Pass to RAG."
                )

        agent_config = self.config.get("agent", {})
        max_iter = agent_config.get("max_iterations", 5)
        state = AgentState(query=question, max_iterations=max_iter)

        # Đọc threshold từ config (hoặc dùng giá trị mặc định)
        high_conf = agent_config.get("high_confidence_threshold", self._HIGH_CONF_DEFAULT)
        low_conf  = agent_config.get("low_confidence_threshold",  self._LOW_CONF_DEFAULT)
        min_avg_sim = agent_config.get("min_avg_similarity", self._MIN_AVG_SIM_DEFAULT)

        retrieval_cfg = self.config.get("retrieval", {})
        top_k = retrieval_cfg.get("top_k", 3)
        threshold = retrieval_cfg.get("similarity_threshold", 0.35)

        current_query = question
        all_results: List[Tuple] = []

        try:
            # ============================================================
            # VÒNG LẶP: Retrieve → Evaluate → (QueryRewrite → Retrieve)*
            # ============================================================
            for hop in range(self.MAX_RETRIEVAL_HOPS):
                notify(f"🔍 [{hop + 1}/{self.MAX_RETRIEVAL_HOPS}] Đang tìm kiếm: \"{current_query[:60]}\"")

                results = self._retrieve(current_query, top_k, threshold)

                # Nếu quá ít → fallback threshold
                if len(results) < 2 and threshold > 0.25:
                    notify(f"⚠️ Chỉ tìm được {len(results)} đoạn, mở rộng phạm vi tìm kiếm...")
                    results = self._retrieve(current_query, top_k + 2, 0.25)

                state.add_iteration(
                    thought=f"Tìm kiếm lần {hop + 1} với query: '{current_query}'",
                    action="Retrieve",
                    action_input=current_query,
                    observation=f"Tìm được {len(results)} đoạn tài liệu",
                )

                # Merge kết quả (dedup theo content)
                existing_contents = {doc.page_content for doc, _ in all_results}
                for doc, score in results:
                    if doc.page_content not in existing_contents:
                        all_results.append((doc, score))
                        existing_contents.add(doc.page_content)

                if not all_results:
                    logger.warning("⚠️ Không tìm thấy tài liệu liên quan.")
                    break

                # ============================================================
                # [FIX v4 — CRITICAL] AVG-SIMILARITY CHECK
                # Thay thế logic cũ "hop 1 skip evaluate nếu ≥ 2 docs".
                # Kiểm tra chất lượng docs bằng avg cosine similarity.
                # Docs tốt (avg ≥ min_avg_sim) → thoát vòng lặp, generate.
                # Docs kém → tiếp tục sang Evaluate + QueryRewrite.
                # ============================================================
                recent_scores = [score for _, score in results[:top_k] if results]
                avg_sim = sum(recent_scores) / max(len(recent_scores), 1)

                logger.info(
                    f"[Hop {hop+1}] Docs: {len(all_results)}, "
                    f"avg_similarity: {avg_sim:.3f} (ngưỡng: {min_avg_sim:.2f})"
                )

                if avg_sim >= min_avg_sim:
                    state.add_iteration(
                        thought=f"Hop {hop+1}: avg_similarity={avg_sim:.2f} ≥ {min_avg_sim} — docs đủ chất lượng",
                        action="Evaluate",
                        action_input=f"avg_sim={avg_sim:.3f}",
                        observation=f"Docs tốt ({len(all_results)} đoạn, avg_sim={avg_sim:.2f}) → generate",
                    )
                    logger.info(f"✅ Hop {hop+1}: avg_sim={avg_sim:.2f} đạt ngưỡng, proceed to generate.")
                    break

                # Avg similarity thấp — chạy LLM Evaluate để xác nhận
                notify(f"🧐 Đang đánh giá mức độ liên quan của tài liệu...")
                context_for_eval = self._build_context(all_results[:top_k])
                is_relevant, eval_reason = self._evaluate_context(question, context_for_eval)

                state.add_iteration(
                    thought=f"Hop {hop+1}: avg_sim={avg_sim:.2f} thấp, cần LLM evaluate",
                    action="Evaluate",
                    action_input=context_for_eval[:100] + "...",
                    observation=f"Liên quan: {is_relevant} | Lý do: {eval_reason}",
                )

                if is_relevant:
                    logger.info(f"✅ LLM xác nhận tài liệu liên quan sau hop {hop+1}. Generate.")
                    break

                # ---- QUERY REWRITE ----
                if hop < self.MAX_RETRIEVAL_HOPS - 1:
                    notify(f"✏️ Tài liệu chưa liên quan, đang viết lại câu hỏi...")
                    rewritten = self._rewrite_query(question, eval_reason)
                    if rewritten and rewritten != current_query:
                        current_query = rewritten
                        state.add_iteration(
                            thought=f"Query rewrite: '{rewritten}'",
                            action="QueryRewrite",
                            action_input=question,
                            observation=f"Query mới: {rewritten}",
                        )
                    else:
                        logger.info("Query rewrite không tạo ra query mới. Dừng tìm kiếm.")
                        break

            # ============================================================
            # GENERATE ANSWER
            # ============================================================
            if not all_results:
                answer = self._no_result_answer(question)
                state.set_answer(answer, confidence=0.1, success=False)
                return self._build_result(answer, 0.1, False, state, [])

            # Thu thập sources
            for doc, _ in all_results:
                if hasattr(doc, "metadata"):
                    source = (
                        doc.metadata.get("source_file")
                        or doc.metadata.get("source")
                        or "Không rõ nguồn"
                    )
                    state.add_source(source)

            notify("🧠 Đang tổng hợp câu trả lời...")
            context = self._build_context(all_results)
            state.add_iteration(
                thought="Đã có đủ tài liệu, tổng hợp câu trả lời",
                action="GenerateAnswer",
                action_input=question,
                observation=f"Context từ {len(all_results)} đoạn",
            )

            raw_answer = self._generate_answer(question, context)
            confidence = self._calculate_confidence(all_results, raw_answer, state.iterations)

            logger.info(
                f"[ConfidenceGate] confidence={confidence:.1%} | "
                f"high={high_conf:.0%}, low={low_conf:.0%}"
            )

            # ============================================================
            # [FIX v4 — CRITICAL] CONFIDENCE GATE
            # Dùng confidence score để QUYẾT ĐỊNH cách trả lời.
            # Trước đây: chỉ tính rồi hiển thị, không filter.
            # Bây giờ: gate cứng theo 3 mức.
            # ============================================================
            if confidence < low_conf:
                # Dưới ngưỡng tối thiểu → từ chối, trả về thông báo không tìm thấy
                logger.warning(
                    f"[ConfidenceGate] {confidence:.1%} < low_threshold {low_conf:.0%} — reject answer."
                )
                answer = self._no_result_answer(question)
                state.set_answer(answer, confidence=confidence, success=False)
                notify(f"⚠️ Độ tin cậy thấp ({confidence:.0%}), không đủ thông tin để trả lời.")
            elif confidence < high_conf:
                # Vùng trung gian → trả lời kèm cảnh báo
                logger.info(
                    f"[ConfidenceGate] {confidence:.1%} trong vùng trung gian — answer with warning."
                )
                answer = (
                    raw_answer
                    + f"\n\n---\n⚠️ *Lưu ý: Độ tin cậy của câu trả lời này ở mức trung bình "
                    f"({confidence:.0%}). Vui lòng kiểm tra lại với tài liệu gốc hoặc liên hệ "
                    f"Phòng Đào tạo để xác nhận.*"
                )
                state.set_answer(answer, confidence=confidence, success=True)
            else:
                # Đủ ngưỡng → trả lời bình thường
                answer = raw_answer
                state.set_answer(answer, confidence=confidence, success=True)

            logger.info(f"✅ Done — confidence: {confidence:.1%}, hops: {state.iterations}")

            # Lưu turn vào memory (bao gồm entity đã bóc tách)
            if self.memory:
                entities_to_save = intent_result.entities if intent_result else {}
                self.memory.add_turn(
                    session_id=session_id,
                    question=question,
                    answer=answer[:500],
                    entities=entities_to_save,
                    intent_name=intent_result.intent_name if intent_result else "",
                    needs_clarification=False,
                )
                logger.debug(
                    f"[Memory] Saved turn for session '{session_id}'. "
                    f"Total turns: {self.memory.get_turn_count(session_id)}"
                )

            # Chuẩn bị chunks để UI hiển thị
            retrieved_chunks = self._format_chunks_for_ui(all_results)
            result = self._build_result(answer, confidence, state.success, state, retrieved_chunks)
            result["intent_name"] = intent_result.intent_name if intent_result else "UNKNOWN"
            result["entities"] = intent_result.entities if intent_result else {}
            result["needs_clarification"] = False
            return result


        except Exception as e:
            logger.error(f"❌ Agent error: {e}", exc_info=True)
            state.set_error(str(e), confidence=0.0)
            return self._build_result(f"❌ Lỗi hệ thống: {e}", 0.0, False, state, [])

    # -------------------------------------------------------------- #
    #  Retrieve                                                       #
    # -------------------------------------------------------------- #

    def _retrieve(self, query: str, k: int, threshold: float) -> list:
        """Gọi ChromaDB similarity search."""
        return self.vector_db_manager.search_similar(
            query=query, k=k, score_threshold=threshold
        )

    # -------------------------------------------------------------- #
    #  Evaluate context                                               #
    # -------------------------------------------------------------- #

    def _evaluate_context(self, question: str, context: str) -> Tuple[bool, str]:
        """
        [FIX v2] Kiểm tra tài liệu có LIÊN QUAN đến chủ đề câu hỏi không.
        Không đánh giá "hoàn hảo" mà chỉ đánh giá "có liên quan".
        Returns: (is_relevant, reason)
        """
        prompt = _EVALUATE_PROMPT.format(question=question, context=context[:2000])
        raw = ""
        try:
            raw = _invoke_llm(self.llm, self._provider, prompt)
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group())
                # [FIX] Đọc key 'relevant' (mới), fallback sang 'sufficient' (cũ)
                is_relevant = bool(data.get("relevant", data.get("sufficient", True)))
                return is_relevant, data.get("reason", "")
        except Exception as e:
            logger.warning(f"Evaluate parse error: {e}. Raw: {raw[:200]}")
        # Fallback: nếu parse thất bại → coi như liên quan để tránh vòng lặp
        return True, "Không parse được kết quả đánh giá"

    # _check_intent() đã xóa (dead code — thay thế bởi IntentClassifier.classify() từ v3)

    # -------------------------------------------------------------- #
    #  Query Rewrite                                                  #
    # -------------------------------------------------------------- #

    def _rewrite_query(self, original_question: str, reason: str) -> str:
        """Yêu cầu LLM viết lại câu hỏi với thuật ngữ học thuật hơn."""
        prompt = _REWRITE_PROMPT.format(question=original_question, reason=reason)
        try:
            rewritten = _invoke_llm(self.llm, self._provider, prompt).strip()
            rewritten = rewritten.strip('"\'')  # Xóa dấu ngoặc kép nếu có
            logger.info(f"✏️ Query rewritten: '{original_question}' → '{rewritten}'")
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewrite failed: {e}")
            return original_question

    # -------------------------------------------------------------- #
    #  Build Context                                                   #
    # -------------------------------------------------------------- #

    def _build_context(self, results: list) -> str:
        parts = []
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            content = doc.page_content if hasattr(doc, "page_content") else str(doc)
            source = meta.get("source_file") or meta.get("source") or "Không rõ"
            chapter = meta.get("chapter_title", "")
            article = meta.get("article_title", "")

            header = f"--- Đoạn {i} | Nguồn: {source} | Độ liên quan: {score:.1%} ---"
            if chapter:
                header += f"\nChương: {chapter}"
            if article:
                header += f"\nĐiều: {article}"
            parts.append(f"{header}\n{content}")
        return "\n\n".join(parts)

    # -------------------------------------------------------------- #
    #  Generate Answer                                                 #
    # -------------------------------------------------------------- #

    def _generate_answer(self, question: str, context: str) -> str:
        prompt = _ANSWER_PROMPT.format(
            system_prompt=REACT_SYSTEM_PROMPT,
            context=context,
            question=question,
        )
        return _invoke_llm(self.llm, self._provider, prompt)

    def _no_result_answer(self, question: str) -> str:
        return (
            f"Xin lỗi, tôi không tìm thấy thông tin liên quan đến câu hỏi: **'{question}'** "
            f"trong cơ sở dữ liệu quy chế hiện tại.\n\n"
            f"Bạn có thể:\n"
            f"• Thử hỏi lại với từ khóa khác (ví dụ: tên Chương, Điều cụ thể)\n"
            f"• Liên hệ Phòng Đào tạo hoặc Phòng Công tác Sinh viên ĐHBK Hà Nội\n"
            f"• Tra cứu trực tiếp: https://hust.edu.vn"
        )

    # -------------------------------------------------------------- #
    #  Confidence                                                     #
    # -------------------------------------------------------------- #

    def _calculate_confidence(self, results: list, answer: str, iterations: int) -> float:
        score = 0.0

        # Yếu tố 1: Số lượng docs (tối đa 0.30)
        doc_count = len(results)
        score += min(doc_count / 5, 1.0) * 0.30

        # Yếu tố 2: Chất lượng câu trả lời (tối đa 0.40)
        if answer:
            answer_lower = answer.lower()
            has_numbers = any(c.isdigit() for c in answer)
            has_legal = any(t in answer_lower for t in [
                "điều", "khoản", "chương", "tín chỉ", "gpa", "cpa",
                "%", "học kỳ", "năm học", "quyết định",
            ])
            is_negative = any(t in answer_lower for t in [
                "không biết", "không tìm thấy", "không có thông tin", "xin lỗi",
            ])
            if is_negative:
                score += 0.0
            elif has_numbers and has_legal:
                score += 0.40
            elif has_numbers or has_legal:
                score += 0.25
            elif len(answer) > 100:
                score += 0.15

        # Yếu tố 3: Hiệu quả (tối đa 0.30) - ít hop hơn = tốt hơn
        if iterations <= 2:
            score += 0.30
        elif iterations <= 4:
            score += 0.20
        elif iterations <= 6:
            score += 0.10

        return round(min(max(score, 0.0), 1.0), 2)

    # -------------------------------------------------------------- #
    #  Format chunks cho UI                                           #
    # -------------------------------------------------------------- #

    def _format_chunks_for_ui(self, results: list) -> List[Dict[str, Any]]:
        """Chuẩn bị dữ liệu chunk để hiển thị raw text trên giao diện."""
        chunks = []
        for i, (doc, score) in enumerate(results, 1):
            meta = doc.metadata if hasattr(doc, "metadata") else {}
            chunks.append({
                "index": i,
                "content": doc.page_content if hasattr(doc, "page_content") else str(doc),
                "score": score,
                "source": meta.get("source_file") or meta.get("source") or "Không rõ",
                "chapter": meta.get("chapter_title", ""),
                "article": meta.get("article_title", ""),
            })
        return chunks

    # -------------------------------------------------------------- #
    #  Build result dict                                              #
    # -------------------------------------------------------------- #

    def _build_result(
        self,
        answer: str,
        confidence: float,
        success: bool,
        state: AgentState,
        retrieved_chunks: list,
    ) -> Dict[str, Any]:
        return {
            "answer": answer,
            "confidence": confidence,
            "success": success,
            "state": state,
            "retrieved_chunks": retrieved_chunks,
        }

    # -------------------------------------------------------------- #
    #  Batch utility                                                  #
    # -------------------------------------------------------------- #

    def batch_answer_questions(self, questions: List[str]) -> List[Dict[str, Any]]:
        return [self.answer_question(q) for q in questions]
