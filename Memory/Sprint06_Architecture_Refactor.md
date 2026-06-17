# 🏗️ Sprint 06 — Agent Architecture Refactor v6

**Ngày:** 2026-06-15  
**Mục tiêu:** Khôi phục tool-based agent design, tách biệt concerns

---

## Tóm tắt

### Vấn đề đã fix
1. **Orchestrator monolithic (770 dòng)** → Tách thành tools + pipeline modules (340 dòng)
2. **`tools.py` dead code (239 dòng)** → Xóa hoàn toàn, thay bằng 4 tool classes
3. **Preprocessing nằm sai chỗ** → Di chuyển intent_classifier, schema_loader, memory_manager ra khỏi `src/agent/`

### Kiến trúc mới: 3 tầng

```
Preprocessing (src/pipeline/) → Agent Reasoning (src/agent/) → Postprocessing (src/pipeline/)
     ↓                              ↓                              ↓
IntentClassifier              4 Tools (BaseTool)            ConfidenceGate
SchemaLoader                  RetrieveTool                  reject/warn/pass
                              EvaluateTool
                              RewriteTool
                              GenerateTool
```

### Files mới tạo
- `src/agent/tools/` — base.py, retrieve_tool.py, evaluate_tool.py, rewrite_tool.py, generate_tool.py
- `src/pipeline/` — intent_classifier.py, schema_loader.py, confidence_gate.py
- `src/memory/` — memory_manager.py

### Files đã xóa
- `src/agent/tools.py` (dead code)

### Verification
- ✅ Syntax check: 16/16 files OK
- ✅ Import test: All modules chain OK
- ⏳ Runtime test: Pending (cần `streamlit run app.py`)

### Công việc còn lại
1. Xóa 3 file gốc trong `src/agent/` (intent_classifier.py, schema_loader.py, memory_manager.py)
2. Xử lý `src/agent/skills/`
3. Cập nhật SYSTEM_FLOWCHART.md
4. Runtime test với câu hỏi thực
