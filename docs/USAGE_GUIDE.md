# 📘 Hướng Dẫn Sử Dụng Agent

Hướng dẫn chi tiết cách sử dụng Agent ReACT cho hệ thống trả lời câu hỏi về quy định sinh viên.

---

## 📋 Mục Lục

1. [Cài Đặt](#cài-đặt)
2. [Cấu Trúc Thư Mục](#cấu-trúc-thư-mục)
3. [Khái Niệm Cơ Bản](#khái-niệm-cơ-bản)
4. [Sử Dụng](#sử-dụng)
5. [Ví Dụ](#ví-dụ)
6. [Debugging](#debugging)
7. [Các Vấn Đề Thường Gặp](#các-vấn-đề-thường-gặp)

---

## 🔧 Cài Đặt

### Yêu Cầu

- Python 3.8+
- Chroma DB đã khởi tạo với chunks dữ liệu
- Ollama chạy locally (mistral model)
- Các packages từ requirements.txt

### Kiểm Tra Cài Đặt

```bash
# 1. Kiểm tra Ollama
curl http://localhost:11434/api/tags

# 2. Kiểm tra Chroma DB
ls ./data/chroma/

# 3. Kiểm tra Python packages
python -c "from langchain.agents import create_react_agent; print('✅ LangChain OK')"
```

---

## 📁 Cấu Trúc Thư Mục

```
src/
├── agent/                      # Agent module
│   ├── __init__.py            # Export classes
│   ├── orchestrator.py         # Agent chính (StudentRegulationAgent)
│   ├── state.py               # AgentState - track trạng thái
│   ├── tools.py               # AgentTools - Retrieve, Verify, Refine
│   ├── prompts.py             # ReACT prompts templates
│   └── config.py              # (Optional) Agent-specific config
│
├── embeddings/
│   ├── model.py               # Embedding model
│   ├── vector_db.py           # Vector Database Manager
│   └── processor.py           # Text processing
│
└── retrieval/                 # Retrieval components
    └── __init__.py
```

---

## 💡 Khái Niệm Cơ Bản

### ReACT Pattern

Agent hoạt động theo chu kỳ: **Thought → Action → Observation → Repeat**

```
┌─────────────────────────────────────────────┐
│ ITERATION 1                                 │
├─────────────────────────────────────────────┤
│ 💭 THOUGHT: "Tôi cần tìm về học phí"       │
│ 🔧 ACTION: Retrieve("học phí năm nhất")    │
│ 👀 OBSERVATION: Tìm được 3 tài liệu        │
│                                             │
│ 💭 THOUGHT: "Thông tin có đủ không?"       │
│ 📊 Confidence: 0.68 < 0.75 → Tiếp tục      │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ ITERATION 2                                 │
├─────────────────────────────────────────────┤
│ 💭 THOUGHT: "Cần tìm thêm về deadline"     │
│ 🔧 ACTION: Retrieve("deadline thanh toán") │
│ 👀 OBSERVATION: Tìm được 2 tài liệu        │
│                                             │
│ 💭 THOUGHT: "Đủ rồi!"                     │
│ 📊 Confidence: 0.87 ≥ 0.75 → Dừng          │
│ ✅ FINAL ANSWER: "Học phí là ... ngày..."  │
└─────────────────────────────────────────────┘
```

### Tools (Công Cụ)

Agent có 3 công cụ:

| Tool | Mô Tả | Khi Nào Dùng |
|------|-------|------------|
| **Retrieve** | Tìm kiếm tài liệu từ Chroma | Cần thông tin từ KB |
| **Refine** | Tạo query alternatives | Retrieve không tìm được |
| **Verify** | Kiểm tra chất lượng answer | Để xác định tiếp tục hay dừng |

### AgentState

Tracking object lưu trữ toàn bộ quá trình reasoning:

```python
state = AgentState(query="Học phí bao nhiêu?")
# sau mỗi iteration:
state.add_iteration(
    thought="Tôi cần tìm...",
    action="Retrieve",
    action_input="học phí",
    observation="Tìm được 3 docs..."
)
# cuối cùng:
state.set_answer(answer="...", confidence=0.87)
```

---

## 🚀 Sử Dụng

### Cách 1: Sử Dụng Trực Tiếp trong Python

```python
from src.agent import StudentRegulationAgent

# 1. Khởi tạo agent
agent = StudentRegulationAgent(config_path="./config.yaml")

# 2. Trả lời câu hỏi
result = agent.answer_question("Học phí năm nhất bao nhiêu?")

# 3. Truy cập kết quả
print(f"Trả lời: {result['answer']}")
print(f"Độ tin cậy: {result['confidence']:.0%}")
print(f"Thành công: {result['success']}")

# 4. In chi tiết (tùy chọn)
state = result['state']
state.print_summary()
```

### Cách 2: Batch Processing (Nhiều câu hỏi)

```python
from src.agent import StudentRegulationAgent

agent = StudentRegulationAgent()

questions = [
    "Học phí năm nhất bao nhiêu?",
    "Có thể học lại không?",
    "Năng suất tối thiểu là bao nhiêu?",
]

results = agent.batch_answer_questions(questions)

for i, result in enumerate(results, 1):
    print(f"\n[Câu {i}]")
    print(f"Trả lời: {result['answer']}")
    print(f"Confidence: {result['confidence']:.0%}")
```

### Cách 3: Tích Hợp API/Streamlit

```python
# api/main.py hoặc streamlit_app.py
from src.agent import StudentRegulationAgent
import json

# Khởi tạo một lần
agent = StudentRegulationAgent()

def ask_question(question: str):
    """Endpoint API"""
    result = agent.answer_question(question)
    
    return {
        "question": question,
        "answer": result['answer'],
        "confidence": result['confidence'],
        "success": result['success'],
        "sources": result['state'].sources if result['state'] else []
    }

# Ví dụ
if __name__ == "__main__":
    response = ask_question("Học phí là gì?")
    print(json.dumps(response, ensure_ascii=False, indent=2))
```

### Cách 4: Sử Dụng State Để Debug

```python
from src.agent import StudentRegulationAgent, AgentState

agent = StudentRegulationAgent()

# Tạo state riêng
state = AgentState(query="Quy định về GPA?", max_iterations=5)

# Thực thi (có thể custom)
result = agent.answer_question("Quy định về GPA?")
state = result['state']

# Debug - xem chi tiết từng iteration
print(f"Iteration: {state.iterations}")
for i, thought in enumerate(state.thoughts, 1):
    print(f"[{i}] Thought: {thought}")
    print(f"    Action: {state.actions[i-1]}")
    print(f"    Obs: {state.observations[i-1][:100]}...")

# Confidence breakdown
print(f"Confidence: {state.confidence:.2%}")
print(f"Sources: {state.sources}")
```

---

## 📚 Ví Dụ

### Ví Dụ 1: Câu Hỏi Đơn Giản

**Input:**
```python
agent.answer_question("Học phí năm nhất bao nhiêu?")
```

**Output:**
```
{
    "answer": "Theo Quyết định tuyển sinh năm 2025, học phí năm nhất là 8,000,000 VND (tám triệu đồng) cho sinh viên chính quy. Ngày thanh toán hạn chót là 30 tháng 9.",
    "confidence": 0.92,
    "success": true,
    "state": <AgentState object>
}

[State Summary]
Query: Học phí năm nhất bao nhiêu?
Iterations: 2
Sources: ["QD_TuyenSinh_2025.pdf", "Quy_che_25.pdf"]
```

### Ví Dụ 2: Câu Hỏi Phức Tạp

**Input:**
```python
agent.answer_question("Nếu GPA dưới 2.0, tôi còn được học không?")
```

**Flow:**
```
[Iteration 1]
💭 Thought: "Cần tìm quy định về GPA"
🔧 Action: Retrieve("GPA dưới 2.0")
👀 Observation: "Tìm được quy chế học tập"
📊 Confidence: 0.65 (chưa đủ)

[Iteration 2]
💭 Thought: "Cần tìm thêm về hoãn học"
🔧 Action: Retrieve("hoãn học GPA thấp")
👀 Observation: "Tìm được Quyết định về hoãn học"
📊 Confidence: 0.82 (đủ rồi!)

✅ Final Answer: "Nếu GPA < 2.0 và X điều kiện khác, 
   bạn được phép hoãn học tối đa 1 năm học..."
```

### Ví Dụ 3: Câu Hỏi Không Có Kết Quả

**Input:**
```python
agent.answer_question("Có bao nhiêu sao?")  # Câu hỏi không liên quan
```

**Output:**
```
{
    "answer": "❌ Không tìm thấy thông tin liên quan đến câu hỏi này trong cơ sở dữ liệu quy định sinh viên.",
    "confidence": 0.2,
    "success": false,
    "state": <AgentState>
}
```

---

## 🐛 Debugging

### Bật Debug Mode

```python
import logging

# Bật logging chi tiết
logging.basicConfig(level=logging.DEBUG)

agent = StudentRegulationAgent()
result = agent.answer_question("Học phí bao nhiêu?")
```

### In Reasoning Process

```python
state = result['state']

# Xem chi tiết từng bước
print("\n=== REASONING PROCESS ===")
for step in state.steps:
    print(f"\n[Step {step.iteration}]")
    print(f"Thought: {step.thought}")
    print(f"Action: {step.action}")
    print(f"Input: {step.action_input}")
    print(f"Observation: {step.observation[:200]}...")

# Xem resources sử dụng
print(f"\nResources Used:")
print(f"  - Iterations: {state.iterations}")
print(f"  - Documents: {len(state.sources)}")
print(f"  - Confidence: {state.confidence:.2%}")
```

### Kiểm Tra Config

```python
from src.agent import StudentRegulationAgent
import yaml

agent = StudentRegulationAgent()

# Kiểm tra config được load
print(agent.config['retrieval'])
print(agent.config['agent'])
print(agent.config['llm'])
```

---

## ❓ Các Vấn Đề Thường Gặp

### ❌ Lỗi: "Connection refused" từ Ollama

**Nguyên Nhân:** Ollama service chưa chạy

**Giải Pháp:**
```bash
# Windows
ollama serve

# Linux/Mac
ollama serve &
```

### ❌ Lỗi: "mistral model not found"

**Nguyên Nhân:** Model chưa được download

**Giải Pháp:**
```bash
ollama pull mistral
```

### ❌ Lỗi: "Chroma connection error"

**Nguyên Nhân:** Chroma DB chưa được khởi tạo

**Giải Pháp:**
```python
# Chạy script khởi tạo data
python -m src.embeddings.processor
```

### ⚠️ Agent chạy quá lâu

**Nguyên Nhân:** Số iteration quá cao hoặc LLM chậm

**Giải Pháp:**
1. Giảm `max_iterations` trong config.yaml
2. Kiểm tra tốc độ mạng/máy
3. Thử dùng model nhỏ hơn (ví dụ: neural-chat thay mistral)

### 🔍 Agent lúc trả lời tốt, lúc trả lời tệ

**Nguyên Nhân:** Độ tin cậy không ổn định

**Giải Pháp:**
1. Tăng `confidence_threshold` trong config
2. Tăng `top_k` để lấy thêm documents
3. Cải thiện chunking strategy

---

## 📖 Tài Liệu Tham Khảo

- [08-Agent-Design.md](../docs/08-Agent-Design.md) - Chi tiết ReACT pattern
- [ARCHITECTURE_DIAGRAM_AGENTIC_RAG.md](../docs/ARCHITECTURE_DIAGRAM_AGENTIC_RAG.md) - Kiến trúc hệ thống
- [LangChain Docs](https://python.langchain.com/docs/modules/agents/) - LangChain Agent docs
- [Ollama Docs](https://github.com/ollama/ollama) - Ollama LLM

---

## 💬 Hỗ Trợ

Nếu gặp vấn đề:

1. **Kiểm tra logs:** Xem file `./logs/` để tìm lỗi
2. **Debuging:** Bật debug logging như trên
3. **Test Components:** Test từng component riêng lẻ trước
4. **Xem Examples:** Xem folder `notebooks/` để có examples thực tế

---

**Last Updated:** 2025-04-27  
**Author:** AI Assistant  
**Version:** 1.0.0
