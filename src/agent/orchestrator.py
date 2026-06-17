"""
Orchestrator — Agent chính thực hiện ReACT pattern (Tool-Based).

Refactored v6:
  - Agent gọi Tools qua BaseTool interface thay vì hardcode logic.
  - Preprocessing (Intent/Schema) tách ra src/pipeline/.
  - Memory tách ra src/memory/.
  - Confidence Gate tách ra src/pipeline/confidence_gate.py.

Luồng:
  [Pipeline] IntentClassifier → needs_clarification?
      ↓ NO
  [Agent] for hop in MAX_HOPS:
      Tool: RetrieveTool.execute()
      Tool: EvaluateTool.execute()
      Tool: RewriteTool.execute() (nếu cần)
  Tool: GenerateTool.execute()
      ↓
  [Pipeline] ConfidenceGate.evaluate()
  [Memory] save_turn()
"""
import logging
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import yaml

from src.agent.state import AgentState
from src.agent.prompts import REACT_SYSTEM_PROMPT
from src.agent.tools import RetrieveTool, EvaluateTool, RewriteTool, GenerateTool
from src.pipeline.intent_classifier import IntentClassifier
from src.pipeline.schema_loader import SchemaLoader
from src.pipeline.confidence_gate import ConfidenceGate
from src.memory.memory_manager import get_memory

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
#  Agent                                                              #
# ================================================================== #

class StudentRegulationAgent:
    """
    AgenticRAG v6 — Tool-Based Orchestrator:
      [Pipeline] IntentClassifier → [Agent] Tools Loop → [Pipeline] ConfidenceGate
    
    Tools:
      1. RetrieveTool   — Tìm kiếm tài liệu từ ChromaDB
      2. EvaluateTool   — Đánh giá mức độ liên quan (avg-sim + LLM)
      3. RewriteTool    — Viết lại câu hỏi khi cần
      4. GenerateTool   — Tổng hợp câu trả lời từ context
    """

    MAX_RETRIEVAL_HOPS = 2

    def __init__(self, config_path: str = "./config.yaml"):
        self.config = self._load_config(config_path)
        self.llm = None
        self._provider = "ollama"
        self.vector_db_manager = None
        self.intent_classifier: Optional[IntentClassifier] = None
        self.memory = None
        self.confidence_gate: Optional[ConfidenceGate] = None
        self._schema_loader: Optional[SchemaLoader] = None
        self._system_prompt: str = REACT_SYSTEM_PROMPT
        self._tools: Dict[str, Any] = {}
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
        logger.info("🚀 Initializing StudentRegulationAgent (v6 — Tool-Based)...")

        # 1. LLM
        llm_config = self.config.get("llm", {})
        self.llm, self._provider = _build_llm(llm_config)

        # 2. Vector DB
        self._initialize_vector_db()

        # 3. Schema Loader → System Prompt
        self._initialize_schema_loader()

        # 4. Tools — phụ thuộc vào LLM, VectorDB, System Prompt
        self._register_tools()

        # 5. Intent Classifier
        self._initialize_intent_classifier()

        # 6. Memory
        self._initialize_memory()

        # 7. Confidence Gate
        self._initialize_confidence_gate()

        logger.info(
            f"✅ Agent ready. Tools: {list(self._tools.keys())}"
        )

    def _initialize_vector_db(self):
        from src.embeddings.model import EmbeddingModelManager
        embedding_manager = EmbeddingModelManager(config_path="./config.yaml")
        embeddings = embedding_manager.get_model()
        from src.embeddings.vector_db import VectorDatabaseManager
        self.vector_db_manager = VectorDatabaseManager(
            embeddings=embeddings,
            config_path="./config.yaml",
        )
        logger.info("✅ Vector Database initialized")

    def _initialize_schema_loader(self):
        """Khởi tạo SchemaLoader và cập nhật system prompt từ university info."""
        self._schema_loader = SchemaLoader(self.config)
        if self._schema_loader.schema_exists():
            uni_info = self._schema_loader.load_university_info()
            uni_name = uni_info.get("name", "")
            doc_list = uni_info.get("source_documents", [])
            if uni_name or doc_list:
                from src.agent.prompts import build_system_prompt
                self._system_prompt = build_system_prompt(
                    university_name=uni_name,
                    document_list=doc_list,
                )
                logger.info(
                    f"[SchemaLoader] ✅ System prompt cập nhật cho: {uni_name} "
                    f"({len(doc_list)} documents)"
                )
        else:
            logger.info(
                "[SchemaLoader] university_schema.yaml chưa tồn tại. "
                "Dùng REACT_SYSTEM_PROMPT mặc định."
            )

    def _register_tools(self):
        """Đăng ký tất cả tools cho Agent."""
        llm_invoker = self._create_llm_invoker()

        self._tools = {
            "retrieve": RetrieveTool(
                vector_db_manager=self.vector_db_manager,
                config=self.config,
            ),
            "evaluate": EvaluateTool(),
            "rewrite": RewriteTool(llm_invoker=llm_invoker),
            "generate": GenerateTool(
                llm_invoker=llm_invoker,
                system_prompt=self._system_prompt,
            ),
        }
        logger.info(f"✅ Tools registered: {list(self._tools.keys())}")

    def _create_llm_invoker(self) -> Callable[[str], str]:
        """Tạo closure gọi LLM — dùng cho các tools."""
        llm = self.llm
        provider = self._provider

        def invoker(prompt: str) -> str:
            return _invoke_llm(llm, provider, prompt)

        return invoker

    def _initialize_intent_classifier(self):
        """Khởi tạo IntentClassifier với schema từ SchemaLoader."""
        if self._schema_loader is None:
            self._schema_loader = SchemaLoader(self.config)

        intent_config = self._schema_loader.load()
        if not intent_config:
            logger.warning(
                "[Orchestrator] Không tìm thấy intent schema nào. "
                "IntentClassifier sẽ không hoạt động."
            )
            self.intent_classifier = None
            return

        domain_entities = self._schema_loader.load_domain_entities()
        self.intent_classifier = IntentClassifier(
            intent_config=intent_config,
            llm_invoker=self._create_llm_invoker(),
            domain_entities=domain_entities if domain_entities else None,
        )
        source = (
            "university_schema.yaml"
            if self._schema_loader.schema_exists()
            else "config.yaml (fallback)"
        )
        logger.info(f"✅ IntentClassifier initialized (source: {source})")

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

    def _initialize_confidence_gate(self):
        """Khởi tạo ConfidenceGate với thresholds từ config."""
        agent_config = self.config.get("agent", {})
        self.confidence_gate = ConfidenceGate(
            high_threshold=agent_config.get("high_confidence_threshold"),
            low_threshold=agent_config.get("low_confidence_threshold"),
        )
        logger.info(
            f"✅ ConfidenceGate initialized "
            f"(high={self.confidence_gate.high}, low={self.confidence_gate.low})"
        )

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
        Trả lời câu hỏi qua vòng lặp ReACT Multi-hop (Tool-Based).

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
        # BƯỚC 0: INTENT GATE (Preprocessing — src/pipeline/)
        # ============================================================
        notify("🔎 Đang phân loại câu hỏi...")
        intent_result = self._run_intent_gate(question, session_id)

        if intent_result and intent_result.needs_clarification:
            logger.info(
                f"❓ Intent='{intent_result.intent_name}' | "
                f"Missing: {intent_result.missing_fields}"
            )
            state = AgentState(query=question, max_iterations=1)
            state.add_iteration(
                thought=f"Intent '{intent_result.intent_name}' cần entity: {intent_result.missing_fields}",
                action="Clarify",
                action_input=question,
                observation=f"Thiếu: {intent_result.missing_fields}",
            )

            # Lưu clarification state vào memory
            if self.memory:
                self.memory.add_turn(
                    session_id=session_id,
                    question=question,
                    answer=intent_result.clarification_question,
                    entities=intent_result.entities,
                    intent_name=intent_result.intent_name,
                    needs_clarification=True,
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
        elif intent_result:
            logger.info(
                f"✅ Intent='{intent_result.intent_name}' | "
                f"Entities={intent_result.entities} | Pass to RAG."
            )

        # ============================================================
        # BƯỚC 1-N: AGENT REASONING LOOP (gọi Tools)
        # ============================================================
        agent_config = self.config.get("agent", {})
        max_iter = agent_config.get("max_iterations", 5)
        min_avg_sim = agent_config.get("min_avg_similarity", 0.45)
        top_k = self.config.get("retrieval", {}).get("top_k", 3)

        state = AgentState(query=question, max_iterations=max_iter)
        current_query = question
        all_results: List[Tuple] = []

        try:
            for hop in range(self.MAX_RETRIEVAL_HOPS):
                # ── Tool 1: RETRIEVE ──
                notify(f"🔍 [{hop + 1}/{self.MAX_RETRIEVAL_HOPS}] Đang tìm kiếm: \"{current_query[:60]}\"")
                retrieve_result = self._tools["retrieve"].execute(query=current_query)

                state.add_iteration(
                    thought=f"Tìm kiếm lần {hop + 1} với query: '{current_query}'",
                    action=self._tools["retrieve"].name,
                    action_input=current_query,
                    observation=retrieve_result.message,
                )

                # Merge kết quả (dedup)
                all_results = self._merge_results(all_results, retrieve_result.data)

                if not all_results:
                    logger.warning("⚠️ Không tìm thấy tài liệu liên quan.")
                    break

                # ── Tool 2: EVALUATE ──
                notify("🧐 Đang đánh giá mức độ liên quan...")
                eval_result = self._tools["evaluate"].execute(
                    question=question,
                    results=all_results,
                    min_avg_sim=min_avg_sim,
                    llm_invoker=self._create_llm_invoker(),
                    top_k=top_k,
                )

                eval_data = eval_result.data
                state.add_iteration(
                    thought=f"Hop {hop + 1}: avg_sim={eval_data.get('avg_sim', 0):.2f}",
                    action=self._tools["evaluate"].name,
                    action_input=f"avg_sim={eval_data.get('avg_sim', 0):.3f}",
                    observation=f"relevant={eval_data.get('relevant')} | {eval_data.get('reason', '')}",
                )

                if eval_data.get("relevant"):
                    logger.info(f"✅ Hop {hop + 1}: Tài liệu liên quan → generate.")
                    break

                # ── Tool 3: REWRITE (nếu chưa đạt) ──
                if hop < self.MAX_RETRIEVAL_HOPS - 1:
                    notify("✏️ Tài liệu chưa liên quan, đang viết lại câu hỏi...")
                    rewrite_result = self._tools["rewrite"].execute(
                        question=question,
                        reason=eval_data.get("reason", ""),
                    )

                    if rewrite_result.success and rewrite_result.data != current_query:
                        current_query = rewrite_result.data
                        state.add_iteration(
                            thought=f"Query rewrite: '{rewrite_result.data}'",
                            action=self._tools["rewrite"].name,
                            action_input=question,
                            observation=rewrite_result.message,
                        )
                    else:
                        logger.info("Query rewrite không tạo ra query mới. Dừng.")
                        break

            # ============================================================
            # GENERATE ANSWER (Tool 4)
            # ============================================================
            if not all_results:
                answer = ConfidenceGate._no_result_answer(question)
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
            gen_result = self._tools["generate"].execute(
                question=question,
                results=all_results,
            )

            state.add_iteration(
                thought="Đã có đủ tài liệu, tổng hợp câu trả lời",
                action=self._tools["generate"].name,
                action_input=question,
                observation=f"Generated {len(gen_result.data)} chars",
            )

            raw_answer = gen_result.data

            # ============================================================
            # CONFIDENCE GATE (Postprocessing — src/pipeline/)
            # ============================================================
            confidence = ConfidenceGate.calculate_confidence(
                all_results, raw_answer, state.iterations
            )
            gate_result = self.confidence_gate.evaluate(
                confidence, raw_answer, question
            )

            logger.info(
                f"[ConfidenceGate] confidence={confidence:.1%} | "
                f"action={gate_result.action}"
            )

            answer = gate_result.answer
            state.set_answer(answer, confidence=confidence, success=gate_result.success)

            if gate_result.action == "reject":
                notify(f"⚠️ Độ tin cậy thấp ({confidence:.0%}), không đủ thông tin.")

            logger.info(f"✅ Done — confidence: {confidence:.1%}, hops: {state.iterations}")

            # ============================================================
            # SAVE MEMORY
            # ============================================================
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

            # Build response
            retrieved_chunks = self._format_chunks_for_ui(all_results)
            result = self._build_result(
                answer, confidence, gate_result.success, state, retrieved_chunks
            )
            result["intent_name"] = intent_result.intent_name if intent_result else "UNKNOWN"
            result["entities"] = intent_result.entities if intent_result else {}
            result["needs_clarification"] = False
            return result

        except Exception as e:
            logger.error(f"❌ Agent error: {e}", exc_info=True)
            state.set_error(str(e), confidence=0.0)
            return self._build_result(f"❌ Lỗi hệ thống: {e}", 0.0, False, state, [])

    # -------------------------------------------------------------- #
    #  Intent Gate (delegates to src/pipeline/)                       #
    # -------------------------------------------------------------- #

    def _run_intent_gate(self, question: str, session_id: str):
        """Chạy IntentClassifier với memory context."""
        if not self.intent_classifier:
            return None

        memory_context = self.memory.get_context(session_id) if self.memory else ""
        memory_entities = (
            self.memory.get_entities_from_memory(session_id) if self.memory else {}
        )
        previous_intent = None
        if self.memory:
            previous_intent = self.memory.get_last_clarification_intent(session_id)

        return self.intent_classifier.classify(
            question=question,
            memory_context=memory_context,
            memory_entities=memory_entities,
            previous_intent=previous_intent,
        )

    # -------------------------------------------------------------- #
    #  Helper methods                                                 #
    # -------------------------------------------------------------- #

    @staticmethod
    def _merge_results(
        existing: List[Tuple], new_results: list
    ) -> List[Tuple]:
        """Merge kết quả retrieve, dedup theo page_content."""
        existing_contents = {doc.page_content for doc, _ in existing}
        for doc, score in (new_results or []):
            if doc.page_content not in existing_contents:
                existing.append((doc, score))
                existing_contents.add(doc.page_content)
        return existing

    @staticmethod
    def _format_chunks_for_ui(results: list) -> List[Dict[str, Any]]:
        """Chuẩn bị dữ liệu chunk để hiển thị trên giao diện."""
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

    @staticmethod
    def _build_result(
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
