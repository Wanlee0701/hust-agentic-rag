# 🏗️ ĐÁNH GIÁ KIẾN TRÚC AGENT & ĐỀ XUẤT LUỒNG THỐNG NHẤT
> **Ngày phân tích:** 2026-06-09  
> **Tác giả phân tích:** AI Engineer  
> **Mục đích:** So sánh luồng thiết kế gốc vs luồng hiện tại, xác định vấn đề, đề xuất kiến trúc chuẩn

---

## 1. LUỒNG GỐC (SYSTEM_FLOWCHART.md — Thiết kế ban đầu)

Theo `docs/SYSTEM_FLOWCHART.md`, luồng agent thiết kế ban đầu là:

```
START (max_iterations=5, confidence_threshold=0.75)
  │
  └─► [ITERATION N]
        │
        ├─ THINK: Phân tích câu hỏi, xác định từ khóa
        │
        ├─ ACTION: Chọn công cụ từ {retrieve_documents | refine_query | verify_answer}
        │
        ├─ OBSERVATION: Nhận kết quả
        │
        └─ CALCULATE CONFIDENCE (Score = similarity × iterations × source_count)
              │
              ├─ Confidence ≥ 0.75? → GenerateAnswer → FINISH ✅
              │
              └─ Confidence < 0.75? + iterations < 5?
                    └─► Refine query → retry [ITERATION N+1]
```

**Đặc điểm thiết kế gốc:**
- ✅ **Threshold check** cứng: `confidence ≥ 0.75` mới được generate
- ✅ **Fallback threshold**: Nếu không tìm được docs → hạ xuống 0.3
- ✅ **Max 5 iterations** với vòng lặp THINK → ACTION → OBSERVATION đầy đủ
- ✅ **3 tools**: `retrieve_documents`, `refine_query`, `verify_answer`
- ❌ **Không có** Intent Routing / Clarification
- ❌ **Không có** Conversation Memory

---

## 2. LUỒNG HIỆN TẠI (orchestrator.py v3 — Sau các sprint)

Luồng thực tế đang chạy:

```
START (session_id)
  │
  ├─ [BƯỚC 0] Intent Classification (LLM + YAML)
  │     │
  │     ├─ needs_clarification? → return clarification_question (DỪNG)
  │     └─ pass → tiếp tục
  │
  └─ [RAG LOOP] MAX_RETRIEVAL_HOPS = 2
        │
        ├─ [HOP 1] Retrieve(query, top_k=3, threshold=0.35)
        │     │
        │     ├─ < 2 kết quả? → fallback threshold=0.25, top_k+2
        │     │
        │     └─ ≥ 2 kết quả? → SKIP EVALUATE → GenerateAnswer NGAY ← ⚠️ VẤN ĐỀ
        │
        └─ [HOP 2] Nếu hop 1 thất bại:
              │
              ├─ Evaluate(LLM): "Tài liệu có liên quan không?"
              │     relevant=true → GenerateAnswer
              │     relevant=false → QueryRewrite → HOP kết thúc
              │
              └─ GenerateAnswer → tính Confidence → lưu Memory
```

---

## 3. SO SÁNH CHI TIẾT: ĐÃ MẤT GÌ / ĐƯỢC GÌ

### ✅ ĐƯỢC GÌ (tính năng mới thêm)

| Tính năng | Luồng gốc | Luồng hiện tại |
|---|---|---|
| Intent Routing (YAML + LLM) | ❌ | ✅ 5 intents, required_fields |
| Clarification Flow | ❌ | ✅ Hỏi lại khi thiếu entity |
| Conversation Memory | ❌ | ✅ Sliding Window K=5 |
| Entity Carry-over | ❌ | ✅ Gộp entity từ memory |
| Session Reset | ❌ | ✅ Nút "Phiên chat mới" |
| Đa ngôn ngữ | ❌ | ✅ Detect & reply same lang |

### ❌ ĐÃ MẤT (regression so với thiết kế gốc)

| Thành phần | Luồng gốc | Luồng hiện tại | Mức độ nghiêm trọng |
|---|---|---|---|
| **Confidence Threshold Check** | ✅ `≥ 0.75` mới generate | ❌ **KHÔNG CÓ** — generate vô điều kiện | 🔴 CRITICAL |
| **Max Iterations linh hoạt** | ✅ Lên đến 5 iterations | ❌ Cứng 2 hops | 🟠 HIGH |
| **Tool: verify_answer** | ✅ Quality check sau generate | ❌ Bị loại bỏ | 🟠 HIGH |
| **Tool: refine_query (LLM)** | ✅ LLM tạo alternative queries | ⚠️ Thay bằng _rewrite_query (đơn giản hơn) | 🟡 MEDIUM |
| **Hop 1 evaluate** | ✅ Evaluate mọi hop | ❌ Skip evaluate hop 1 (≥2 docs = OK) | 🟡 MEDIUM |
| **Fallback threshold logic** | ✅ Ngưỡng 0.3 + 0.75 | ⚠️ Chỉ có threshold=0.35→0.25 | 🟡 MEDIUM |
| **Confidence-gated generation** | ✅ | ❌ **MISSING** | 🔴 CRITICAL |

---

## 4. PHÂN TÍCH VẤN ĐỀ: TẠI SAO CONFIDENCE 38% VẪN TRẢ LỜI

### Root Cause

```python
# orchestrator.py - _calculate_confidence()
# Hàm này chỉ TÍNH confidence SAU KHI đã generate xong
# Không có code nào dùng kết quả này để QUYẾT ĐỊNH có generate không

answer = self._generate_answer(question, context)
confidence = self._calculate_confidence(all_results, answer, state.iterations)
# ↑ Tính xong → lưu → trả về UI, KHÔNG qua threshold check
```

### Vấn đề cascade

1. **Hop 1 có ≥ 2 kết quả** → Code skip evaluate ngay, generate luôn (bất kể similarity score của 2 docs đó là bao nhiêu — có thể chỉ 0.36)
2. **Sau generate** → `_calculate_confidence()` tính ra 38% → ghi vào result → UI hiển thị "🔴 38%"
3. **Không có guard nào** ngăn việc trả câu trả lời kém chất lượng ra cho người dùng

### Vòng đời Confidence hiện tại

```
Retrieve → [SKIP Evaluate] → Generate → Tính confidence
                ↑                              ↓
           (Chỉ check               Confidence chỉ dùng
            "số lượng")              để HIỂN THỊ, không
                                     gating generation
```

---

## 5. KIẾN TRÚC AGENT THỐNG NHẤT ĐỀ XUẤT (v4)

### Mục tiêu thiết kế

1. **Giữ lại** toàn bộ tính năng mới (Intent, Memory) từ v3
2. **Khôi phục** Confidence threshold gate từ thiết kế gốc
3. **Hợp nhất** vòng lặp ReACT + Multi-hop thành một luồng nhất quán
4. **Đơn giản hóa**: Loại bỏ logic phức tạp không cần thiết

### Sơ đồ luồng thống nhất

```
┌─────────────────────────────────────────────────────────────┐
│                    USER QUESTION                            │
└──────────────────────────┬──────────────────────────────────┘
                           │ session_id
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 0: HYBRID INTENT CLASSIFICATION                        │
│  memory_context + memory_entities → IntentClassifier.classify│
│                                                             │
│  needs_clarification = True? ──────────────────────────────►│
│                               ❓ Return clarification_q     │
│  needs_clarification = False?                               │
└──────────────────────────┬──────────────────────────────────┘
                           │ intent_result, enriched_query
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 1: RETRIEVE (lần 1)                                    │
│  query = question (+ entity hints nếu có)                   │
│  top_k = 3, threshold = 0.35                                │
│  < 2 kết quả? → fallback threshold=0.25, top_k=5           │
└──────────────────────────┬──────────────────────────────────┘
                           │ results_hop1
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 2: PRE-CONFIDENCE ESTIMATE                             │
│  Tính avg_similarity từ top results                         │
│  avg_similarity ≥ MIN_SIM (0.45)? → tiếp tục               │
│  avg_similarity < 0.45? → QueryRewrite → Retrieve lần 2    │
└──────────────────────────┬──────────────────────────────────┘
                           │ all_results (dedup merged)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 3: RETRIEVE LẦN 2 (chỉ nếu lần 1 thất bại)           │
│  rewritten_query = _rewrite_query(question, reason)         │
│  Retrieve lại, merge kết quả (dedup)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │ all_results (final)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 4: LLM EVALUATE (quality gate)                         │
│  Đánh giá: "Tài liệu có đủ để trả lời không?"              │
│  relevant = False + không còn hop → trả "không tìm thấy"   │
│  relevant = True → tiếp tục                                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ approved context
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 5: GENERATE ANSWER                                     │
│  LLM tổng hợp câu trả lời từ context                       │
└──────────────────────────┬──────────────────────────────────┘
                           │ raw_answer
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 6: CONFIDENCE SCORING + THRESHOLD GATE ← KHÔI PHỤC   │
│  confidence = _calculate_confidence(results, answer, hops)  │
│                                                             │
│  confidence ≥ HIGH_THRESHOLD (0.65)?                        │
│    → success=True, trả về answer bình thường               │
│                                                             │
│  LOW_THRESHOLD (0.35) ≤ confidence < HIGH_THRESHOLD?        │
│    → success=True, answer kèm CẢNH BÁO độ tin cậy thấp    │
│      "⚠️ Câu trả lời có thể chưa đầy đủ, vui lòng kiểm tra"│
│                                                             │
│  confidence < LOW_THRESHOLD (0.35)?                         │
│    → success=False, trả về "không tìm thấy" message        │
└──────────────────────────┬──────────────────────────────────┘
                           │ final_result
                           ▼
┌─────────────────────────────────────────────────────────────┐
│ BƯỚC 7: SAVE TO MEMORY                                      │
│  memory.add_turn(session_id, question, answer, entities)    │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
                    ✅ Return to UI
```

---

## 6. CÁC THÔNG SỐ CHUẨN (Constants)

| Tham số | Giá trị đề xuất | Lý do |
|---|---|---|
| `MAX_RETRIEVAL_HOPS` | 2 | Giữ nguyên, đủ cho 2 lần retrieve |
| `MIN_SIMILARITY_THRESHOLD` | 0.35 | Vector threshold cơ bản |
| `FALLBACK_SIMILARITY` | 0.25 | Mở rộng khi ít kết quả |
| `MIN_DOC_COUNT` | 2 | Ít nhất 2 docs để generate |
| `HIGH_CONFIDENCE_THRESHOLD` | 0.65 | Generate bình thường (hạ từ 0.75 → 0.65 vì tính confidence hiện tại hơi thấp) |
| `LOW_CONFIDENCE_THRESHOLD` | 0.35 | Dưới mức này = "không tìm thấy" |
| `WINDOW_SIZE` | 5 | Memory window |

> **Lý do hạ HIGH_THRESHOLD từ 0.75 → 0.65:** Hàm `_calculate_confidence` hiện tại có max score khoảng 0.70-0.85 trong điều kiện lý tưởng (3 docs + answer có số + thuật ngữ pháp lý + 1-2 hops). Giữ ngưỡng 0.75 sẽ gây reject quá nhiều câu trả lời tốt.

---

## 7. FILE CẦN SỬA ĐỂ ĐẠT LUỒNG THỐNG NHẤT

### 7.1 `src/agent/orchestrator.py` — Thay đổi chính

**[A] Thêm `CONFIDENCE_THRESHOLD` constants:**
```python
HIGH_CONFIDENCE_THRESHOLD = 0.65   # Trả lời bình thường
LOW_CONFIDENCE_THRESHOLD = 0.35    # Dưới này → không tìm thấy
```

**[B] Thay logic "Hop 1 skip evaluate" bằng PRE-CONFIDENCE:**
```python
# Thay vì: if hop == 0 and len(results) >= 2: break
# Dùng: kiểm tra avg similarity của docs tìm được
avg_sim = sum(score for _, score in results[:top_k]) / max(len(results[:top_k]), 1)
if avg_sim < 0.45 and hop < MAX_RETRIEVAL_HOPS - 1:
    # Tài liệu similarity thấp → rewrite và thử lại
    rewritten = self._rewrite_query(...)
    continue
```

**[C] Thêm Confidence Gate SAU khi generate:**
```python
answer = self._generate_answer(question, context)
confidence = self._calculate_confidence(all_results, answer, state.iterations)

if confidence < self.LOW_CONFIDENCE_THRESHOLD:
    # Trả về "không tìm thấy"
    answer = self._no_result_answer(question)
    state.set_answer(answer, confidence=confidence, success=False)
elif confidence < self.HIGH_CONFIDENCE_THRESHOLD:
    # Thêm cảnh báo vào câu trả lời
    answer = answer + "\n\n---\n⚠️ *Lưu ý: Độ tin cậy thấp ({:.0%}). Vui lòng xác minh lại với tài liệu gốc.*".format(confidence)
    state.set_answer(answer, confidence=confidence, success=True)
else:
    state.set_answer(answer, confidence=confidence, success=True)
```

**[D] Xóa `_check_intent` cũ** (đã được thay bằng IntentClassifier nhưng vẫn còn code cũ trong file từ dòng 551):
```python
# Xóa method _check_intent() dòng 551-569 (dead code)
```

### 7.2 `config.yaml` — Thêm threshold constants

```yaml
agent:
  type: "react"
  max_iterations: 5
  confidence_threshold: 0.65       # HIGH threshold
  low_confidence_threshold: 0.35   # LOW threshold (dưới = không tìm thấy)
  min_avg_similarity: 0.45         # Ngưỡng avg similarity để skip rewrite
```

---

## 8. VẤN ĐỀ PHỤ CẦN LƯU Ý

### 8.1 Dead Code: `_check_intent()` cũ vẫn còn

File `orchestrator.py` dòng 551-569 vẫn còn method `_check_intent()` từ v2 (trước khi có `IntentClassifier`). Method này **không được gọi** ở đâu nhưng chiếm code và gây nhầm lẫn. Cần xóa.

### 8.2 `_INTENT_CHECK_PROMPT` cũ vẫn còn

Dòng 123-143 vẫn còn prompt `_INTENT_CHECK_PROMPT` từ v2, không được dùng. Cần xóa.

### 8.3 Intent Classifier gọi LLM lần 1 → RAG cũng gọi LLM

Mỗi câu hỏi hiện tại tốn **3 LLM calls** cho path thông thường:
1. `IntentClassifier.classify()` → 1 call
2. `_evaluate_context()` (nếu hop 2) → 1 call
3. `_generate_answer()` → 1 call

Với Gemini Flash mỗi call ~2-4s, tổng ~6-12s. Có thể tối ưu bằng cách bỏ evaluate ở hop 2 nếu avg_similarity đủ cao.

### 8.4 Memory add_turn signature mismatch

`orchestrator.py` gọi `memory.add_turn(..., intent_name=..., needs_clarification=...)` nhưng `memory_manager.py` cũng có các tham số đó — **nhất quán**, không có lỗi.

---

## 9. PRIORITY FIX LIST

| # | Vấn đề | File | Mức độ |
|---|---|---|---|
| 1 | **Thêm Confidence Gate** — generate xong phải check threshold | `orchestrator.py` | 🔴 CRITICAL |
| 2 | **Thay "skip evaluate hop 1"** bằng avg_similarity check | `orchestrator.py` | 🔴 CRITICAL |
| 3 | **Thêm threshold vào config.yaml** | `config.yaml` | 🟠 HIGH |
| 4 | **Xóa dead code** `_check_intent()` và `_INTENT_CHECK_PROMPT` | `orchestrator.py` | 🟡 MEDIUM |
| 5 | Cập nhật `SYSTEM_FLOWCHART.md` theo luồng thực tế v4 | `docs/` | 🟡 MEDIUM |

---

## 10. LUỒNG THỐNG NHẤT — MÃ PSEUDOCODE ĐẦY ĐỦ

```python
def answer_question(question, session_id, status_callback):
    
    # === BƯỚC 0: INTENT GATE ===
    memory_ctx = memory.get_context(session_id)
    memory_ent = memory.get_entities_from_memory(session_id)
    intent = intent_classifier.classify(question, memory_ctx, memory_ent)
    
    if intent.needs_clarification:
        memory.add_turn(session_id, question, intent.clarification_question, ...)
        return CLARIFICATION_RESPONSE
    
    # === BƯỚC 1-3: MULTI-HOP RETRIEVE ===
    current_query = question
    all_results = []
    
    for hop in range(MAX_RETRIEVAL_HOPS=2):
        results = retrieve(current_query, top_k=3, threshold=0.35)
        if len(results) < 2:
            results = retrieve(current_query, top_k=5, threshold=0.25)
        
        merge_dedup(all_results, results)
        
        if not all_results:
            break
        
        # === BƯỚC 2: PRE-CONFIDENCE CHECK (thay cho "skip evaluate") ===
        avg_sim = avg([score for _, score in results[:3]])
        
        if avg_sim >= MIN_AVG_SIM (0.45):
            break  # Docs tốt → thoát vòng lặp, sang generate
        
        if hop < MAX_RETRIEVAL_HOPS - 1:
            # === BƯỚC 3: LLM EVALUATE → REWRITE ===
            is_relevant, reason = evaluate_context(question, context)
            if is_relevant:
                break
            current_query = rewrite_query(question, reason)
    
    if not all_results:
        return NO_RESULT_RESPONSE
    
    # === BƯỚC 4: GENERATE ===
    context = build_context(all_results)
    raw_answer = generate_answer(question, context)
    
    # === BƯỚC 5: CONFIDENCE GATE ← ĐIỂM BỊ THIẾU ===
    confidence = calculate_confidence(all_results, raw_answer, hops)
    
    if confidence < LOW_THRESHOLD (0.35):
        return NO_RESULT_RESPONSE (confidence quá thấp)
    
    if confidence < HIGH_THRESHOLD (0.65):
        answer = raw_answer + WARNING_MESSAGE
        success = True
    else:
        answer = raw_answer
        success = True
    
    # === BƯỚC 6: SAVE MEMORY ===
    memory.add_turn(session_id, question, answer[:500], intent.entities)
    
    return {answer, confidence, success, intent_name, entities, chunks}
```

---

## 11. TỔNG KẾT

| Câu hỏi | Trả lời |
|---|---|
| Tại sao confidence 38% vẫn trả lời? | Không có threshold gate sau bước generate |
| Luồng mất gì so với thiết kế gốc? | Confidence-gated generation, verify_answer tool, max 5 iterations linh hoạt |
| Luồng được gì so với thiết kế gốc? | Intent routing, clarification, conversation memory, entity carry-over |
| Fix quan trọng nhất? | Thêm Confidence Gate + thay "skip evaluate hop 1" bằng avg_similarity check |
| Cần bao nhiêu file để sửa? | 2 file: `orchestrator.py` + `config.yaml` |
