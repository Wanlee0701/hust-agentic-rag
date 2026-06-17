"""
LangGraph StateGraph cho AgenticRAG v6.

Graph nodes (theo thứ tự):
  intent_gate → [END nếu clarify] → retrieve → evaluate
  → [rewrite →] generate → confidence_gate → save_memory → END

Tất cả nodes là closures bên trong build_graph(agent) để
capture agent components mà không cần global state.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)


# ================================================================== #
#  GraphState — State chia sẻ giữa tất cả nodes                      #
# ================================================================== #

class GraphState(TypedDict):
    # Input
    question: str
    session_id: str

    # Intent Gate output
    intent_name: str
    entities: Dict[str, Any]
    needs_clarification: bool
    clarification_question: str
    missing_fields: List[str]

    # Retrieval loop control
    current_query: str
    all_results: List               # List[(Document, score)]
    hop_count: int
    max_hops: int

    # Config (injected at invoke time)
    min_avg_sim: float
    top_k: int

    # Evaluation
    is_relevant: bool
    avg_sim: float
    eval_reason: str

    # Generation
    raw_answer: str

    # Confidence gate
    confidence: float
    gate_action: str                # 'reject' | 'warn' | 'pass'
    final_answer: str
    success: bool

    # Tracking
    steps: List[Dict[str, Any]]     # serializable Step dicts
    sources: List[str]
    error: str


# ================================================================== #
#  Graph builder                                                       #
# ================================================================== #

def build_graph(agent) -> Any:
    """
    Xây dựng và compile LangGraph StateGraph.

    Args:
        agent: StudentRegulationAgent instance (captured by closures).

    Returns:
        Compiled LangGraph runnable.
    """

    # ── Node functions ─────────────────────────────────────────── #

    def intent_gate_node(state: GraphState) -> dict:
        """Bước 0: Phân loại intent + kiểm tra entity còn thiếu."""
        question = state["question"]
        session_id = state["session_id"]

        memory_context = (
            agent.memory.get_context(session_id) if agent.memory else ""
        )
        memory_entities = (
            agent.memory.get_entities_from_memory(session_id)
            if agent.memory
            else {}
        )
        previous_intent = (
            agent.memory.get_last_clarification_intent(session_id)
            if agent.memory
            else None
        )

        if not agent.intent_classifier:
            return {
                "intent_name": "UNKNOWN",
                "entities": {},
                "needs_clarification": False,
                "clarification_question": "",
                "missing_fields": [],
                "steps": state["steps"],
            }

        result = agent.intent_classifier.classify(
            question=question,
            memory_context=memory_context,
            memory_entities=memory_entities,
            previous_intent=previous_intent,
        )

        step = {
            "iteration": len(state["steps"]) + 1,
            "thought": (
                f"Intent='{result.intent_name}' | "
                f"needs_clarification={result.needs_clarification}"
            ),
            "action": "IntentClassifier",
            "action_input": question,
            "observation": (
                f"Missing: {result.missing_fields}"
                if result.needs_clarification
                else f"Entities: {result.entities}"
            ),
        }

        # Lưu memory cho clarification turn
        if result.needs_clarification and agent.memory:
            agent.memory.add_turn(
                session_id=session_id,
                question=question,
                answer=result.clarification_question,
                entities=result.entities,
                intent_name=result.intent_name,
                needs_clarification=True,
            )

        return {
            "intent_name": result.intent_name,
            "entities": result.entities,
            "needs_clarification": result.needs_clarification,
            "clarification_question": result.clarification_question,
            "missing_fields": result.missing_fields,
            "steps": state["steps"] + [step],
        }

    def retrieve_node(state: GraphState) -> dict:
        """Bước 1: Tìm kiếm tài liệu từ ChromaDB."""
        current_query = state["current_query"]

        result = agent._tools["retrieve"].execute(query=current_query)
        new_results = result.data or []

        # Merge + dedup theo page_content
        existing_contents = {doc.page_content for doc, _ in state["all_results"]}
        merged = list(state["all_results"])
        for doc, score in new_results:
            if doc.page_content not in existing_contents:
                merged.append((doc, score))
                existing_contents.add(doc.page_content)

        step = {
            "iteration": len(state["steps"]) + 1,
            "thought": (
                f"Tìm kiếm hop {state['hop_count'] + 1} "
                f"với query: '{current_query[:60]}'"
            ),
            "action": "retrieve_documents",
            "action_input": current_query,
            "observation": result.message,
        }

        logger.info(
            f"[retrieve_node] hop={state['hop_count'] + 1} | "
            f"query='{current_query[:50]}' | docs={len(new_results)}"
        )

        return {
            "all_results": merged,
            "steps": state["steps"] + [step],
        }

    def evaluate_node(state: GraphState) -> dict:
        """Bước 2: Đánh giá mức độ liên quan (avg-sim + LLM nếu cần)."""
        eval_result = agent._tools["evaluate"].execute(
            question=state["question"],
            results=state["all_results"],
            min_avg_sim=state["min_avg_sim"],
            llm_invoker=agent._create_llm_invoker(),
            top_k=state["top_k"],
        )

        eval_data = eval_result.data
        new_hop = state["hop_count"] + 1

        step = {
            "iteration": len(state["steps"]) + 1,
            "thought": (
                f"Hop {new_hop}: avg_sim={eval_data.get('avg_sim', 0):.2f}"
            ),
            "action": "evaluate_relevance",
            "action_input": f"avg_sim={eval_data.get('avg_sim', 0):.3f}",
            "observation": (
                f"relevant={eval_data.get('relevant')} | "
                f"{eval_data.get('reason', '')}"
            ),
        }

        logger.info(
            f"[evaluate_node] hop={new_hop} | "
            f"relevant={eval_data.get('relevant')} | "
            f"avg_sim={eval_data.get('avg_sim', 0):.2f}"
        )

        return {
            "is_relevant": eval_data.get("relevant", False),
            "avg_sim": eval_data.get("avg_sim", 0.0),
            "eval_reason": eval_data.get("reason", ""),
            "hop_count": new_hop,
            "steps": state["steps"] + [step],
        }

    def rewrite_node(state: GraphState) -> dict:
        """Bước 3 (optional): Viết lại query với thuật ngữ chính xác hơn."""
        rewrite_result = agent._tools["rewrite"].execute(
            question=state["question"],
            reason=state["eval_reason"],
        )

        new_query = (
            rewrite_result.data
            if rewrite_result.success and rewrite_result.data != state["current_query"]
            else state["current_query"]
        )

        step = {
            "iteration": len(state["steps"]) + 1,
            "thought": f"Query rewrite: '{new_query[:60]}'",
            "action": "rewrite_query",
            "action_input": state["question"],
            "observation": rewrite_result.message,
        }

        logger.info(f"[rewrite_node] new_query='{new_query[:60]}'")

        return {
            "current_query": new_query,
            "steps": state["steps"] + [step],
        }

    def generate_node(state: GraphState) -> dict:
        """Bước 4: Tổng hợp câu trả lời từ tất cả tài liệu đã thu thập."""
        all_results = state["all_results"]

        if not all_results:
            from src.pipeline.confidence_gate import ConfidenceGate
            no_result = ConfidenceGate._no_result_answer(state["question"])
            step = {
                "iteration": len(state["steps"]) + 1,
                "thought": "Không tìm thấy tài liệu liên quan",
                "action": "generate_answer",
                "action_input": state["question"],
                "observation": "No documents found",
            }
            return {
                "raw_answer": no_result,
                "sources": [],
                "steps": state["steps"] + [step],
            }

        # Thu thập sources
        sources: List[str] = []
        for doc, _ in all_results:
            if hasattr(doc, "metadata"):
                source = (
                    doc.metadata.get("source_file")
                    or doc.metadata.get("source")
                    or "Không rõ nguồn"
                )
                if source not in sources:
                    sources.append(source)

        gen_result = agent._tools["generate"].execute(
            question=state["question"],
            results=all_results,
        )

        step = {
            "iteration": len(state["steps"]) + 1,
            "thought": "Đã có đủ tài liệu, tổng hợp câu trả lời",
            "action": "generate_answer",
            "action_input": state["question"],
            "observation": f"Generated {len(gen_result.data)} chars",
        }

        logger.info(f"[generate_node] answer_len={len(gen_result.data)}")

        return {
            "raw_answer": gen_result.data,
            "sources": sources,
            "steps": state["steps"] + [step],
        }

    def confidence_gate_node(state: GraphState) -> dict:
        """Bước 5: Tính confidence score và quyết định reject/warn/pass."""
        from src.pipeline.confidence_gate import ConfidenceGate

        all_results = state["all_results"]

        # Shortcut: không có tài liệu → reject ngay
        if not all_results:
            return {
                "confidence": 0.1,
                "gate_action": "reject",
                "final_answer": state["raw_answer"],
                "success": False,
            }

        confidence = ConfidenceGate.calculate_confidence(
            all_results, state["raw_answer"], len(state["steps"])
        )
        gate_result = agent.confidence_gate.evaluate(
            confidence, state["raw_answer"], state["question"]
        )

        logger.info(
            f"[confidence_gate_node] confidence={confidence:.1%} | "
            f"action={gate_result.action}"
        )

        return {
            "confidence": confidence,
            "gate_action": gate_result.action,
            "final_answer": gate_result.answer,
            "success": gate_result.success,
        }

    def save_memory_node(state: GraphState) -> dict:
        """Bước 6: Lưu lượt hội thoại vào ConversationMemory."""
        if agent.memory:
            agent.memory.add_turn(
                session_id=state["session_id"],
                question=state["question"],
                answer=state["final_answer"][:500],
                entities=state["entities"],
                intent_name=state["intent_name"],
                needs_clarification=False,
            )
        return {}

    # ── Routing functions ──────────────────────────────────────── #

    def route_after_intent(state: GraphState) -> str:
        """Sau intent_gate: clarify hoặc chuyển sang RAG."""
        return "clarify" if state["needs_clarification"] else "pass_to_rag"

    def route_after_evaluate(state: GraphState) -> str:
        """
        Sau evaluate:
          - Tài liệu liên quan → generate
          - Đã đủ hop → force_generate
          - Còn hop + chưa liên quan → rewrite
        """
        if state["is_relevant"]:
            return "relevant"
        if state["hop_count"] >= state["max_hops"]:
            return "force_generate"
        return "rewrite"

    # ── Build StateGraph ───────────────────────────────────────── #

    graph = StateGraph(GraphState)

    graph.add_node("intent_gate",     intent_gate_node)
    graph.add_node("retrieve",        retrieve_node)
    graph.add_node("evaluate",        evaluate_node)
    graph.add_node("rewrite",         rewrite_node)
    graph.add_node("generate",        generate_node)
    graph.add_node("confidence_gate", confidence_gate_node)
    graph.add_node("save_memory",     save_memory_node)

    graph.set_entry_point("intent_gate")

    graph.add_conditional_edges(
        "intent_gate",
        route_after_intent,
        {"clarify": END, "pass_to_rag": "retrieve"},
    )
    graph.add_edge("retrieve", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        route_after_evaluate,
        {
            "relevant":       "generate",
            "rewrite":        "rewrite",
            "force_generate": "generate",
        },
    )
    graph.add_edge("rewrite",         "retrieve")
    graph.add_edge("generate",        "confidence_gate")
    graph.add_edge("confidence_gate", "save_memory")
    graph.add_edge("save_memory",     END)

    return graph.compile()
