# 📋 SPRINT LOG #3 — Hybrid Intent Routing + Conversation Memory
> **Ngày thực hiện:** 2026-06-09  
> **Phiên bản hệ thống sau sprint:** v3.0  
> **Trạng thái:** ✅ Hoàn thành — Syntax OK, sẵn sàng test

---

## 1. Bối cảnh & Yêu cầu

Sau khi demo kết quả cho khách hàng, team nhận được yêu cầu kỹ thuật chính thức (PRD) gồm **2 tính năng cốt lõi** cần phát triển thêm:

| # | Tính năng | Mô tả ngắn |
|---|---|---|
| 1 | **Hybrid Intent Classification & Routing** | Phân loại câu hỏi qua LLM + YAML config, hỏi lại khi thiếu entity cần thiết |
| 2 | **Persistent Conversation Memory** | Nhớ ngữ cảnh phiên chat (Sliding Window K=5), reset bằng nút UI |

**Quyết định kiến trúc đã thống nhất với team:**
- Storage: **Python in-memory dict** (local-first, không cần Redis/MongoDB)
- Intent config: Thêm trực tiếp vào **`config.yaml`** (single source of truth)

---

## 2. Các file đã thay đổi

| File | Trạng thái | Mô tả |
|---|---|---|
| `config.yaml` | ✏️ SỬA | Thêm section `intents` (5 intents) + section `memory` |
| `src/agent/intent_classifier.py` | 🆕 MỚI | Hybrid Intent Classifier: LLM extraction + YAML validation |
| `src/agent/memory_manager.py` | 🆕 MỚI | Conversation Memory: Sliding Window + entity carry-over |
| `src/agent/orchestrator.py` | ✏️ SỬA | Tích hợp IntentClassifier + Memory vào Bước 0; thêm `session_id` |
| `app.py` | ✏️ SỬA | Thêm `session_id`, nút "Phiên chat mới", truyền session vào agent |

---

## 3. Chi tiết kỹ thuật từng thay đổi

### 3.1 `config.yaml` — Intent & Memory Config

Thêm 2 section mới vào cuối file:

**Section `intents`:** Định nghĩa 5 intent là "Ground Truth" cho logic rẽ nhánh.

```yaml
intents:
  GENERAL_REGULATION:        # requires_entities: false → pass thẳng RAG
  ACADEMIC_DISCIPLINE:       # requires_entities: false → pass thẳng RAG
  SCHOLARSHIP:               # requires_entities: false → pass thẳng RAG
  LANGUAGE_REQUIREMENT:      # requires_entities: true → cần nganh_hoc + khoa_hoc
  TUITION_FEE:               # requires_entities: true → cần nganh_hoc + khoa_hoc
```

Mỗi intent có các field:
- `description` — Mô tả để inject vào prompt LLM
- `requires_entities: true/false` — Có cần entity không
- `required_fields: [...]` — Danh sách entity bắt buộc
- `clarification_template` — Câu hỏi làm rõ pre-defined (thay vì auto-generate)
- `examples` — Ví dụ câu hỏi (để tham khảo, không inject vào prompt)

**Section `memory`:**
```yaml
memory:
  enabled: true
  strategy: "sliding_window"
  window_size: 5
  max_context_chars: 1500
```

---

### 3.2 `src/agent/intent_classifier.py` — File mới

**Class: `IntentClassifier`**

**Luồng xử lý:**
```
classify(question, memory_context, memory_entities)
    │
    ├─ _call_llm(question, memory_context)
    │     └─ LLM đọc intent list + context → JSON {intent, entities, confidence}
    │
    ├─ Merge entities: {**memory_entities, **llm_entities}
    │     (LLM có priority cao hơn memory, nhưng memory bổ sung field còn thiếu)
    │
    ├─ _check_required_fields(intent_def, merged_entities)
    │     └─ So sánh với required_fields trong YAML
    │
    └─ needs_clarification?
          True  → _build_clarification() → return IntentResult(needs_clarification=True)
          False → return IntentResult(pass to RAG)
```

**Dataclass `IntentResult`:**
```python
@dataclass
class IntentResult:
    intent_name: str
    entities: Dict[str, Any]      # {"nganh_hoc": "CNTT", "khoa_hoc": "K65"}
    needs_clarification: bool
    clarification_question: str
    missing_fields: List[str]
    confidence: float
    raw_llm_response: str
```

**Extraction Prompt:** Nhúng danh sách intent descriptions + memory context + câu hỏi → LLM trả JSON.

**Xử lý lỗi (Fallback):** Nếu LLM parse thất bại → `needs_clarification=False`, `intent=GENERAL_REGULATION` → luôn pass vào RAG, không bao giờ crash.

---

### 3.3 `src/agent/memory_manager.py` — File mới

**Class: `ConversationMemory`**

**Dataclass `ConversationTurn`:**
```python
@dataclass
class ConversationTurn:
    question: str
    answer: str
    entities: Dict[str, Any]   # ← Điểm đặc biệt: lưu entity bóc tách được
```

**Phương thức chính:**

| Method | Mô tả |
|---|---|
| `add_turn(session_id, q, a, entities)` | Thêm turn, tự cắt khi > window_size |
| `get_context(session_id)` | Trả về plain text K turn gần nhất, giới hạn max_context_chars |
| `get_entities_from_memory(session_id)` | Gộp entity từ toàn window (cũ → mới, mới ghi đè cũ) |
| `reset(session_id)` | Hard delete toàn bộ session |
| `has_session(session_id)` | Kiểm tra session tồn tại |

**Entity Carry-over (tính năng quan trọng):**
```
Turn 1: user nói "Tôi học CNTT K65"
  → entities: {"nganh_hoc": "CNTT", "khoa_hoc": "K65"}

Turn 2: user hỏi "Yêu cầu tiếng Anh?"
  → memory_entities = {"nganh_hoc": "CNTT", "khoa_hoc": "K65"}
  → IntentClassifier merge vào entities của turn 2
  → required_fields đã đủ → KHÔNG hỏi lại!
```

**Singleton `get_memory()`:** Trả về 1 instance duy nhất toàn app, tránh nhiều Streamlit session tạo nhiều instance riêng biệt.

---

### 3.4 `src/agent/orchestrator.py` — Thay đổi lớn

**Import thêm:**
```python
from src.agent.intent_classifier import IntentClassifier
from src.agent.memory_manager import get_memory
```

**`__init__`:** Thêm 2 attribute mới: `self.intent_classifier`, `self.memory`

**2 phương thức init mới:**
- `_initialize_intent_classifier()`: Đọc YAML config, tạo `IntentClassifier` với `llm_invoker` wrapper
- `_initialize_memory()`: Đọc memory config, tạo `ConversationMemory` via `get_memory()`

**`answer_question()` — Signature mới:**
```python
def answer_question(
    self,
    question: str,
    session_id: str = "default",   # ← Tham số mới
    status_callback=None,
) -> Dict[str, Any]:
```

**Bước 0 mới (thay thế `_check_intent` cũ):**
```python
# Lấy context và entity từ memory
memory_context = self.memory.get_context(session_id)
memory_entities = self.memory.get_entities_from_memory(session_id)

# Phân loại câu hỏi
intent_result = self.intent_classifier.classify(question, memory_context, memory_entities)

if intent_result.needs_clarification:
    → return clarification response (dừng luồng)
else:
    → continue to RAG loop
```

**Sau GenerateAnswer — Lưu Memory:**
```python
if self.memory:
    self.memory.add_turn(
        session_id=session_id,
        question=question,
        answer=answer[:500],     # Cắt bớt để tiết kiệm RAM
        entities=intent_result.entities,
    )
```

**Result dict bổ sung thêm keys:**
- `intent_name`: Tên intent LLM phân loại
- `entities`: Entity đã bóc tách
- `needs_clarification`: Luôn `False` khi đến đây

---

### 3.5 `app.py` — Session Management

**Import thêm:** `import uuid`

**Session State mới:**
```python
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
```

**Sidebar — Section "Phiên làm việc":**
- Hiển thị `session_id` rút gọn (8 ký tự đầu)
- Nút **"🗑️ Phiên chat mới"**:
  1. Gọi `agent.memory.reset(session_id)` → xóa memory backend
  2. Sinh UUID mới → `session_id` mới
  3. Clear `st.session_state.messages` → xóa UI history
  4. `st.rerun()`

**Truyền `session_id` vào agent:**
```python
result = agent.answer_question(
    question,
    session_id=st.session_state.session_id,   # ← Mới
    status_callback=update_status,
)
```

**Meta lưu vào message history bổ sung:**
```python
"intent_name": result.get("intent_name", ""),
"entities": result.get("entities", {}),
```

---

## 4. Acceptance Criteria — Kết quả kỳ vọng

| Kịch bản | Input | Expected |
|---|---|---|
| AC-1 | "Bao nhiêu tín chỉ thì bị cảnh cáo?" | `ACADEMIC_DISCIPLINE`, pass thẳng RAG |
| AC-2 | "Học phí một học kỳ là bao nhiêu?" | `TUITION_FEE`, clarification: hỏi ngành + khóa |
| AC-3 | "Học phí ngành CNTT K65 bao nhiêu?" | `TUITION_FEE`, entities đủ, pass RAG |
| AC-4 (Memory) | "Tôi học Cơ điện tử K66" → "Yêu cầu TA?" | Turn 2 dùng entity từ memory → pass RAG không hỏi lại |
| AC-5 (Reset) | Nhấn "Phiên chat mới" → "Học phí của tôi?" | Memory cleared → clarification lại |
| AC-6 (Token limit) | Chat liên tục 50 câu | Window tự cắt ở K=5, không crash |

---

## 5. Luồng xử lý đầy đủ v3 (Updated Architecture)

```
User Question
     │
     ▼
[Memory Manager]
  get_context(session_id)      → plain text K=5 turns gần nhất
  get_entities_from_memory()   → dict entity đã biết từ lịch sử
     │
     ▼
[IntentClassifier.classify()]
  LLM: question + memory_context → {intent, entities, confidence}
  Merge: llm_entities ← memory_entities (carry-over)
  YAML: kiểm tra required_fields
     │
     ├─ needs_clarification = True?
     │    → return clarification_question (dừng)
     │
     └─ False → pass vào RAG
          │
          ▼
     [Multi-hop RAG Loop]  (max 2 hops)
     Hop 1: Retrieve → nếu ≥2 kết quả → Generate ngay (skip Evaluate)
     Hop 2: Retrieve → Evaluate relevance → Generate hoặc QueryRewrite
          │
          ▼
     [GenerateAnswer]
          │
          ▼
     [Memory.add_turn()] ← lưu (question, answer[:500], entities)
          │
          ▼
     Response → UI
```

---

## 6. Lưu ý kỹ thuật quan trọng

### Fallback an toàn
- `IntentClassifier._call_llm()`: Nếu LLM parse lỗi → `intent=GENERAL_REGULATION`, `needs_clarification=False` → luôn đi vào RAG, không crash.
- `_initialize_intent_classifier()`: Nếu không có section `intents` trong config → `self.intent_classifier = None` → skip bước 0, chạy bình thường.
- `_initialize_memory()`: Nếu `memory.enabled = false` → `self.memory = None` → skip toàn bộ memory logic.

### Token Budget cho Memory Context
- `max_context_chars: 1500` — Tổng ký tự context inject vào LLM Intent prompt
- `answer[:500]` — Cắt answer khi lưu vào turn để tránh bộ nhớ phình to
- `window_size: 5` — Tối đa 5 cặp Q&A, khi vượt → tự cắt turn cũ nhất

### Thứ tự ưu tiên Entity
```
Entity từ câu hỏi hiện tại (LLM extract) > Entity từ memory cũ
```
Ví dụ: Nếu lịch sử có `nganh_hoc=CNTT` nhưng câu mới nói `ngành Cơ khí` → dùng `Cơ khí`.

---

## 7. Trạng thái tính năng (Updated Feature Matrix)

| Tính năng | Trạng thái | Ghi chú |
|---|---|---|
| Multi-hop RAG | ✅ Stable | Max 2 hops, skip Evaluate hop 1 |
| Hybrid Intent Routing | ✅ Mới (v3) | 5 intents, YAML + LLM |
| Conversation Memory | ✅ Mới (v3) | Sliding Window K=5 |
| Entity Carry-over | ✅ Mới (v3) | Tự merge entity từ lịch sử |
| Session Reset | ✅ Mới (v3) | Nút UI + hard delete memory |
| Evaluate Fix (relevance) | ✅ v2 | Không còn trigger rewrite vô hạn |
| Asyncio Deadlock Fix | ✅ v2 | Không xóa đoạn event loop patch |
| Đa ngôn ngữ | ✅ v2 | Detect language, reply same lang |
| Hybrid Search (BM25+Vector) | ❌ Chưa | Next sprint |
| GraphRAG / Structured KB | ❌ Chưa | Tương lai |
| Containerization (Docker) | ❌ Chưa | Khi deploy production |

---

## 8. Lệnh test nhanh sau khi chạy lại

```bash
# Khởi động app
streamlit run app.py

# Test trong terminal: syntax check
venv\Scripts\python.exe -c "
import ast
files = ['src/agent/memory_manager.py', 'src/agent/intent_classifier.py',
         'src/agent/orchestrator.py', 'app.py']
[print(f'OK  {f}') for f in files if not ast.parse(open(f, encoding='utf-8').read())]
"
```

**Test cases thủ công theo thứ tự:**

1. `"Bao nhiêu tín chỉ thì bị cảnh cáo?"` → Phải trả lời ngay (no clarification)
2. `"Học phí một học kỳ bao nhiêu?"` → Phải hỏi lại ngành + khóa
3. `"Học phí ngành CNTT K65?"` → Phải trả lời ngay
4. Gõ `"Tôi học Cơ điện tử K66"` → rồi gõ tiếp `"Yêu cầu tiếng Anh?"` → Phải trả lời ngay (không hỏi lại)
5. Nhấn **"🗑️ Phiên chat mới"** → Gõ `"Yêu cầu tiếng Anh?"` → Phải hỏi lại ngành + khóa
