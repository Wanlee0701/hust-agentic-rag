# LangGraph Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thay thế vòng lặp Python thủ công trong `orchestrator.py` bằng LangGraph `StateGraph` gồm 7 nodes, giữ nguyên 100% logic và interface hiện tại, thêm LangSmith tracing.

**Architecture:** GraphState (TypedDict) được chia sẻ qua 7 nodes: `intent_gate → retrieve → evaluate → [rewrite →] generate → confidence_gate → save_memory`. Routing functions quyết định edge có điều kiện. Tất cả nodes được định nghĩa là closures bên trong `build_graph(agent)` để capture agent components.

**Tech Stack:** `langgraph==1.1.6`, `langsmith==0.8.9`, `langchain-core==1.4.1`, LangGraph `StateGraph`, Python `TypedDict`.

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `src/agent/graph.py` | **CREATE** | GraphState TypedDict + 7 node functions + 2 routing functions + `build_graph()` |
| `src/agent/orchestrator.py` | **MODIFY** | `__init__` thêm `self._graph = build_graph(self)`; `answer_question()` gọi `graph.invoke()`; thêm `_state_to_response()` |
| `src/agent/state.py` | **MODIFY** | Thêm `AgentState.from_graph_state()` classmethod |
| `src/agent/__init__.py` | **MODIFY** | Export thêm `build_graph` |
| `.env` | **MODIFY** | Thêm `LANGCHAIN_TRACING_V2`, `LANGCHAIN_API_KEY`, `LANGCHAIN_PROJECT` |

Files **không thay đổi:** `src/agent/tools/*`, `src/agent/prompts.py`, `src/pipeline/*`, `src/memory/*`, `app.py`.

---

## Task 1: Tạo `src/agent/graph.py`

**Files:**
- Create: `src/agent/graph.py`

- [ ] **Step 1: Tạo file với GraphState TypedDict và tất cả nodes**

```python
# src/agent/graph.py
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
from typing import Any, Dict, List, Optional

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
```

- [ ] **Step 2: Kiểm tra import**

```bash
cd "c:/Users/PC/Desktop/ĐATN"
python -c "from src.agent.graph import build_graph, GraphState; print('graph.py OK')"
```

Expected: `graph.py OK`

- [ ] **Step 3: Commit**

```bash
git add src/agent/graph.py
git commit -m "feat: add LangGraph StateGraph definition (graph.py)"
```

---

## Task 2: Thêm `AgentState.from_graph_state()` vào `state.py`

**Files:**
- Modify: `src/agent/state.py`

- [ ] **Step 1: Thêm classmethod vào class AgentState**

Thêm method sau vào cuối class `AgentState` (sau `_format_steps`), trước dấu đóng class:

```python
    @classmethod
    def from_graph_state(cls, gs: dict) -> "AgentState":
        """
        Chuyển đổi GraphState dict → AgentState object.
        Dùng để tương thích ngược với app.py (vẫn hiển thị AgentState).

        Args:
            gs: Final state dict từ graph.invoke().

        Returns:
            AgentState object đã được populate đầy đủ.
        """
        state = cls(
            query=gs.get("question", ""),
            max_iterations=gs.get("max_hops", 2) * 4,
        )
        for step_dict in gs.get("steps", []):
            state.add_iteration(
                thought=step_dict.get("thought", ""),
                action=step_dict.get("action", ""),
                action_input=step_dict.get("action_input", ""),
                observation=step_dict.get("observation", ""),
            )
        for src in gs.get("sources", []):
            state.add_source(src)

        final_answer = gs.get("final_answer") or gs.get("clarification_question", "")
        confidence = gs.get("confidence", 0.0)
        success = gs.get("success", False)
        if final_answer:
            state.set_answer(final_answer, confidence, success)
        if gs.get("error"):
            state.set_error(gs["error"])
        return state
```

- [ ] **Step 2: Kiểm tra**

```bash
python -c "
from src.agent.state import AgentState
gs = {
    'question': 'test', 'steps': [], 'sources': [],
    'final_answer': 'OK', 'confidence': 0.8, 'success': True,
    'max_hops': 2, 'error': '',
}
s = AgentState.from_graph_state(gs)
print('answer:', s.answer, '| confidence:', s.confidence)
"
```

Expected: `answer: OK | confidence: 0.8`

- [ ] **Step 3: Commit**

```bash
git add src/agent/state.py
git commit -m "feat: add AgentState.from_graph_state() for LangGraph compatibility"
```

---

## Task 3: Refactor `orchestrator.py` để dùng graph

**Files:**
- Modify: `src/agent/orchestrator.py`

- [ ] **Step 1: Thêm import graph vào đầu file**

Thêm dòng sau ngay bên dưới `from src.memory.memory_manager import get_memory`:

```python
from src.agent.graph import build_graph
```

- [ ] **Step 2: Thêm `self._graph = build_graph(self)` vào `_initialize()`**

Trong method `_initialize()`, thêm dòng cuối sau khi ConfidenceGate được khởi tạo (sau `logger.info(...)`):

```python
        # 8. Build LangGraph
        self._graph = build_graph(self)
        logger.info("✅ LangGraph compiled")
```

- [ ] **Step 3: Thay thế toàn bộ body `answer_question()`**

Xóa toàn bộ body của method `answer_question()` (từ `def notify` đến hết `except Exception`) và thay bằng:

```python
    def answer_question(
        self,
        question: str,
        session_id: str = "default",
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> Dict[str, Any]:
        """
        Trả lời câu hỏi thông qua LangGraph StateGraph.

        Graph: intent_gate → retrieve → evaluate → [rewrite →]
               generate → confidence_gate → save_memory → END
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
            # Intent defaults
            "intent_name": "UNKNOWN",
            "entities": {},
            "needs_clarification": False,
            "clarification_question": "",
            "missing_fields": [],
            # Retrieval loop
            "current_query": question,
            "all_results": [],
            "hop_count": 0,
            "max_hops": self.MAX_RETRIEVAL_HOPS,
            # Config
            "min_avg_sim": agent_config.get("min_avg_similarity", 0.45),
            "top_k": self.config.get("retrieval", {}).get("top_k", 3),
            # Evaluation
            "is_relevant": False,
            "avg_sim": 0.0,
            "eval_reason": "",
            # Generation
            "raw_answer": "",
            # Confidence gate
            "confidence": 0.0,
            "gate_action": "",
            "final_answer": "",
            "success": False,
            # Tracking
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
            from src.agent.state import AgentState
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
```

- [ ] **Step 4: Thêm method `_state_to_response()` vào class**

Thêm sau method `answer_question()`, trước method `_run_intent_gate()`:

```python
    def _state_to_response(self, final_state: dict) -> Dict[str, Any]:
        """Chuyển đổi GraphState dict → response dict cho app.py."""
        from src.agent.state import AgentState
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
```

- [ ] **Step 5: Xóa method `_run_intent_gate()` (đã được thay bằng `intent_gate_node`)**

Xóa toàn bộ method `_run_intent_gate()` từ dòng `def _run_intent_gate(self, ...)` đến hết method (khoảng 15 dòng). Logic này đã được chuyển vào `intent_gate_node` trong `graph.py`.

- [ ] **Step 6: Kiểm tra agent khởi tạo**

```bash
python -c "
from src.agent import StudentRegulationAgent
a = StudentRegulationAgent()
print('Agent init OK. Graph type:', type(a._graph).__name__)
"
```

Expected: `Agent init OK. Graph type: CompiledStateGraph`

- [ ] **Step 7: Commit**

```bash
git add src/agent/orchestrator.py
git commit -m "refactor: replace answer_question() loop with LangGraph graph.invoke()"
```

---

## Task 4: Cập nhật `src/agent/__init__.py`

**Files:**
- Modify: `src/agent/__init__.py`

- [ ] **Step 1: Thêm export `build_graph`**

Thay thế toàn bộ nội dung file:

```python
"""
Agent module — AgenticRAG v6 (LangGraph-based) cho Q&A về quy định sinh viên.

Components:
  - graph.py:        LangGraph StateGraph (7 nodes + routing)
  - orchestrator.py: Agent chính, compile và invoke graph
  - state.py:        AgentState, Step, GraphState
  - prompts.py:      Prompt templates
  - tools/:          Các tool agent sử dụng (retrieve, evaluate, rewrite, generate)
"""
from src.agent.state import AgentState, Step
from src.agent.prompts import get_prompt, get_react_prompt, PROMPTS
from src.agent.orchestrator import StudentRegulationAgent
from src.agent.graph import build_graph, GraphState

__all__ = [
    "AgentState",
    "Step",
    "get_prompt",
    "get_react_prompt",
    "PROMPTS",
    "StudentRegulationAgent",
    "build_graph",
    "GraphState",
]
```

- [ ] **Step 2: Commit**

```bash
git add src/agent/__init__.py
git commit -m "chore: export build_graph and GraphState from agent module"
```

---

## Task 5: Cấu hình LangSmith trong `.env`

**Files:**
- Modify: `.env`

- [ ] **Step 1: Thêm LangSmith env vars**

Thêm vào cuối file `.env` (giữ nguyên các dòng hiện có):

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_***
LANGCHAIN_PROJECT=hust-agentic-rag
```

> **Ghi chú:** `LANGCHAIN_API_KEY` giống hệt `LANGSMITH_API_KEY` đã có. LangGraph tự động gửi traces khi env vars này được set — không cần code thêm.

- [ ] **Step 2: Đảm bảo dotenv được load trong `app.py` hoặc entry point**

Kiểm tra xem app.py có `load_dotenv()` chưa:

```bash
grep -n "dotenv\|load_dotenv" "c:/Users/PC/Desktop/ĐATN/app.py" || echo "NOT FOUND"
```

Nếu NOT FOUND, thêm vào đầu `app.py`:
```python
from dotenv import load_dotenv
load_dotenv()
```

- [ ] **Step 3: Commit**

```bash
git add .env
git commit -m "chore: add LangSmith tracing env vars"
```

---

## Task 6: Verification

- [ ] **Step 1: Test import toàn bộ module**

```bash
python -c "
from src.agent import StudentRegulationAgent, build_graph, GraphState
print('All imports OK')
print('GraphState keys:', list(GraphState.__annotations__.keys()))
"
```

Expected:
```
All imports OK
GraphState keys: ['question', 'session_id', 'intent_name', ...]
```

- [ ] **Step 2: Test khởi tạo agent và cấu trúc graph**

```bash
python -c "
from src.agent import StudentRegulationAgent
a = StudentRegulationAgent()
print('Agent ready:', list(a._tools.keys()))
print('Graph nodes:', list(a._graph.graph.nodes.keys()))
"
```

Expected output chứa:
```
Agent ready: ['retrieve', 'evaluate', 'rewrite', 'generate']
Graph nodes: ['intent_gate', 'retrieve', 'evaluate', 'rewrite', 'generate', 'confidence_gate', 'save_memory']
```

- [ ] **Step 3: Test một câu hỏi đơn giản**

```bash
python -c "
from src.agent import StudentRegulationAgent
a = StudentRegulationAgent()
result = a.answer_question('Quy chế tốt nghiệp là gì?', session_id='test')
print('answer[:100]:', result['answer'][:100])
print('confidence:', result['confidence'])
print('success:', result['success'])
print('intent:', result['intent_name'])
print('chunks:', len(result['retrieved_chunks']))
"
```

Expected: Câu trả lời hợp lệ (không exception), `confidence > 0`, `retrieved_chunks` là list.

- [ ] **Step 4: Kiểm tra LangSmith traces**

Mở [smith.langchain.com](https://smith.langchain.com) → Project `hust-agentic-rag` → Xác nhận trace mới xuất hiện với đủ 7 nodes.

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "refactor: complete LangGraph migration (AgenticRAG v6 → v7)"
```
