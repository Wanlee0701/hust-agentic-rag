# 📋 SPRINT LOG #4 — Confidence Gate + Avg-Similarity Check + Dead Code Removal
> **Ngày thực hiện:** 2026-06-09  
> **Phiên bản hệ thống sau sprint:** v4.0  
> **Trạng thái:** ✅ Hoàn thành — Syntax OK, 11/11 verification checks PASS  
> **Tham chiếu:** `Memory/Architecture_Analysis_v4.md`

---

## 1. Vấn đề được fix

### 🔴 CRITICAL #1 — Confidence Gate bị thiếu
**Triệu chứng:** Câu trả lời có confidence 38% vẫn được trả ra cho người dùng như bình thường.  
**Root cause:** `_calculate_confidence()` chỉ tính điểm rồi ghi vào kết quả, **không có code nào dùng điểm đó để quyết định** có trả lời không.

### 🔴 CRITICAL #2 — Hop 1 skip evaluate vô điều kiện
**Triệu chứng:** Chỉ cần tìm được ≥ 2 docs là generate ngay, bất kể similarity score của 2 docs đó là bao nhiêu.  
**Root cause:** Logic `if hop == 0 and len(all_results) >= 2: break` quá đơn giản, không kiểm tra chất lượng docs.

### 🟠 HIGH — Thresholds hardcode / thiếu trong config
**Triệu chứng:** `config.yaml` section `agent` chỉ có `confidence_threshold: 0.75` (không được dùng ở đâu).  
**Root cause:** Các threshold constants nằm rải rác, không được đọc từ config.

### 🟡 MEDIUM — Dead Code
- `_INTENT_CHECK_PROMPT` (prompt cũ từ v2, không được gọi sau khi có IntentClassifier)
- `_check_intent()` method (thay thế bởi `IntentClassifier.classify()` từ v3)

---

## 2. Thay đổi đã thực hiện

### 2.1 `config.yaml` — Agent section
```yaml
# Trước:
agent:
  type: "react"
  max_iterations: 5
  confidence_threshold: 0.75   ← không được dùng

# Sau:
agent:
  type: "react"
  max_iterations: 5
  high_confidence_threshold: 0.65   # ≥ 65%: trả lời bình thường
  low_confidence_threshold: 0.35    # < 35%: từ chối, "không tìm thấy"
  min_avg_similarity: 0.45          # avg sim ≥ 45% → docs tốt, skip rewrite
```

### 2.2 `src/agent/orchestrator.py` — Class constants
```python
class StudentRegulationAgent:
    """AgenticRAG v4 — Luồng thống nhất: [Intent] → Retrieve → [Avg-Sim] → Generate → [Confidence Gate]"""
    MAX_RETRIEVAL_HOPS = 2
    _HIGH_CONF_DEFAULT = 0.65    # fallback nếu không có config
    _LOW_CONF_DEFAULT  = 0.35
    _MIN_AVG_SIM_DEFAULT = 0.45
```

### 2.3 `orchestrator.py` — Đọc threshold từ config
```python
# Trong answer_question(), đọc ngay sau khi khởi tạo state:
agent_config = self.config.get("agent", {})
high_conf   = agent_config.get("high_confidence_threshold", self._HIGH_CONF_DEFAULT)
low_conf    = agent_config.get("low_confidence_threshold",  self._LOW_CONF_DEFAULT)
min_avg_sim = agent_config.get("min_avg_similarity", self._MIN_AVG_SIM_DEFAULT)
```

### 2.4 `orchestrator.py` — Fix CRITICAL #2: Avg-Similarity Check
```python
# Trước (vấn đề):
if hop == 0 and len(all_results) >= 2:
    break  # ← bỏ qua evaluate, generate ngay!

# Sau (fix):
recent_scores = [score for _, score in results[:top_k] if results]
avg_sim = sum(recent_scores) / max(len(recent_scores), 1)

if avg_sim >= min_avg_sim:  # ← kiểm tra CHẤT LƯỢNG, không chỉ SỐ LƯỢNG
    state.add_iteration(...)
    break  # Docs tốt → generate

# Nếu avg_sim thấp → chạy LLM Evaluate → QueryRewrite (như cũ)
```

### 2.5 `orchestrator.py` — Fix CRITICAL #1: Confidence Gate
```python
# Trước (vấn đề):
answer = self._generate_answer(question, context)
confidence = self._calculate_confidence(...)
state.set_answer(answer, confidence=confidence, success=True)  # ← luôn success=True!

# Sau (fix — 3 mức):
raw_answer = self._generate_answer(question, context)
confidence = self._calculate_confidence(all_results, raw_answer, state.iterations)

if confidence < low_conf:       # < 35%
    answer = self._no_result_answer(question)
    state.set_answer(answer, confidence=confidence, success=False)
elif confidence < high_conf:    # 35% - 65%
    answer = raw_answer + "\n\n---\n⚠️ *Lưu ý: Độ tin cậy ở mức trung bình ({:.0%})...*"
    state.set_answer(answer, confidence=confidence, success=True)
else:                           # ≥ 65%
    answer = raw_answer
    state.set_answer(answer, confidence=confidence, success=True)

# Quan trọng: _build_result() now uses state.success instead of hardcoded True
result = self._build_result(answer, confidence, state.success, state, retrieved_chunks)
```

### 2.6 `orchestrator.py` — Xóa dead code
```python
# XÓA: _INTENT_CHECK_PROMPT (22 dòng prompt cũ từ v2)
# → Thay bằng comment: "# _INTENT_CHECK_PROMPT đã được xóa (dead code — thay thế bởi IntentClassifier v3)"

# XÓA: def _check_intent() (23 dòng method cũ từ v2)
# → Thay bằng comment: "# _check_intent() đã xóa (dead code — thay thế bởi IntentClassifier.classify() từ v3)"
```

---

## 3. Luồng mới sau v4

```
[Intent Gate] → Retrieve (top_k=3, thr=0.35)
                    ↓ < 2 docs?
               Fallback (top_k=5, thr=0.25)
                    ↓
          [Avg-Similarity Check]
          avg_sim ≥ 0.45? ──────────────────► Generate
          avg_sim < 0.45?
                    ↓
          [LLM Evaluate: "liên quan?"]
          relevant=True ───────────────────► Generate
          relevant=False + hop < max?
                    ↓
          [QueryRewrite → Retrieve lần 2]
                    ↓
                 Generate
                    ↓
          [Confidence Gate] ← FIX MỚI
          < 35%  → "Không tìm thấy"
          35-65% → Answer + ⚠️ Cảnh báo
          ≥ 65%  → Answer bình thường
                    ↓
          [Save Memory] → Return
```

---

## 4. Test cases sau v4

| Câu hỏi | Confidence | Expected v3 (cũ) | Expected v4 (mới) |
|---|---|---|---|
| Câu rõ ràng, docs tốt | ≥ 65% | Trả lời ✅ | Trả lời ✅ |
| Câu rõ ràng, docs trung bình | 35-65% | Trả lời ✅ | Trả lời + ⚠️ warning |
| Câu rõ ràng, docs kém | < 35% | Trả lời ✅ (BUG!) | "Không tìm thấy" ✅ |
| Câu có 2 docs similarity 0.36 | ~38% | Generate ngay (BUG!) | Evaluate → Rewrite → Re-retrieve |

---

## 5. Verification (11/11 PASS)

```
PASS  Dead prompt removed        (_INTENT_CHECK_PROMPT xóa thành công)
PASS  Dead method removed        (_check_intent() xóa thành công)
PASS  avg_similarity check added (logic mới có mặt)
PASS  Confidence Gate added      (ConfidenceGate comment/logic có mặt)
PASS  high threshold in config   (config key đúng)
PASS  low threshold in config    (config key đúng)
PASS  high_conf variable used    (biến được dùng trong code)
PASS  low_conf variable used     (biến được dùng trong code)
PASS  min_avg_sim variable used  (biến được dùng trong code)
PASS  reject path present        (path < low_conf có mặt)
PASS  answer with warning        (path trung gian có mặt)
```
