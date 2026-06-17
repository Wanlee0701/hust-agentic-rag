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
