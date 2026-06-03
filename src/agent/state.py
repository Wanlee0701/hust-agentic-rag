"""
AgentState - Quản lý trạng thái của agent trong quá trình reasoning
Theo hướng dẫn ReACT pattern từ 08-Agent-Design.md
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class Step:
    """Một bước trong quá trình reasoning"""
    iteration: int
    thought: str
    action: str
    action_input: str
    observation: str


@dataclass
class AgentState:
    """
    Quản lý trạng thái của agent
    
    Attributes:
        query: Câu hỏi ban đầu từ user
        iterations: Số lần lặp hiện tại
        max_iterations: Số lần lặp tối đa
        thoughts: Danh sách các thoughts (suy nghĩ)
        actions: Danh sách các actions (hành động)
        observations: Danh sách các observations (quan sát)
        confidence: Độ tin cậy của câu trả lời (0-1)
        answer: Câu trả lời cuối cùng
        steps: Danh sách Step objects
        success: Có thành công hay không
        error: Lỗi nếu có
    """
    query: str
    iterations: int = 0
    max_iterations: int = 5
    thoughts: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)
    observations: List[str] = field(default_factory=list)
    confidence: float = 0.0
    answer: Optional[str] = None
    steps: List[Step] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_iteration(self, thought: str, action: str, action_input: str, observation: str):
        """
        Thêm một bước trong quá trình reasoning
        
        Args:
            thought: Suy nghĩ của agent
            action: Hành động sẽ thực hiện (Retrieve, Verify, Answer, etc)
            action_input: Input cho hành động
            observation: Kết quả quan sát từ hành động
        """
        self.iterations += 1
        self.thoughts.append(thought)
        self.actions.append(action)
        self.observations.append(observation)
        
        step = Step(
            iteration=self.iterations,
            thought=thought,
            action=action,
            action_input=action_input,
            observation=observation
        )
        self.steps.append(step)
    
    def set_answer(self, answer: str, confidence: float, success: bool = True):
        """
        Đặt câu trả lời cuối cùng
        
        Args:
            answer: Câu trả lời
            confidence: Độ tin cậy (0-1)
            success: Thành công hay không
        """
        self.answer = answer
        self.confidence = min(max(confidence, 0.0), 1.0)  # Clamp to 0-1
        self.success = success
    
    def set_error(self, error: str, confidence: float = 0.0):
        """
        Đặt lỗi nếu có
        
        Args:
            error: Thông báo lỗi
            confidence: Độ tin cậy
        """
        self.error = error
        self.success = False
        self.confidence = confidence
    
    def add_source(self, source: str):
        """Thêm source của document"""
        if source not in self.sources:
            self.sources.append(source)
    
    def is_max_iterations_reached(self) -> bool:
        """Kiểm tra có đạt giới hạn iteration"""
        return self.iterations >= self.max_iterations
    
    def should_continue(self, confidence_threshold: float = 0.75) -> bool:
        """
        Kiểm tra có tiếp tục iteration hay không
        
        Args:
            confidence_threshold: Ngưỡng confidence để dừng
            
        Returns:
            True nếu nên tiếp tục, False nếu nên dừng
        """
        if self.is_max_iterations_reached():
            return False
        
        if self.confidence >= confidence_threshold:
            return False
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Chuyển state thành dictionary
        
        Returns:
            Dictionary chứa toàn bộ state
        """
        return {
            "query": self.query,
            "iterations": self.iterations,
            "max_iterations": self.max_iterations,
            "thoughts": self.thoughts,
            "actions": self.actions,
            "observations": self.observations,
            "confidence": round(self.confidence, 2),
            "answer": self.answer,
            "success": self.success,
            "error": self.error,
            "sources": self.sources,
            "timestamp": self.timestamp,
            "steps": [
                {
                    "iteration": step.iteration,
                    "thought": step.thought,
                    "action": step.action,
                    "action_input": step.action_input,
                    "observation": step.observation[:200] + "..." if len(step.observation) > 200 else step.observation
                }
                for step in self.steps
            ]
        }
    
    def print_summary(self):
        """In ra tóm tắt state"""
        print(f"""
╔═══════════════════════════════════════════════════════════╗
║                    AGENT STATE SUMMARY                   ║
╚═══════════════════════════════════════════════════════════╝

📝 Query: {self.query}
🔄 Iterations: {self.iterations}/{self.max_iterations}
📊 Confidence: {self.confidence:.2%}
✅ Success: {self.success}

📋 Reasoning Steps:
{self._format_steps()}

💬 Final Answer: {self.answer if self.answer else 'N/A'}
📚 Sources: {', '.join(self.sources) if self.sources else 'None'}

⚠️ Error: {self.error if self.error else 'None'}
""")
    
    def _format_steps(self) -> str:
        """Format các steps để in đẹp"""
        if not self.steps:
            return "  (No steps yet)"
        
        formatted = []
        for step in self.steps:
            formatted.append(f"  [{step.iteration}] {step.action}: {step.action_input[:50]}...")
        
        return "\n".join(formatted)
