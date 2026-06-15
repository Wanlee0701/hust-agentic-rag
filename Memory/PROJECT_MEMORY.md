# 📋 MEMORY — HUST Chatbot AgenticRAG
> Cập nhật lần cuối: 2026-06-09 (v3 — Intent Routing + Conversation Memory)

---

## 1. Tổng quan dự án

**Tên:** HUST Student Regulation Chatbot  
**Mục tiêu:** Chatbot hỏi đáp về quy chế đào tạo ĐHBK Hà Nội dựa trên tập tài liệu PDF chính thức.  
**Kiến trúc:** Agentic RAG với vòng lặp ReACT Multi-hop.

---

## 2. Tech Stack

| Thành phần | Chi tiết |
|---|---|
| UI | Streamlit (`app.py`) |
| Agent | LangChain + custom ReACT loop (`src/agent/orchestrator.py`) |
| Vector DB | ChromaDB (local SQLite tại `data/chroma/`) |
| Embedding | `BAAI/bge-m3` (SentenceTransformers, CPU) |
| LLM Local | Ollama (`mistral:latest` - 4.4GB, nằm gọn trong GPU RTX 4050 6GB) |
| LLM Cloud | Google Gemini (`gemini-2.5-flash`) qua `langchain-google-genai` |
| Config | `config.yaml` là nguồn sự thật duy nhất |
| Secrets | `.env` chứa `GEMINI_API_KEY` |

---

## 3. Cấu trúc thư mục quan trọng

```
ĐATN/
├── app.py                      # Streamlit UI chính
├── config.yaml                 # Cấu hình LLM, retrieval, agent
├── .env                        # GEMINI_API_KEY
├── src/
│   └── agent/
│       ├── orchestrator.py     # ⭐ CORE: Agent loop, prompts, clarification, evaluate
│       ├── prompts.py          # System prompt + helper prompts (ít dùng)
│       └── state.py            # AgentState dataclass
│   └── embeddings/
│       ├── model.py            # Load BAAI/bge-m3
│       └── vector_db.py        # ChromaDB wrapper
├── data/
│   ├── chroma/                 # Vector DB SQLite
│   └── chunks/                 # JSON chunks từ PDF (9 files)
├── knowledge_base/raw/         # PDF gốc (không push Git)
└── logs/chatbot.log            # Log chi tiết để debug
```

---

## 4. Luồng xử lý chính (v2 - đã cập nhật)

```
User Question
    │
    ▼
[Bước 0: Intent Check] ── _check_intent(question)
    │   Mơ hồ? ──────────────────────────────────────► Trả về clarification_question
    │   Rõ ràng?
    ▼
[Vòng lặp ReACT - tối đa 2 hops]
    │
    ├─ Retrieve(query, top_k, threshold)
    │       └── Fallback: nếu < 2 kết quả → hạ threshold xuống 0.25
    │
    ├─ [Hop 1] Có ≥ 2 kết quả → SKIP Evaluate → Generate ngay
    │
    ├─ [Hop 2+] Evaluate relevance ── _evaluate_context()
    │       Liên quan? ──────────────────────────────► Generate
    │       Không liên quan? → QueryRewrite → lặp lại
    │
    ▼
GenerateAnswer(question, context)
    │
    ▼
Trả về: {answer, confidence, success, retrieved_chunks, needs_clarification}
```

---

## 5. Các bug đã fix và quyết định thiết kế

### 5.1 Fix Evaluate "quá khắt khe" (2026-06-09)

**Vấn đề:** `_EVALUATE_PROMPT` hỏi LLM *"Tài liệu có đủ để trả lời hoàn chỉnh không?"*  
→ Gemini Flash (thinking model) luôn trả `false` → mọi câu đều trigger rewrite.

**Cách fix:**
1. Đổi câu hỏi sang *"Tài liệu có ĐỀ CẬP đến chủ đề câu hỏi không?"* (tiêu chí nhẹ hơn)
2. JSON key đổi từ `"sufficient"` sang `"relevant"` (code parse giữ fallback cả 2 key)
3. **Quan trọng:** Bỏ qua Evaluate ở Hop 1 nếu đã có ≥ 2 kết quả — generate luôn
4. Giảm `MAX_RETRIEVAL_HOPS` từ 3 xuống 2

**File sửa:** `src/agent/orchestrator.py` — `_EVALUATE_PROMPT`, `_evaluate_context()`, vòng lặp chính

### 5.2 Thêm Clarification Flow (2026-06-09)

**Vấn đề:** Chatbot không biết hỏi lại khi người dùng hỏi mơ hồ (thiếu tên ngành, khóa...).

**Cách làm:**
- Thêm `_INTENT_CHECK_PROMPT`: yêu cầu LLM trả về `{"needs_clarification": true/false, "clarification_question": "..."}`
- Thêm method `_check_intent()` trong `StudentRegulationAgent`
- Bước 0 trong `answer_question()` gọi `_check_intent()` trước khi vào RAG loop
- Nếu `needs_clarification=True`: return dict đặc biệt với key `needs_clarification=True` và `answer = clarification_question`

**File sửa:** `src/agent/orchestrator.py` + `app.py` (UI render khác: viền vàng, icon ❓)

### 5.3 Fix Gemini Asyncio Deadlock (2026-06-08)

**Vấn đề:** Streamlit thread không có event loop → `httpx` async của Google SDK bị deadlock ở gọi thứ 2.

**Cách fix:** Trong `_invoke_llm()`: nếu provider là `gemini`, ép `asyncio.get_event_loop()` hoặc tạo mới trước khi `.invoke()`.

**File sửa:** `src/agent/orchestrator.py` — hàm `_invoke_llm()`

### 5.4 Đa ngôn ngữ (2026-06-09)

`_ANSWER_PROMPT` đã được cập nhật thêm dòng: *"Phát hiện ngôn ngữ câu hỏi và trả lời bằng đúng ngôn ngữ đó"*

---

## 6. Cấu hình `config.yaml` quan trọng

```yaml
llm:
  provider: "gemini"            # "ollama" hoặc "gemini"
  model_name: "gemini-2.5-flash"
  api_key_env: "GEMINI_API_KEY"
  temperature: 0.3
  timeout_seconds: 120

retrieval:
  top_k: 3
  similarity_threshold: 0.35   # Fallback tự động xuống 0.25 nếu < 2 kết quả

agent:
  max_iterations: 5
```

---

## 7. Câu lệnh chạy

```bash
# Khởi động Streamlit
streamlit run app.py

# Đặt API Key (PowerShell)
$env:GEMINI_API_KEY = "your_key"
# Hoặc lưu vào file .env: GEMINI_API_KEY=your_key
```

---

## 8. Bộ Test Cases (để kiểm thử 2 fix trên)

### Test Fix Evaluate (Phần 1)
Những câu dưới đây KHÔNG được trigger rewrite nếu fix đúng:

| # | Câu hỏi | Expected |
|---|---|---|
| T1 | "GPA bao nhiêu thì bị cảnh báo học vụ?" | Trả lời ngay, không rewrite |
| T2 | "Điều kiện nhận học bổng Trần Đại Nghĩa là gì?" | Trả lời ngay, không rewrite |
| T3 | "Bao nhiêu tín chỉ thì tốt nghiệp cử nhân?" | Trả lời ngay, không rewrite |
| T4 | "Học phí nếu rút học phần sau 7 tuần thì sao?" | Trả lời ngay, tối đa 1 rewrite |
| T5 | "Sinh viên bị trượt 14 tín thì bị cảnh cáo mức mấy?" | Tối đa 1 rewrite, KHÔNG loop 3 lần |

### Test Clarification (Phần 2)
Những câu dưới đây PHẢI trigger clarification:

| # | Câu hỏi | Expected (Clarification) |
|---|---|---|
| C1 | "Yêu cầu tiếng Anh của tôi là gì?" | "Bạn đang học ngành gì và thuộc khóa nào (K65/K68/K70)?" |
| C2 | "Học phí của tôi bao nhiêu?" | "Bạn học ngành gì và thuộc khóa nào?" |
| C3 | "Tôi có đủ điều kiện nhận học bổng không?" | "Bạn có thể cho biết GPA học kỳ vừa rồi và ngành học?" |
| C4 | "Điểm chuẩn tiếng Anh của ngành tôi?" | "Bạn học ngành gì và thuộc khóa nào?" |

### Test KHÔNG Trigger Clarification
Những câu này PHẢI đi thẳng vào RAG, KHÔNG hỏi lại:

| # | Câu hỏi |
|---|---|
| NC1 | "GPA bao nhiêu thì bị cảnh báo?" |
| NC2 | "Điều kiện học bổng TDN?" |
| NC3 | "K65 cần TOEIC bao nhiêu để tốt nghiệp?" |
| NC4 | "Sinh viên bị kỷ luật xóa tên khi nào?" |

---

## 9. Tình trạng hiện tại (2026-06-09)

| Tính năng | Trạng thái |
|---|---|
| Multi-hop RAG (Retrieve → Evaluate → Rewrite) | ✅ Hoạt động |
| Fix Evaluate quá khắt khe | ✅ Đã fix v2 |
| Clarification (hỏi lại người dùng) | ✅ Đã implement |
| Hiển thị Raw Chunks trên UI | ✅ Hoạt động |
| Google Gemini integration | ✅ Hoạt động |
| Đa ngôn ngữ | ✅ Cơ bản (detect + respond) |
| Structured KB cho Ngoại ngữ | ❌ Chưa làm |
| GraphRAG | ❌ Chưa làm |
| Conversation Memory | ❌ Chưa làm |
| Hybrid Search (BM25 + Vector) | ❌ Chưa làm |

---

## 10. Việc cần làm tiếp theo

1. **[Ngắn hạn]** Test bộ test cases ở mục 8 để xác nhận 2 fix hoạt động đúng
2. **[Trung hạn]** Xây dựng Structured Knowledge Base cho tài liệu ngoại ngữ (JSON mapping ngành → loại CT → yêu cầu TOEIC/IELTS)
3. **[Trung hạn]** Thêm Hybrid Search: kết hợp BM25 (keyword) + ChromaDB (vector)
4. **[Dài hạn]** GraphRAG với Neo4j/NetworkX
5. **[Dài hạn]** Conversation Memory trong AgentState
