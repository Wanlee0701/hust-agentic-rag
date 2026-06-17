"""
Agent module — ReACT pattern agent (Tool-Based) cho Q&A về quy định sinh viên.

Components:
  - orchestrator.py: Agent chính, điều phối tools
  - state.py: Quản lý trạng thái agent
  - prompts.py: Prompt templates
  - tools/: Các tool agent sử dụng (retrieve, evaluate, rewrite, generate)
"""
from src.agent.state import AgentState, Step
from src.agent.prompts import get_prompt, get_react_prompt, PROMPTS
from src.agent.orchestrator import StudentRegulationAgent

__all__ = [
    "AgentState",
    "Step",
    "get_prompt",
    "get_react_prompt",
    "PROMPTS",
    "StudentRegulationAgent",
]