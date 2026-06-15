# 📅 DAILY SUMMARY — 2026-06-09
> **Ngày làm việc:** Thứ Hai, 09/06/2026  
> **Hệ thống:** HUST Student Regulation Chatbot — AgenticRAG  
> **Phiên bản kết thúc ngày:** `v4.0-stable`

---

## 🗓️ TỔNG QUAN NGÀY LÀM VIỆC

| Sprint | Nội dung | Trạng thái |
|---|---|---|
| Sprint 03 | Intent Routing + Conversation Memory | ✅ Hoàn thành |
| Architecture Review | Đánh giá kiến trúc, phát hiện regression | ✅ Hoàn thành |
| Sprint 04 | Confidence Gate + Avg-Sim Check + Dead Code | ✅ Hoàn thành |

---

## ✅ CÔNG VIỆC ĐÃ HOÀN THÀNH

### 🔷 Sprint 03 — Hybrid Intent Routing + Conversation Memory

**Vấn đề xuất phát:** Khách hàng yêu cầu 2 tính năng cốt lõi: phân loại câu hỏi tự động và ghi nhớ ngữ cảnh hội thoại.

**Thay đổi kỹ thuật:**

#### File mới tạo
| File | Mô tả |
|---|---|
| `src/agent/intent_classifier.py` | Class `IntentClassifier`: LLM bóc tách intent + entities, YAML kiểm tra required_fields, sinh câu hỏi làm rõ |
| `src/agent/memory_manager.py` | Class `ConversationMemory`: Sliding Window K=5, entity carry-over, singleton pattern |

#### File đã sửa
| File | Thay đổi |
|---|---|
| `config.yaml` | Thêm section `intents` (5 intent definitions) + section `memory` |
| `src/agent/orchestrator.py` | Bước 0 mới: IntentClassifier thay `_check_intent` cũ; thêm `session_id`; lưu memory sau generate |
| `app.py` | Import `uuid`; init `session_id`; nút **"🗑️ Phiên chat mới"**; truyền `session_id` vào agent |

**5 Intent đã định nghĩa:**
- `GENERAL_REGULATION` — Câu hỏi chung về quy chế (không cần entity)
- `ACADEMIC_DISCIPLINE` — Cảnh báo, kỷ luật học tập (không cần entity)
- `SCHOLARSHIP` — Học bổng (không cần entity)
- `LANGUAGE_REQUIREMENT` — Chuẩn ngoại ngữ (**cần** ngành + khóa)
- `TUITION_FEE` — Học phí (**cần** ngành + khóa)

**Luồng entity carry-over:**
```
Turn 1: "Tôi học Cơ điện tử K66" → entities: {nganh_hoc: "Cơ điện tử", khoa_hoc: "K66"}
Turn 2: "Yêu cầu tiếng Anh?"    → memory inject entities → KHÔNG hỏi lại
```

---

### 🔶 Architecture Review — Phân tích & phát hiện regression

**Bối cảnh:** Sau Sprint 03, user test thực tế và phát hiện **Confidence 38% vẫn trả lời** — dấu hiệu có lỗi kiến trúc.

**Phân tích đã thực hiện:**
- Đọc toàn bộ `src/agent/orchestrator.py` (716 dòng)
- Đọc `docs/SYSTEM_FLOWCHART.md` (thiết kế gốc)
- So sánh luồng gốc vs luồng thực tế

**Kết quả phân tích — Đã mất (regression):**

| Thành phần | Thiết kế gốc | Thực tế v3 | Mức độ |
|---|---|---|---|
| Confidence Gate | ✅ `≥ 0.75` mới generate | ❌ Không có | 🔴 Critical |
| Hop 1 Evaluate | ✅ Luôn evaluate | ❌ Skip nếu ≥ 2 docs | 🔴 Critical |
| Confidence config | ✅ Trong config | ❌ Không được đọc | 🟠 High |
| Dead code | ✅ Clean | ❌ 2 artifacts cũ còn tồn tại | 🟡 Medium |

**Output:** File [`Memory/Architecture_Analysis_v4.md`](c:/Users/PC/Desktop/ĐATN/Memory/Architecture_Analysis_v4.md) — đề xuất luồng thống nhất v4 với pseudocode đầy đủ.

---

### 🔷 Sprint 04 — Confidence Gate + Avg-Similarity Fix

**Fix CRITICAL #1 — Confidence Gate** (`orchestrator.py`):

```python
# Trước: generate xong → success=True vô điều kiện
answer = self._generate_answer(...)
state.set_answer(answer, confidence=confidence, success=True)  # BUG!

# Sau: 3 nhánh theo threshold
if confidence < low_conf (0.35):
    → Từ chối: trả "không tìm thấy"
elif confidence < high_conf (0.65):
    → Trả lời + ⚠️ "Độ tin cậy trung bình, vui lòng xác minh lại"
else:
    → Trả lời bình thường
```

**Fix CRITICAL #2 — Avg-Similarity Check** (`orchestrator.py`):

```python
# Trước: đếm số lượng docs
if hop == 0 and len(all_results) >= 2:
    break  # BUG! 2 docs similarity 0.36 cũng generate ngay

# Sau: kiểm tra CHẤT LƯỢNG
avg_sim = sum(scores[:top_k]) / len(scores[:top_k])
if avg_sim >= min_avg_sim (0.45):
    break  # Docs tốt → generate
# else: LLM Evaluate → QueryRewrite
```

**Fix HIGH — Threshold config** (`config.yaml`):

```yaml
agent:
  high_confidence_threshold: 0.65  # ≥ 65%: OK
  low_confidence_threshold: 0.35   # < 35%: từ chối
  min_avg_similarity: 0.45         # avg sim để skip rewrite
```

**Xóa dead code** (`orchestrator.py`):
- ~~`_INTENT_CHECK_PROMPT`~~ (22 dòng prompt cũ v2)
- ~~`def _check_intent()`~~ (23 dòng method cũ v2)

**Verification: 11/11 checks PASS, Syntax OK.**

---

## 📊 TRẠNG THÁI TÍNH NĂNG (Kết thúc ngày 09/06)

| Tính năng | Trạng thái | Phiên bản |
|---|---|---|
| Multi-hop RAG (Retrieve → Evaluate → Rewrite) | ✅ Stable | v1 |
| LLM Evaluate (relevance check) | ✅ Stable | v2 |
| Asyncio Deadlock Fix (Gemini) | ✅ Stable | v2 |
| Đa ngôn ngữ (detect & reply same lang) | ✅ Stable | v2 |
| Hybrid Intent Routing (YAML + LLM) | ✅ Mới | v3 |
| Conversation Memory (Sliding Window K=5) | ✅ Mới | v3 |
| Entity Carry-over giữa các turn | ✅ Mới | v3 |
| Session Reset (nút "Phiên chat mới") | ✅ Mới | v3 |
| **Confidence Gate (3 mức)** | ✅ Mới | **v4** |
| **Avg-Similarity Check (thay skip evaluate)** | ✅ Mới | **v4** |
| **Threshold đọc từ config.yaml** | ✅ Mới | **v4** |

---

## 🏗️ LUỒNG KIẾN TRÚC AGENT v4 (Hiện tại)

```
User Question (session_id)
        │
        ▼
┌───────────────────────────────────────┐
│ BƯỚC 0: INTENT GATE                  │
│ Memory context + entities →           │
│ IntentClassifier.classify()           │
│                                       │
│ needs_clarification?                  │
│   True  → ❓ Hỏi lại người dùng      │
│   False → tiếp tục                   │
└──────────────┬────────────────────────┘
               ▼
┌───────────────────────────────────────┐
│ BƯỚC 1: RETRIEVE                     │
│ top_k=3, threshold=0.35              │
│ Nếu < 2 docs → fallback 0.25, top_k+2│
└──────────────┬────────────────────────┘
               ▼
┌───────────────────────────────────────┐
│ BƯỚC 2: AVG-SIMILARITY CHECK  [v4]   │
│ avg_sim = mean(scores[:top_k])        │
│                                       │
│ avg_sim ≥ 0.45? → Generate ngay      │
│ avg_sim < 0.45? → LLM Evaluate       │
│   relevant=True  → Generate ngay     │
│   relevant=False → QueryRewrite      │
│     → Retrieve lần 2 → Generate      │
└──────────────┬────────────────────────┘
               ▼
┌───────────────────────────────────────┐
│ BƯỚC 3: GENERATE ANSWER              │
│ LLM tổng hợp từ context              │
└──────────────┬────────────────────────┘
               ▼
┌───────────────────────────────────────┐
│ BƯỚC 4: CONFIDENCE GATE  [v4]        │
│                                       │
│ < 35%  → ❌ "Không tìm thấy"         │
│ 35-65% → ⚠️  Answer + cảnh báo       │
│ ≥ 65%  → ✅ Answer bình thường       │
└──────────────┬────────────────────────┘
               ▼
┌───────────────────────────────────────┐
│ BƯỚC 5: SAVE MEMORY                  │
│ memory.add_turn(session_id, q, a[:500], entities)│
└──────────────┬────────────────────────┘
               ▼
          Return to UI
```

---

## 📋 CÔNG VIỆC SẮP TỚI (Next Steps)

### 🔴 Ưu tiên cao — Cần làm trước

| # | Task | Mô tả | File liên quan |
|---|---|---|---|
| 1 | **Test thực tế v4** | Chạy lại 5 AC test cases từ Sprint 03 + test confidence gate với câu hỏi trả về 38% trước đây | `app.py` |
| 2 | **Tune threshold nếu cần** | Sau test, nếu confidence phân phối không hợp lý → điều chỉnh `high_confidence_threshold` / `low_confidence_threshold` trong config.yaml | `config.yaml` |
| 3 | **Cập nhật SYSTEM_FLOWCHART.md** | Bản vẽ kiến trúc trong `docs/` hiện phản ánh thiết kế gốc v1, chưa cập nhật theo v4 | `docs/SYSTEM_FLOWCHART.md` |

### 🟠 Ưu tiên trung bình — Sprint tiếp theo

| # | Task | Mô tả | Độ phức tạp |
|---|---|---|---|
| 4 | **Hybrid Search (BM25 + Vector)** | Kết hợp keyword search (BM25) với vector search để tìm chính xác các từ viết tắt (TDN, KKHT, mã môn học) | 🔴 Cao |
| 5 | **Structured KB cho Ngoại ngữ** | JSON mapping `ngành → {K65: {TOEIC: 600, ...}, K68: {...}}` để trả lời chính xác yêu cầu TA mà không phụ thuộc hoàn toàn vào PDF search | 🟠 Trung bình |
| 6 | **Query Enrichment với Entities** | Khi intent classify ra `{nganh_hoc: "CNTT", khoa_hoc: "K65"}`, tự động bổ sung vào query trước khi retrieve (VD: "Yêu cầu tiếng Anh" → "Yêu cầu tiếng Anh ngành CNTT K65") | 🟡 Thấp |

### 🟡 Ưu tiên thấp — Tương lai

| # | Task | Mô tả |
|---|---|---|
| 7 | **Redis/DB Memory** | Nâng cấp storage từ in-memory dict → Redis/SQLite để persist memory qua restart |
| 8 | **Dockerization** | `Dockerfile` + `docker-compose.yml` để deploy production |
| 9 | **Evaluation Framework** | Script đo RAGAS score (faithfulness, context precision) tự động để track chất lượng qua các phiên bản |

---

## 📂 CÁC FILE QUAN TRỌNG CẦN BIẾT

```
ĐATN/
├── src/agent/
│   ├── orchestrator.py        ← Tim hệ thống (v4: Intent Gate + Avg-Sim + Conf Gate)
│   ├── intent_classifier.py   ← Hybrid Intent (LLM + YAML) [v3]
│   ├── memory_manager.py      ← Sliding Window Memory [v3]
│   ├── prompts.py             ← Prompt templates (REACT system, query refinement)
│   └── state.py               ← AgentState tracking
├── config.yaml                ← Cấu hình trung tâm (intents, memory, agent thresholds)
├── app.py                     ← Streamlit UI (session_id, "Phiên chat mới" button)
│
└── Memory/                    ← Sprint logs & project context
    ├── Overview_task.md           (Project overview, cập nhật v3)
    ├── PROJECT_MEMORY.md          (Ngữ cảnh chi tiết kỹ thuật)
    ├── Architecture_Analysis_v4.md (Phân tích regression + đề xuất luồng v4)
    ├── Sprint03_Intent_Routing_Memory.md
    ├── Sprint04_Confidence_Gate_Fix.md
    └── DailySummary_2026-06-09.md  ← File này
```

---

## 🔑 GHI CHÚ QUAN TRỌNG CHO SESSION KẾ TIẾP

1. **Không xóa asyncio event loop patch** trong `_invoke_llm()` — cần thiết cho Gemini chạy trong Streamlit thread.
2. **Config thresholds** giờ ở `config.yaml → agent → high/low_confidence_threshold`. Nếu muốn điều chỉnh độ nhạy thì sửa ở đây, không hardcode trong code.
3. **`_check_intent()` và `_INTENT_CHECK_PROMPT` đã bị xóa** — nếu merge từ branch cũ cần cẩn thận không đưa chúng trở lại.
4. **IntentClassifier fallback an toàn**: Nếu LLM parse lỗi → `intent=GENERAL_REGULATION`, `needs_clarification=False` → luôn đi vào RAG, không crash.
5. **avg_sim threshold (0.45)** có thể cần tune sau khi test — docs tiếng Anh thường có similarity thấp hơn docs tiếng Việt với câu hỏi tiếng Việt.
