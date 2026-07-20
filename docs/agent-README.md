# 🤖 Agent Module - ReACT Pattern Implementation

Agent module thực hiện **Agentic RAG** (Reasoning + Acting + Retrieval Augmented Generation) sử dụng **ReACT pattern** cho hệ thống trả lời câu hỏi về quy định sinh viên.

---

## 📁 Cấu Trúc Thư Mục

```
src/agent/
├── __init__.py              # Export public classes & functions
├── orchestrator.py          # ⭐ Agent chính (StudentRegulationAgent)
├── state.py                 # AgentState - quản lý trạng thái reasoning
├── tools.py                 # AgentTools - Retrieve, Verify, Refine tools
├── prompts.py               # Prompt templates cho ReACT pattern
├── example_usage.py         # 📖 Ví dụ cách sử dụng
└── README.md                # File này
```

---

## 🎯 Các File Chính

### 1. **orchestrator.py** - Agent Chính

```python
from src.agent import StudentRegulationAgent

# Khởi tạo agent
agent = StudentRegulationAgent(config_path="./config.yaml")

# Trả lời câu hỏi
result = agent.answer_question("Học phí bao nhiêu?")
print(result['answer'])
print(f"Confidence: {result['confidence']:.0%}")
```

**Trách vụ:**
- Quản lý lifecycle của agent
- Khởi tạo LLM, Vector DB, Tools
- Thực hiện ReACT loop
- Tính toán confidence score

---

### 2. **state.py** - State Management

```python
from src.agent import AgentState

state = AgentState(query="Học phí là gì?")
state.add_iteration(
    thought="Tôi cần tìm thông tin học phí",
    action="Retrieve",
    action_input="học phí",
    observation="Tìm được 3 tài liệu"
)
state.set_answer("Học phí là...", confidence=0.85)
```

**Trách vụ:**
- Lưu toàn bộ quá trình reasoning
- Track thoughts, actions, observations
- Quản lý confidence score
- Export state thành dict/JSON

---

### 3. **tools.py** - Agent Tools

3 công cụ chính mà agent có thể sử dụng:

| Tool | Mục Đích | Sử Dụng |
|------|----------|--------|
| **retrieve_documents** | Tìm kiếm từ Chroma DB | Lấy thông tin liên quan |
| **refine_query** | Tạo query alternatives | Query không tìm được kết quả |
| **verify_answer** | Kiểm tra chất lượng answer | Xác định dừng hay tiếp tục |

---

### 4. **prompts.py** - Prompt Templates

Chứa tất cả ReACT prompts:
- `REACT_SYSTEM_PROMPT` - Hướng dẫn hệ thống
- `REACT_FORMAT_PROMPT` - Định dạng output
- `VERIFICATION_PROMPT` - Kiểm tra answer
- `QUERY_REFINEMENT_PROMPT` - Cải thiện query

---

## 🔄 ReACT Pattern Flow

```
┌─────────────────────────────────────────┐
│ User asks: "Học phí bao nhiêu?"        │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ AGENT REASONING LOOP                    │
├─────────────────────────────────────────┤
│ [ITERATION 1]                           │
│ 💭 Thought: "Cần tìm info học phí"    │
│ 🔧 Action: Retrieve("học phí")         │
│ 👀 Observation: Tìm được 3 docs       │
│ 📊 Confidence: 0.65 < 0.75 → Tiếp tục │
│                                         │
│ [ITERATION 2]                           │
│ 💭 Thought: "Cần tìm deadline"         │
│ 🔧 Action: Retrieve("deadline đóng")   │
│ 👀 Observation: Tìm được 2 docs       │
│ 📊 Confidence: 0.87 ≥ 0.75 → Dừng     │
│                                         │
│ ✅ Final Answer: "Học phí là..."       │
└─────────────────────────────────────────┘
           ↓
┌─────────────────────────────────────────┐
│ Return: {answer, confidence, state}    │
└─────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start Ollama
ollama serve

# 3. Pull mistral model
ollama pull mistral

# 4. Ensure Chroma DB is ready
python -m src.embeddings.processor  # Nếu chưa khởi tạo
```

### Basic Usage

```python
from src.agent import StudentRegulationAgent

# Initialize
agent = StudentRegulationAgent()

# Ask a question
result = agent.answer_question("Học phí năm nhất bao nhiêu?")

# Get results
print(result['answer'])
print(f"Confidence: {result['confidence']:.0%}")
print(f"Sources: {result['state'].sources}")
```

---

## 📚 Advanced Usage

### Batch Processing

```python
from src.agent import StudentRegulationAgent

agent = StudentRegulationAgent()

questions = [
    "Có được học lại không?",
    "Học bổng là gì?",
    "GPA tối thiểu là bao nhiêu?",
]

results = agent.batch_answer_questions(questions)

for q, r in zip(questions, results):
    print(f"Q: {q}")
    print(f"A: {r['answer']}\n")
```

### Detailed State Analysis

```python
result = agent.answer_question("Quy định về GPA?")
state = result['state']

# Inspect reasoning steps
for step in state.steps:
    print(f"[{step.iteration}] {step.action}: {step.action_input}")

# Inspect confidence calculation
print(f"Confidence: {state.confidence:.2%}")
print(f"Iterations: {state.iterations}/{state.max_iterations}")
print(f"Success: {state.success}")
```

### Custom State Tracking

```python
from src.agent import AgentState

state = AgentState(query="Test?", max_iterations=5)

# Manually track iterations
state.add_iteration(
    thought="...",
    action="Retrieve",
    action_input="...",
    observation="..."
)

# Set answer
state.set_answer("Answer...", confidence=0.9)

# Export as dict
state_dict = state.to_dict()
```

---

## ⚙️ Configuration

Agent được cấu hình qua `config.yaml`:

```yaml
# LLM Configuration
llm:
  provider: "ollama"
  model_name: "mistral"
  base_url: "http://localhost:11434"
  temperature: 0.3
  max_tokens: 1024

# Agent Configuration
agent:
  type: "react"
  max_iterations: 5
  confidence_threshold: 0.75

# Retrieval Configuration
retrieval:
  top_k: 3
  similarity_threshold: 0.5
```

---

## 🔧 Debugging

### Enable Logging

```python
import logging

logging.basicConfig(level=logging.DEBUG)

agent = StudentRegulationAgent()
result = agent.answer_question("Test?")
```

### Print State Summary

```python
result = agent.answer_question("Test?")
state = result['state']

# Print detailed summary
state.print_summary()
```

### Export State to JSON

```python
import json

state_dict = state.to_dict()
print(json.dumps(state_dict, indent=2, ensure_ascii=False))
```

---

## 📖 Ví Dụ Chi Tiết

Xem `example_usage.py` để có 5 ví dụ thực tế:

1. **Simple Question** - Trả lời câu hỏi đơn giản
2. **Complex Question** - Trả lời câu hỏi phức tạp
3. **Batch Questions** - Trả lời nhiều câu hỏi
4. **State Tracking** - Chi tiết quá trình reasoning
5. **Error Handling** - Xử lý lỗi

```bash
python -m src.agent.example_usage
```

---

## 🎓 Concepts Explained

### ReACT Pattern

**Reasoning + Acting** - Mô hình agent suy nghĩ rồi hành động:

1. **THINK** - Agent suy nghĩ về vấn đề
2. **ACTION** - Agent chọn công cụ để sử dụng
3. **OBSERVATION** - Agent quan sát kết quả
4. **REPEAT** - Lặp lại cho đến khi đủ confidence

### Confidence Scoring

Độ tin cậy được tính dựa trên:
- Số lượng documents tìm được (0-0.3)
- Tính cụ thể của answer (0-0.4)
- Số iterations cần (0-0.3)

**Công thức:** `score = weighted_sum(factors) / sum(weights)`

### Tools

**retrieve_documents:** Tìm kiếm tài liệu từ Chroma
```python
docs = retrieve_documents("học phí")
# Returns formatted string with results
```

**refine_query:** Tạo query alternatives khi không tìm được
```python
alternatives = refine_query("học lại được không?")
# Returns: ["Có thể retake môn?", "Quy định học lại", ...]
```

**verify_answer:** Kiểm tra chất lượng answer
```python
verification = verify_answer("Học phí là 8 triệu VND")
# Returns: {"sufficient": True, "reason": "...", "confidence": 0.85}
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Start Ollama: `ollama serve` |
| "mistral not found" | Download model: `ollama pull mistral` |
| "Chroma error" | Initialize data: `python -m src.embeddings.processor` |
| Agent too slow | Reduce `max_iterations` in config |
| Low confidence answers | Increase `top_k` in retrieval config |

---

## 📞 Support & Resources

- **Full Usage Guide:** [USAGE_GUIDE.md](../../USAGE_GUIDE.md)
- **Agent Design Docs:** [08-Agent-Design.md](../../docs/08-Agent-Design.md)
- **Architecture Diagrams:** [ARCHITECTURE_DIAGRAM_AGENTIC_RAG.md](../../docs/ARCHITECTURE_DIAGRAM_AGENTIC_RAG.md)
- **LangChain Docs:** https://python.langchain.com/

---

**Version:** 1.0.0  
**Last Updated:** 2025-04-27  
**Author:** AI Assistant
