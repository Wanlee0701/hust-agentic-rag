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
from src.agent.graph import build_graph

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

        # 8. Build LangGraph
        self._graph = build_graph(self)
        logger.info("✅ LangGraph compiled")

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
        notify("🔎 Đang phân loại câu hỏi...")

        agent_config = self.config.get("agent", {})

        initial_state: Dict[str, Any] = {
            "question": question,
            "session_id": session_id,
            "intent_name": "UNKNOWN",
            "entities": {},
            "needs_clarification": False,
            "clarification_question": "",
            "missing_fields": [],
            "current_query": question,
            "all_results": [],
            "hop_count": 0,
            "max_hops": self.MAX_RETRIEVAL_HOPS,
            "min_avg_sim": agent_config.get("min_avg_similarity", 0.45),
            "top_k": self.config.get("retrieval", {}).get("top_k", 3),
            "is_relevant": False,
            "avg_sim": 0.0,
            "eval_reason": "",
            "raw_answer": "",
            "confidence": 0.0,
            "gate_action": "",
            "final_answer": "",
            "success": False,
            "steps": [],
            "sources": [],
            "error": "",
        }

        try:
            final_state = self._graph.invoke(initial_state)
            logger.info(
                f"✅ Done — confidence: {final_state.get('confidence', 0):.1%} | "
                f"steps: {len(final_state.get('steps', []))}"
            )
            return self._state_to_response(final_state)
        except Exception as e:
            logger.error(f"❌ Agent error: {e}", exc_info=True)
            return {
                "answer": f"❌ Lỗi hệ thống: {e}",
                "confidence": 0.0,
                "success": False,
                "state": AgentState(query=question),
                "retrieved_chunks": [],
                "needs_clarification": False,
                "clarification_question": "",
                "intent_name": "UNKNOWN",
                "entities": {},
            }

    def _state_to_response(self, final_state: dict) -> Dict[str, Any]:
        """Chuyển đổi GraphState dict → response dict cho app.py."""
        state = AgentState.from_graph_state(final_state)

        if final_state.get("needs_clarification"):
            return {
                "answer": final_state["clarification_question"],
                "confidence": 0.0,
                "success": False,
                "state": state,
                "retrieved_chunks": [],
                "needs_clarification": True,
                "clarification_question": final_state["clarification_question"],
                "intent_name": final_state["intent_name"],
                "entities": final_state["entities"],
            }

        retrieved_chunks = self._format_chunks_for_ui(
            final_state.get("all_results", [])
        )
        return {
            "answer": final_state.get("final_answer", ""),
            "confidence": final_state.get("confidence", 0.0),
            "success": final_state.get("success", False),
            "state": state,
            "retrieved_chunks": retrieved_chunks,
            "needs_clarification": False,
            "clarification_question": "",
            "intent_name": final_state.get("intent_name", "UNKNOWN"),
            "entities": final_state.get("entities", {}),
        }

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
