# 📋 SPRINT LOG #5 — Auto-Discovery Intent Schema (Hướng 3)
> **Ngày thực hiện:** 2026-06-11  
> **Phiên bản hệ thống sau sprint:** v5.0  
> **Trạng thái:** ✅ Hoàn thành — Syntax 7/7 PASS, Import tests PASS  
> **Tham chiếu:** `Memory/Sprint04_Confidence_Gate_Fix.md`

---

## 1. Vấn đề được giải quyết

### 🔴 CORE PROBLEM — Intent config bị hardcode, không portable

**Triệu chứng:**  
- Toàn bộ intent definitions (`GENERAL_REGULATION`, `TUITION_FEE`, `LANGUAGE_REQUIREMENT`...) được viết tay trong `config.yaml`.
- Entity names (`nganh_hoc`, `khoa_hoc`, `gpa`) và clarification prompts hardcode trong `intent_classifier.py`.
- `REACT_SYSTEM_PROMPT` hardcode tên "ĐHBK Hà Nội" và danh sách tài liệu cụ thể.

**Root cause:**  
Hệ thống giả định tài liệu nguồn là cố định → cần người dev đọc toàn bộ tài liệu raw để viết đúng intent config → không thể đem đi triển khai cho trường khác.

**Hệ quả:**  
- Để dùng cho trường khác phải viết lại toàn bộ intents thủ công.
- Nếu thêm tài liệu mới, phải cập nhật config thủ công.
- Entity list trong prompt LLM (`nganh_hoc`, `khoa_hoc`...) không thay đổi được theo domain.

---

## 2. Giải pháp: Auto-Discovery (Hướng 3)

### Kiến trúc mới (v5)

```
[Onboarding Pipeline — chạy 1 lần khi nạp tài liệu mới]
    data/*.json  →  SchemaDiscoveryEngine (LLM)  →  university_schema.yaml

[Runtime — mỗi câu hỏi]
    university_schema.yaml  →  SchemaLoader  →  IntentClassifier (dynamic)
                                                     ↓
                                             LLM + dynamic entity list
                                                     ↓
                                         Entity check → Clarification / RAG
```

**Nguyên tắc:** LLM tự đọc tài liệu, tự phát hiện "chiều thông tin phụ thuộc", tự sinh schema → không cần dev biết trước nội dung tài liệu.

---

## 3. Các file thay đổi

### 3.1 `src/agent/schema_loader.py` [NEW]

Module trung gian với **priority chain**:
1. Đọc `university_schema.yaml` (auto-generated) nếu tồn tại.
2. Fallback về `config.yaml['intents']` nếu chưa có schema.

```python
loader = SchemaLoader(config)
intent_config = loader.load()           # → dict intents hợp lệ
domain_entities = loader.load_domain_entities()  # → dict entities từ schema
uni_info = loader.load_university_info()         # → tên trường, doc list
```

**Quan trọng:** Backward compatible — nếu chưa chạy `discover_schema.py`, hệ thống vẫn hoạt động bình thường với config.yaml cũ.

### 3.2 `scripts/discover_schema.py` [NEW]

Script onboarding có 2 giai đoạn LLM:

**Giai đoạn 1 — Phân tích từng tài liệu:**
```
_ANALYZE_DOC_PROMPT:
  Input: 3000 ký tự đầu của mỗi file JSON
  Output: {doc_summary, topic_group, dimension_required, dimensions[], example_questions[]}
```

**Giai đoạn 2 — Tổng hợp schema:**
```
_SYNTHESIZE_PROMPT:
  Input: Kết quả phân tích N tài liệu
  Output: {university_name, intents[], domain_entities[]}
```

**Output `university_schema.yaml`:**
```yaml
university:
  name: "Đại học Bách Khoa Hà Nội"
  generated_at: "2026-06-11T09:00:00"
  source_documents: [...]

intents:
  GENERAL_REGULATION:
    description: "..."
    requires_entities: false
    required_fields: []
    clarification_template: ""
    examples: [...]
  TUITION_FEE:
    requires_entities: true
    required_fields: [nganh_hoc, khoa_hoc]
    clarification_template: "..."
    ...

domain_entities:
  nganh_hoc:
    description: "Ngành học của sinh viên"
    examples: ["CNTT", "Cơ điện tử"]
    clarification_prompt: "Bạn đang học ngành gì?"
    discovered_from: ["QD_NN_K65.json", ...]
  khoa_hoc:
    ...
```

### 3.3 `src/agent/intent_classifier.py` [MODIFY]

**Thay đổi chính:**

```python
# TRƯỚC (v4) — hardcode:
_INTENT_EXTRACTION_PROMPT = """
...
## Câu hỏi của sinh viên ĐHBK Hà Nội
...
entities: {"nganh_hoc": null, "khoa_hoc": null, "gpa": null}
"""

field_labels = {
    "nganh_hoc": "ngành học (ví dụ: CNTT, Cơ điện tử...)",
    "khoa_hoc": "khóa học (ví dụ: K65, K68, K70...)",
    "gpa": "điểm GPA của học kỳ gần nhất",
}

# SAU (v5) — dynamic:
_INTENT_EXTRACTION_PROMPT = """
...
## Các loại thông tin (entity) cần bóc tách:
{entity_list}        ← inject động từ domain_entities schema
...
entities: {entity_json_template}  ← sinh từ schema keys
"""

class IntentClassifier:
    def __init__(self, intent_config, llm_invoker, domain_entities=None):
        # domain_entities=None → dùng _default_entities() (fallback)
        self._domain_entities = domain_entities or self._default_entities()

    def _build_clarification(self, intent_def, missing_fields):
        # Lấy clarification_prompt từ domain_entities schema thay vì dict cứng
        entity_cfg = self._domain_entities.get(field_name, {})
        return entity_cfg.get("clarification_prompt", ...)

    @staticmethod
    def _default_entities():
        # Fallback: nganh_hoc, khoa_hoc, gpa (giữ backward compat)
        return {...}
```

### 3.4 `src/agent/orchestrator.py` [MODIFY]

```python
# TRƯỚC (v4):
def _initialize_intent_classifier(self):
    intent_config = self.config.get("intents", {})  # ← đọc config trực tiếp
    self.intent_classifier = IntentClassifier(intent_config=intent_config, ...)

# SAU (v5):
def _initialize_schema_loader(self):
    self._schema_loader = SchemaLoader(self.config)
    if schema_loader.schema_exists():
        uni_info = schema_loader.load_university_info()
        self._system_prompt = build_system_prompt(uni_info.name, uni_info.doc_list)

def _initialize_intent_classifier(self):
    intent_config = self._schema_loader.load()  # ← qua SchemaLoader
    domain_entities = self._schema_loader.load_domain_entities()
    self.intent_classifier = IntentClassifier(
        intent_config=intent_config,
        domain_entities=domain_entities,  # ← inject động
        ...
    )
```

### 3.5 `src/agent/prompts.py` [MODIFY]

Thêm `build_system_prompt()`:
```python
def build_system_prompt(university_name="", document_list=None) -> str:
    if not university_name and not document_list:
        return REACT_SYSTEM_PROMPT  # backward compat

    # Inject tên trường + danh sách tài liệu vào prompt
    return f"""Bạn là trợ lý AI chuyên về quy định tại {university_name}...
Tài liệu: {doc_lines}..."""
```

### 3.6 `config.yaml` [MODIFY]

```yaml
schema:
  auto_discovery: true
  schema_path: "./university_schema.yaml"
  fallback_to_config_intents: true
  sample_chars_per_doc: 3000
```

### 3.7 `scripts/build_knowledge_base.py` [MODIFY]

Thêm `step_5_discover_schema()` vào pipeline và tích hợp vào `run_full_pipeline()`.

---

## 4. Luồng hệ thống mới (v5)

```
[ONBOARDING — chạy 1 lần]

    python scripts/build_knowledge_base.py
         Step 1: PDF → JSON
         Step 2: Chunking
         Step 3: Vector DB
         Step 4: Test retrieval
    →    Step 5: discover_schema.py
              ├─ Phân tích từng JSON (LLM call x N_docs)
              └─ Tổng hợp → university_schema.yaml

[RUNTIME — mỗi câu hỏi]

    User query
         │
         ▼
    SchemaLoader.load()
    ├─ university_schema.yaml tồn tại? → dùng schema auto-generated
    └─ Không tồn tại? → fallback config.yaml['intents']
         │
         ▼
    IntentClassifier (dynamic entity list từ schema)
         │
         ├─ needs_clarification? → câu hỏi làm rõ (prompt từ schema)
         └─ đủ entity? → RAG Retrieval → Confidence Gate
```

---

## 5. Portability — Dùng cho trường khác

```bash
# Trường A (ĐHBK Hà Nội):
cp data/*.json /project_A/data/
python scripts/build_knowledge_base.py
# → university_schema.yaml A được sinh tự động

# Trường B (ĐH Kinh tế):
cp data_B/*.json /project_B/data/
python scripts/build_knowledge_base.py
# → university_schema.yaml B được sinh tự động
#    (có thể có entity khác: "khoa_phong", "he_dao_tao"...)
```

Không cần viết tay bất kỳ dòng config nào khi onboard trường mới.

---

## 6. Verification (7/7 PASS)

```
PASS  src/agent/schema_loader.py        (syntax OK)
PASS  src/agent/intent_classifier.py    (syntax OK)
PASS  src/agent/orchestrator.py         (syntax OK)
PASS  src/agent/prompts.py              (syntax OK)
PASS  scripts/discover_schema.py        (syntax OK)
PASS  scripts/build_knowledge_base.py   (syntax OK)
PASS  config.yaml                       (YAML valid)
```

**Import tests:**
```
PASS  SchemaLoader — load() với fallback config.yaml OK
PASS  IntentClassifier — default entities OK
PASS  IntentClassifier — custom domain_entities OK
PASS  IntentClassifier — classify() OK
PASS  build_system_prompt() — default returns REACT_SYSTEM_PROMPT OK
PASS  build_system_prompt() — university_name injected OK
```

---

## 7. Backward Compatibility

| Tình huống | Hành vi |
|---|---|
| Chưa chạy `discover_schema.py` | Fallback về `config.yaml['intents']` — không breaking |
| `university_schema.yaml` bị lỗi YAML | Warning log → fallback về config.yaml |
| `domain_entities` trống trong schema | IntentClassifier dùng `_default_entities()` |
| `university_name` trống trong schema | `_system_prompt` dùng `REACT_SYSTEM_PROMPT` mặc định |

---

## 8. Cách sử dụng

### Chạy Auto-Discovery lần đầu:
```bash
# Cách 1: Tích hợp trong full pipeline (recommended)
python scripts/build_knowledge_base.py

# Cách 2: Chạy riêng lẻ sau khi đã có vector DB
python scripts/discover_schema.py
python scripts/discover_schema.py --config ./config.yaml --output ./university_schema.yaml
```

### Kiểm tra schema đã sinh:
```bash
cat university_schema.yaml
```

### Reset schema (sinh lại từ đầu):
```bash
del university_schema.yaml
python scripts/discover_schema.py
```
