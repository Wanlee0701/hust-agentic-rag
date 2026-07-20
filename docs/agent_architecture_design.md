# TÀI LIỆU KỸ THUẬT
# Thiết Kế Kiến Trúc Hệ Thống Agent Hỏi Đáp Quy Chế Sinh Viên
## AgenticRAG v6 — Tool-Based Orchestrator

---

**Dự án:** Hệ thống chatbot tư vấn quy chế đào tạo (Đồ án tốt nghiệp)
**Phiên bản:** 6.0 (Tool-Based, Auto-Discovery Schema)
**Ngày:** 2026-06-17
**Tác giả:** Wanlee0701

---

## MỤC LỤC

1. [Tổng quan kiến trúc](#1-tổng-quan-kiến-trúc)
2. [Luồng xử lý tổng thể](#2-luồng-xử-lý-tổng-thể)
3. [Tầng 1 — Preprocessing](#3-tầng-1--preprocessing)
4. [Tầng 2 — Agent Reasoning](#4-tầng-2--agent-reasoning)
5. [Tầng 3 — Postprocessing](#5-tầng-3--postprocessing)
6. [Hạ tầng hỗ trợ (Infrastructure)](#6-hạ-tầng-hỗ-trợ-infrastructure)
7. [Cấu trúc dữ liệu chính](#7-cấu-trúc-dữ-liệu-chính)
8. [Sơ đồ luồng con chi tiết](#8-sơ-đồ-luồng-con-chi-tiết)
9. [Bảng tổng hợp cấu hình](#9-bảng-tổng-hợp-cấu-hình)

---

## 1. TỔNG QUAN KIẾN TRÚC

### 1.1 Mục tiêu hệ thống

Hệ thống xây dựng một **Agentic RAG** (Retrieval-Augmented Generation với vòng lặp reasoning chủ động) cho phép sinh viên hỏi đáp về quy chế đào tạo đại học. Thay vì pipeline RAG tuyến tính một chiều, agent có khả năng:

- **Phân loại ý định** câu hỏi và yêu cầu làm rõ khi thiếu thông tin
- **Đánh giá chất lượng** tài liệu thu được và **viết lại câu hỏi** khi cần
- **Đa bước tìm kiếm** (multi-hop retrieval) qua vòng lặp ReACT
- **Kiểm soát đầu ra** qua cơ chế Confidence Gate nhiều ngưỡng
- **Ghi nhớ hội thoại** để tái sử dụng thông tin qua các lượt

### 1.2 Nguyên lý thiết kế

| Nguyên lý | Biểu hiện trong mã nguồn |
|-----------|--------------------------|
| **Modular Tools** | Mỗi bước reasoning là một `BaseTool` riêng biệt (`RetrieveTool`, `EvaluateTool`, `RewriteTool`, `GenerateTool`) |
| **Separation of Concerns** | Pipeline (`src/pipeline/`), Agent (`src/agent/`), Memory (`src/memory/`) tách bạch hoàn toàn |
| **Schema-Driven** | Intent & entity schema đọc từ `university_schema.yaml`, không hardcode |
| **Graceful Degradation** | Mọi bước đều có fallback (threshold hạ xuống, intent GENERAL_REGULATION, v.v.) |
| **ReACT Pattern** | Thought → Action → Observation lặp lại tối đa `MAX_RETRIEVAL_HOPS = 2` |

### 1.3 Sơ đồ phân lớp module

```
┌─────────────────────────────────────────────────────────────────────┐
│                          GIAO DIỆN (Streamlit UI / API)             │
│                    answer_question(question, session_id)            │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                     src/agent/orchestrator.py                       │
│                    StudentRegulationAgent                           │
│  ┌──────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │ src/pipeline │  │    src/agent/tools   │  │   src/memory     │  │
│  │ ─────────── │  │ ──────────────────── │  │ ──────────────── │  │
│  │ IntentClass. │  │ RetrieveTool         │  │ ConversationMem. │  │
│  │ ConfidenceG. │  │ EvaluateTool         │  │ get_memory()     │  │
│  │ SchemaLoader │  │ RewriteTool          │  └──────────────────┘  │
│  └──────────────┘  │ GenerateTool         │                        │
│                    └──────────────────────┘                        │
└─────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                          HẠ TẦNG (Infrastructure)                   │
│  ┌────────────────┐  ┌─────────────────────┐  ┌──────────────────┐ │
│  │ src/embeddings │  │  src/embeddings      │  │   LLM Factory    │ │
│  │ EmbeddingModel │  │  VectorDatabaseMgr   │  │  Ollama / Gemini │ │
│  │ (BAAI/bge-m3)  │  │  (ChromaDB)          │  │  _build_llm()    │ │
│  └────────────────┘  └─────────────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. LUỒNG XỬ LÝ TỔNG THỂ

### 2.1 Sơ đồ luồng tổng thể (Overall Flow)

```
╔══════════════════════════════════════════════════════════════════╗
║                    NGƯỜI DÙNG (Sinh viên)                        ║
║              Câu hỏi: "Tôi có thể đăng ký học lại không?"       ║
╚══════════════════════════════╦═══════════════════════════════════╝
                               │ question + session_id
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│              TẦNG 1: PREPROCESSING                               │
│                                                                  │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐   │
│  │ SchemaLoader│───▶│MemoryManager │───▶│ IntentClassifier  │   │
│  │ (YAML load) │    │(get context) │    │  (LLM + Schema)   │   │
│  └─────────────┘    └──────────────┘    └─────────┬─────────┘   │
│                                                   │             │
│                          ┌──────────────────────┐ │             │
│                          │  needs_clarification? │◀┘             │
│                          └──────┬───────────────┘               │
│                                 │                               │
│               YES ◀─────────────┤───────────────▶ NO           │
│                │                                    │           │
│     Trả về câu hỏi làm rõ                          │           │
│     (lưu memory + return)                           │           │
└─────────────────────────────────────────────────────┼───────────┘
                                                      │ intent_result
                                                      ▼
┌──────────────────────────────────────────────────────────────────┐
│              TẦNG 2: AGENT REASONING (ReACT Loop)                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  for hop in range(MAX_RETRIEVAL_HOPS = 2):              │    │
│  │                                                         │    │
│  │  ┌─────────────┐                                        │    │
│  │  │ RetrieveTool│ ── ChromaDB similarity search ──▶ docs │    │
│  │  └──────┬──────┘                                        │    │
│  │         │ results                                       │    │
│  │  ┌──────▼──────┐                                        │    │
│  │  │EvaluateTool │ ── avg_sim check / LLM evaluate ──────▶│    │
│  │  └──────┬──────┘                                        │    │
│  │         │                                               │    │
│  │    relevant? ──YES──▶ [break, go to Generate]           │    │
│  │         │                                               │    │
│  │        NO                                               │    │
│  │         │                                               │    │
│  │  ┌──────▼──────┐                                        │    │
│  │  │ RewriteTool │ ── LLM rewrite query ──▶ new_query     │    │
│  │  └─────────────┘                                        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ GenerateTool ── LLM synthesis ──▶ raw_answer            │    │
│  └─────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────┬───────────────────────┘
                                           │ raw_answer + results
                                           ▼
┌──────────────────────────────────────────────────────────────────┐
│              TẦNG 3: POSTPROCESSING                              │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ConfidenceGate.calculate_confidence(results, answer, n)  │   │
│  │  → score = f(doc_count, answer_quality, iterations)      │   │
│  └──────────────────────┬───────────────────────────────────┘   │
│                         │ confidence score                       │
│  ┌──────────────────────▼───────────────────────────────────┐   │
│  │ ConfidenceGate.evaluate(confidence, answer, question)    │   │
│  │                                                          │   │
│  │   < 0.35 → REJECT ──▶ "Không tìm thấy thông tin..."    │   │
│  │   0.35–0.65 → WARN ──▶ answer + ⚠️ cảnh báo độ tin cậy │   │
│  │   ≥ 0.65 → PASS ──▶ answer bình thường                  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ConversationMemory.add_turn(session_id, q, a, entities)  │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────┬───────────────────────┘
                                           │ Dict kết quả
                                           ▼
╔══════════════════════════════════════════════════════════════════╗
║  { answer, confidence, success, state, retrieved_chunks,        ║
║    intent_name, entities, needs_clarification }                 ║
╚══════════════════════════════════════════════════════════════════╝
```

### 2.2 Tóm tắt 3 tầng xử lý

| Tầng | Vai trò | Module chính | Input | Output |
|------|---------|-------------|-------|--------|
| **Preprocessing** | Hiểu ý định, chuẩn bị ngữ cảnh | `IntentClassifier`, `SchemaLoader`, `ConversationMemory` | `question` (raw) | `IntentResult` + context enriched |
| **Agent Reasoning** | Tìm kiếm, đánh giá, tổng hợp | `RetrieveTool`, `EvaluateTool`, `RewriteTool`, `GenerateTool` | `IntentResult` | `raw_answer` + `all_results` |
| **Postprocessing** | Kiểm soát chất lượng, lưu trữ | `ConfidenceGate`, `ConversationMemory` | `raw_answer` + `confidence` | Final `answer` + persisted state |

---

## 3. TẦNG 1 — PREPROCESSING

### 3.1 Mô tả chức năng

Tầng Preprocessing đảm nhiệm ba nhiệm vụ: **(a)** tải schema định nghĩa intent từ nguồn ưu tiên; **(b)** nạp ngữ cảnh hội thoại từ bộ nhớ phiên; **(c)** phân loại ý định và quyết định có cần yêu cầu làm rõ không.

### 3.2 Sơ đồ luồng Preprocessing

```
┌────────────────────────────────────────────────────────────────────┐
│                 PREPROCESSING FLOW                                 │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [INPUT] question (str) + session_id (str)                         │
│                │                                                   │
│                ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                  SchemaLoader.load()                         │  │
│  │                                                             │  │
│  │  Ưu tiên 1: university_schema.yaml ─────────────┐          │  │
│  │                                                  │ intents  │  │
│  │  Ưu tiên 2: config.yaml['intents'] (fallback) ──┘          │  │
│  │                                                             │  │
│  │  + load_domain_entities() → entity schema                   │  │
│  │  + load_university_info() → tên trường, tài liệu            │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                │ intent_config                                     │
│                ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              ConversationMemory                             │  │
│  │                                                             │  │
│  │  get_context(session_id)                                    │  │
│  │  → Lấy K turn gần nhất (sliding window, K=5)               │  │
│  │  → Nối thành plain text (≤ 1500 ký tự)                     │  │
│  │                                                             │  │
│  │  get_entities_from_memory(session_id)                       │  │
│  │  → Gộp entity từ toàn bộ window (carry-over)               │  │
│  │  → { "nganh_hoc": "CNTT", "khoa_hoc": "K68", ... }         │  │
│  │                                                             │  │
│  │  get_last_clarification_intent(session_id)                  │  │
│  │  → Nếu turn trước cần clarify → trả về previous_intent     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                │ memory_context + memory_entities + prev_intent    │
│                ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              IntentClassifier.classify()                    │  │
│  │                                                             │  │
│  │  Bước 1: _call_llm(question, memory_context, prev_intent)   │  │
│  │    → Sinh prompt với intent_list + entity_list              │  │
│  │    → LLM trả JSON: { intent, entities, confidence }         │  │
│  │    → Parse JSON (chiến lược greedy brace / regex)           │  │
│  │    → Fallback: GENERAL_REGULATION nếu parse thất bại        │  │
│  │                                                             │  │
│  │  Bước 2: Merge entities                                     │  │
│  │    merged = {**memory_entities, **llm_entities (non-null)}  │  │
│  │    (LLM ưu tiên hơn memory — câu hỏi hiện tại cụ thể hơn)  │  │
│  │                                                             │  │
│  │  Bước 3: Heuristic clarification response detection         │  │
│  │    Nếu previous_intent tồn tại + question ngắn (≤15 từ)     │  │
│  │    → Giả định user đang trả lời clarification               │  │
│  │    → Reuse previous_intent (không đổi intent)               │  │
│  │                                                             │  │
│  │  Bước 4: _check_required_fields(intent_def, merged_entities)│  │
│  │    required = intent_def["required_fields"]                 │  │
│  │    missing = [f for f in required if not merged.get(f)]     │  │
│  │    needs_clarification = bool(missing)                      │  │
│  │                                                             │  │
│  │  Bước 5: _build_clarification(intent_def, missing_fields)   │  │
│  │    Ưu tiên: clarification_template trong schema             │  │
│  │    Fallback: ghép clarification_prompt của từng entity      │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                │ IntentResult                                      │
│                ▼                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              Clarification Gate (trong orchestrator)        │  │
│  │                                                             │  │
│  │  intent_result.needs_clarification?                         │  │
│  │                                                             │  │
│  │  ── YES ──▶ Lưu memory (clarification turn)                 │  │
│  │             Return { answer: clarification_question,        │  │
│  │                      needs_clarification: True, ... }       │  │
│  │                                                             │  │
│  │  ── NO  ──▶ Tiếp tục sang Tầng 2 (Agent Reasoning)         │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                    │
│  [OUTPUT] IntentResult { intent_name, entities,                    │
│           needs_clarification, clarification_question }            │
└────────────────────────────────────────────────────────────────────┘
```

### 3.3 Cơ chế phân loại Intent

IntentClassifier hoạt động theo mô hình **Hybrid**: kết hợp LLM (phân tích ngữ nghĩa) với Schema (kiểm tra business logic).

```
         HYBRID INTENT CLASSIFICATION
         ──────────────────────────────

  question + memory_context
          │
          ▼
  ┌─────────────┐         ┌──────────────────────────────────────┐
  │   LLM Call  │──JSON──▶│  { "intent": "HOC_BONG_KKHT",        │
  │  (Gemini/   │         │    "entities": {                     │
  │   Ollama)   │         │      "nganh_hoc": "CNTT",            │
  └─────────────┘         │      "khoa_hoc": null,               │
                          │      "gpa": "3.5"                    │
                          │    },                                │
                          │    "confidence": 0.92               │
                          │  }                                   │
                          └──────────────┬───────────────────────┘
                                         │
                    ┌────────────────────▼───────────────────────┐
                    │        Schema Validation                    │
                    │                                            │
                    │  intent_def["requires_entities"] == True?  │
                    │      required_fields: ["nganh_hoc",        │
                    │                        "khoa_hoc", "gpa"]  │
                    │                                            │
                    │  Merge với memory_entities:                │
                    │    nganh_hoc: "CNTT" (từ LLM)              │
                    │    khoa_hoc: null → MISSING!               │
                    │    gpa: "3.5" (từ LLM)                     │
                    │                                            │
                    │  missing_fields = ["khoa_hoc"]             │
                    │  needs_clarification = True                │
                    └────────────────────────────────────────────┘
                                         │
                                         ▼
                    "Bạn vui lòng cho biết bạn thuộc khóa nào?
                     (ví dụ: K65, K68, K70...)"
```

### 3.4 Cơ chế bộ nhớ hội thoại (Sliding Window Memory)

```
  SESSION: "user_abc"    WINDOW_SIZE = 5

  ┌────────────────────────────────────────────────────────┐
  │  Turn 1 │ Q: "Học bổng KKHT yêu cầu GPA bao nhiêu?"  │
  │         │ A: "Cần GPA ≥ 3.2 theo Điều 15..."          │
  │         │ entities: { gpa: null, nganh_hoc: null }     │
  ├─────────┼──────────────────────────────────────────────┤
  │  Turn 2 │ Q: "Tôi học CNTT, GPA 3.5"                  │
  │         │ A: "(clarification)"                        │
  │         │ entities: { nganh_hoc: "CNTT", gpa: "3.5" } │
  │         │ needs_clarification: True                    │
  ├─────────┼──────────────────────────────────────────────┤
  │  Turn 3 │ Q: "Khóa K68"                               │
  │         │ entities: { khoa_hoc: "K68" }               │
  └─────────┴──────────────────────────────────────────────┘

  get_entities_from_memory() →
    { nganh_hoc: "CNTT", gpa: "3.5", khoa_hoc: "K68" }
    (gộp tất cả, turn mới ghi đè turn cũ)

  get_context() →
    "Người dùng: Học bổng KKHT yêu cầu GPA bao nhiêu?
     Bot: Cần GPA ≥ 3.2 theo Điều 15...
     ---
     Người dùng: Tôi học CNTT, GPA 3.5
     Bot: (clarification)
     ---
     Người dùng: Khóa K68"
    (≤ 1500 ký tự)
```

---

## 4. TẦNG 2 — AGENT REASONING

### 4.1 Mô tả chức năng

Tầng Agent Reasoning triển khai vòng lặp **ReACT** (Reason + Act) với tối đa `MAX_RETRIEVAL_HOPS = 2` lần tìm kiếm. Mỗi vòng gồm 3 công cụ (Retrieve → Evaluate → Rewrite nếu cần), kết thúc bằng Generate. Toàn bộ trạng thái được lưu trong `AgentState`.

### 4.2 Sơ đồ luồng Agent Reasoning (ReACT Loop)

```
┌────────────────────────────────────────────────────────────────────┐
│                    AGENT REASONING FLOW                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [INPUT] question + IntentResult                                   │
│          current_query = question                                  │
│          all_results = []                                          │
│          state = AgentState(query, max_iterations)                 │
│                                                                    │
│  ╔═══════════════════════════════════════════════════════════════╗ │
│  ║         for hop in range(MAX_RETRIEVAL_HOPS = 2):            ║ │
│  ║                                                               ║ │
│  ║  ┌──────────────────────────────────────────────────────┐    ║ │
│  ║  │ TOOL 1: RetrieveTool.execute(query=current_query)    │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  ChromaDB.similarity_search_with_score(query, k)     │    ║ │
│  ║  │  ─ Trả về List[(Document, L2_distance)]              │    ║ │
│  ║  │  ─ Chuyển đổi: sim = 1 / (1 + distance)             │    ║ │
│  ║  │  ─ Filter: sim >= threshold (default 0.35)           │    ║ │
│  ║  │  ─ Fallback: nếu < 2 kết quả → hạ threshold = 0.25  │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  state.add_iteration(thought, "RetrieveTool", ...)   │    ║ │
│  ║  │  all_results = merge(all_results, new_results)       │    ║ │
│  ║  └──────────────────────────────┬───────────────────────┘    ║ │
│  ║                                 │ results                     ║ │
│  ║              empty? ───YES──────┼──────▶ BREAK               ║ │
│  ║                                 │                             ║ │
│  ║  ┌──────────────────────────────▼───────────────────────┐    ║ │
│  ║  │ TOOL 2: EvaluateTool.execute(question, results, ...)  │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  TẦNG ĐÁNH GIÁ 1 (nhanh): Avg-Similarity Check       │    ║ │
│  ║  │    avg_sim = mean(scores[:top_k])                    │    ║ │
│  ║  │    avg_sim >= min_avg_sim (0.45)? → relevant=True    │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  TẦNG ĐÁNH GIÁ 2 (chậm — chỉ khi avg_sim thấp):     │    ║ │
│  ║  │    LLM evaluate context vs question                  │    ║ │
│  ║  │    Parse JSON: { relevant: bool, reason: str }       │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  state.add_iteration(thought, "EvaluateTool", ...)   │    ║ │
│  ║  └──────────────────────────────┬───────────────────────┘    ║ │
│  ║                                 │ eval_data                   ║ │
│  ║            relevant? ──YES──────┼──────▶ BREAK               ║ │
│  ║                                 │                             ║ │
│  ║       last hop? ──YES───────────┼──────▶ BREAK               ║ │
│  ║                                 │                             ║ │
│  ║  ┌──────────────────────────────▼───────────────────────┐    ║ │
│  ║  │ TOOL 3: RewriteTool.execute(question, reason)         │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  LLM rewrite: ngôn ngữ thông thường → thuật ngữ     │    ║ │
│  ║  │  pháp lý/học thuật chính xác hơn                    │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  Ví dụ:                                              │    ║ │
│  ║  │   "trượt 14 tín" → "cảnh cáo học tập tín chỉ nợ"   │    ║ │
│  ║  │   "bị đuổi học" → "buộc thôi học điểm tích lũy"    │    ║ │
│  ║  │                                                      │    ║ │
│  ║  │  current_query = rewritten (nếu khác câu gốc)       │    ║ │
│  ║  │  state.add_iteration(thought, "RewriteTool", ...)   │    ║ │
│  ║  └──────────────────────────────────────────────────────┘    ║ │
│  ║         → lặp lại từ đầu với current_query mới               ║ │
│  ╚═══════════════════════════════════════════════════════════════╝ │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ TOOL 4: GenerateTool.execute(question, all_results)          │ │
│  │                                                              │ │
│  │  Xây dựng context từ tất cả docs đã thu thập:               │ │
│  │    "--- Đoạn 1 | Nguồn: Quy_che_25.pdf | 78% ---            │ │
│  │     Chương: II. Tổ chức đào tạo                             │ │
│  │     Điều: Điều 15. Đăng ký học phần...                     │ │
│  │     [nội dung]"                                             │ │
│  │                                                              │ │
│  │  Prompt = system_prompt + context + question + yêu cầu       │ │
│  │  LLM.invoke(prompt) → raw_answer                            │ │
│  │  state.add_iteration(thought, "GenerateTool", ...)          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [OUTPUT] raw_answer (str) + all_results (List[Tuple])             │
│           + state (AgentState với đầy đủ reasoning trace)          │
└────────────────────────────────────────────────────────────────────┘
```

### 4.3 Sơ đồ AgentState theo dõi reasoning

```
  AgentState (trạng thái toàn bộ phiên reasoning)
  ══════════════════════════════════════════════

  query: "Điều kiện học bổng KKHT là gì nếu GPA 3.5 ngành CNTT K68?"
  max_iterations: 5

  ┌───────────────────────────────────────────────────────────────┐
  │ Step 1 │ action: RetrieveTool                                 │
  │        │ input:  "Điều kiện học bổng KKHT..."                 │
  │        │ obs:    "Tìm được 3 đoạn tài liệu"                   │
  ├────────┼───────────────────────────────────────────────────────┤
  │ Step 2 │ action: EvaluateTool                                  │
  │        │ input:  "avg_sim=0.41"                               │
  │        │ obs:    "relevant=False | avg_sim thấp, thử LLM..."   │
  ├────────┼───────────────────────────────────────────────────────┤
  │ Step 3 │ action: RewriteTool                                   │
  │        │ input:  "Điều kiện học bổng KKHT..."                 │
  │        │ obs:    "Query mới: 'tiêu chí xét học bổng KKHT       │
  │        │          điểm tích lũy ngành kỹ thuật'"              │
  ├────────┼───────────────────────────────────────────────────────┤
  │ Step 4 │ action: RetrieveTool                                  │
  │        │ input:  "tiêu chí xét học bổng KKHT..."              │
  │        │ obs:    "Tìm được 5 đoạn tài liệu"                   │
  ├────────┼───────────────────────────────────────────────────────┤
  │ Step 5 │ action: EvaluateTool                                  │
  │        │ input:  "avg_sim=0.68"                               │
  │        │ obs:    "relevant=True | avg_sim >= 0.45 → BREAK"     │
  ├────────┼───────────────────────────────────────────────────────┤
  │ Step 6 │ action: GenerateTool                                  │
  │        │ input:  câu hỏi gốc                                  │
  │        │ obs:    "Generated 524 chars"                         │
  └────────┴───────────────────────────────────────────────────────┘

  confidence: 0.72  |  success: True  |  iterations: 6
  sources: ["Quy_che_25.pdf", "HOC_BONG_KKHT.json"]
```

### 4.4 Luồng chi tiết từng Tool

#### Tool 1 — RetrieveTool

```
  RetrieveTool.execute(query)
  ═══════════════════════════

  query ──▶ VectorDatabaseManager.search_similar(query, k, threshold)
                │
                ▼
         ChromaDB.similarity_search_with_score(query, k=3)
                │
                │ [(Document, L2_distance), ...]
                ▼
         Chuyển đổi similarity:
            sim = 1.0 / (1.0 + distance)
            ─ distance = 0.0 → sim = 1.00 (hoàn hảo)
            ─ distance = 1.0 → sim = 0.50
            ─ distance = 2.0 → sim = 0.33

         Filter: sim >= 0.35
         Sort: giảm dần theo sim
                │
                ├── len(results) < 2 AND threshold > 0.25?
                │     └── Retry với k+2, threshold=0.25 (fallback)
                │
                ▼
         ToolResult { success, data=results, message }
```

#### Tool 2 — EvaluateTool (2-layer)

```
  EvaluateTool.execute(question, results, min_avg_sim)
  ═════════════════════════════════════════════════════

  ┌─────────────────────────────────────────────────────────────┐
  │ TẦNG 1: Avg-Similarity Check (O(1), không gọi LLM)          │
  │                                                             │
  │  scores = [score for _, score in results[:top_k]]           │
  │  avg_sim = mean(scores)                                     │
  │                                                             │
  │  avg_sim >= min_avg_sim (0.45)?                             │
  │  ── YES → return { relevant: True, avg_sim, reason }        │
  │  ── NO  → chuyển sang Tầng 2                                │
  └─────────────────────────────────────────────────────────────┘
                          │ (chỉ khi avg_sim thấp)
                          ▼
  ┌─────────────────────────────────────────────────────────────┐
  │ TẦNG 2: LLM Evaluate (chậm hơn, chỉ gọi khi cần)           │
  │                                                             │
  │  context = build_context(results[:top_k])                   │
  │  prompt = "Đánh giá xem tài liệu có đề cập đến câu hỏi?"  │
  │  raw = llm_invoker(prompt)                                  │
  │                                                             │
  │  Parse JSON: { "relevant": bool, "reason": str }           │
  │  (fallback: relevant=True nếu parse lỗi)                   │
  │                                                             │
  │  return { relevant, avg_sim, reason }                       │
  └─────────────────────────────────────────────────────────────┘
```

#### Tool 3 — RewriteTool

```
  RewriteTool.execute(question, reason)
  ══════════════════════════════════════

  Prompt:
  ┌──────────────────────────────────────────────────────────┐
  │ "Câu hỏi gốc: {question}                                │
  │  Lý do tìm kiếm chưa đủ: {reason}                       │
  │  Viết lại dùng thuật ngữ pháp lý/học thuật.             │
  │  Chỉ trả về 1 câu, KHÔNG giải thích."                   │
  └──────────────────────────────────────────────────────────┘
              │
              ▼ LLM → rewritten_query
              │
  rewritten != original?
  ── YES → ToolResult { success=True, data=rewritten }
  ── NO  → ToolResult { success=False, data=original }
           (orchestrator sẽ BREAK loop)
```

#### Tool 4 — GenerateTool

```
  GenerateTool.execute(question, all_results)
  ════════════════════════════════════════════

  context = build_context(all_results):
  ┌──────────────────────────────────────────────────────────┐
  │ "--- Đoạn 1 | Nguồn: Quy_che_25.pdf | 78% ---          │
  │  Chương: II. Tổ chức đào tạo                            │
  │  Điều: Điều 15. Đăng ký học phần                       │
  │  [page_content]                                         │
  │                                                         │
  │  --- Đoạn 2 | Nguồn: HOC_BONG_KKHT.json | 71% --- "   │
  └──────────────────────────────────────────────────────────┘

  prompt = system_prompt + context + question + yêu cầu

  Yêu cầu trong prompt:
  - Phát hiện ngôn ngữ câu hỏi → trả lời đúng ngôn ngữ đó
  - Trích dẫn số Điều, Chương, tên văn bản
  - KHÔNG bịa đặt ngoài tài liệu
  - Thừa nhận giới hạn nếu không đủ thông tin

  raw_answer = llm_invoker(prompt)
  → ToolResult { success, data=raw_answer, message }
```

---

## 5. TẦNG 3 — POSTPROCESSING

### 5.1 Mô tả chức năng

Tầng Postprocessing gồm hai giai đoạn: **(a)** tính toán Confidence Score đa yếu tố; **(b)** quyết định hành động dựa trên ngưỡng và lưu kết quả vào bộ nhớ.

### 5.2 Sơ đồ luồng Postprocessing

```
┌────────────────────────────────────────────────────────────────────┐
│                   POSTPROCESSING FLOW                              │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  [INPUT] all_results + raw_answer + state.iterations               │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ BƯỚC 1: ConfidenceGate.calculate_confidence()               │ │
│  │                                                              │ │
│  │  score = 0.0                                                 │ │
│  │                                                              │ │
│  │  Yếu tố 1 — Số lượng tài liệu (tối đa +0.30):              │ │
│  │    score += min(len(results) / 5, 1.0) * 0.30               │ │
│  │    ─ 0 docs  → +0.00                                        │ │
│  │    ─ 3 docs  → +0.18                                        │ │
│  │    ─ 5+ docs → +0.30                                        │ │
│  │                                                              │ │
│  │  Yếu tố 2 — Chất lượng câu trả lời (tối đa +0.40):         │ │
│  │    has_numbers = any(c.isdigit() for c in answer)            │ │
│  │    has_legal = "điều"/"khoản"/"chương"/"gpa"/... in answer  │ │
│  │    is_negative = "không biết"/"xin lỗi"/... in answer       │ │
│  │                                                              │ │
│  │    is_negative   → +0.00                                    │ │
│  │    both          → +0.40                                    │ │
│  │    either        → +0.25                                    │ │
│  │    long (>100c)  → +0.15                                    │ │
│  │                                                              │ │
│  │  Yếu tố 3 — Hiệu quả tìm kiếm (tối đa +0.30):              │ │
│  │    iterations ≤ 2 → +0.30 (tìm thấy ngay)                  │ │
│  │    iterations ≤ 4 → +0.20                                   │ │
│  │    iterations ≤ 6 → +0.10                                   │ │
│  │                                                              │ │
│  │  confidence = round(clamp(score, 0.0, 1.0), 2)              │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                │ confidence (float 0–1)                            │
│                ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ BƯỚC 2: ConfidenceGate.evaluate()                           │ │
│  │                                                              │ │
│  │                                                              │ │
│  │   0.0 ────────────────────────────────────────────── 1.0    │ │
│  │    │         │              │                         │      │ │
│  │    │  REJECT │    WARN      │         PASS            │      │ │
│  │    │         │              │                         │      │ │
│  │    0       0.35           0.65                        1      │ │
│  │             low           high                               │ │
│  │                                                              │ │
│  │  REJECT (< 0.35):                                           │ │
│  │    answer = "Xin lỗi, không tìm thấy thông tin..."         │ │
│  │    success = False                                          │ │
│  │                                                              │ │
│  │  WARN (0.35 ≤ x < 0.65):                                    │ │
│  │    answer = raw_answer + "\n⚠️ Độ tin cậy trung bình        │ │
│  │             ({confidence:.0%}). Vui lòng kiểm tra lại..."   │ │
│  │    success = True                                           │ │
│  │                                                              │ │
│  │  PASS (≥ 0.65):                                             │ │
│  │    answer = raw_answer (không thay đổi)                     │ │
│  │    success = True                                           │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                │ GateResult { action, answer, confidence, success } │
│                ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ BƯỚC 3: state.set_answer(answer, confidence, success)       │ │
│  │                                                              │ │
│  │  AgentState cập nhật trạng thái cuối cùng                   │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                │                                                   │
│                ▼                                                   │
│  ┌──────────────────────────────────────────────────────────────┐ │
│  │ BƯỚC 4: ConversationMemory.add_turn()                       │ │
│  │                                                              │ │
│  │  memory.add_turn(                                           │ │
│  │    session_id   = session_id,                               │ │
│  │    question     = question,                                 │ │
│  │    answer       = answer[:500],  # rút gọn tránh bloat      │ │
│  │    entities     = intent_result.entities,                   │ │
│  │    intent_name  = intent_result.intent_name,               │ │
│  │    needs_clarification = False                              │ │
│  │  )                                                          │ │
│  └──────────────────────────────────────────────────────────────┘ │
│                                                                    │
│  [OUTPUT] Final result dict {                                      │
│    answer, confidence, success, state,                            │
│    retrieved_chunks, intent_name, entities,                       │
│    needs_clarification                                            │
│  }                                                                 │
└────────────────────────────────────────────────────────────────────┘
```

### 5.3 Ví dụ tính toán Confidence Score

```
  Ví dụ: Câu hỏi về học bổng KKHT

  all_results = [(doc1, 0.78), (doc2, 0.71), (doc3, 0.65)]
  raw_answer = "Theo Điều 15, Chương III, GPA phải đạt ≥ 3.2..."
  iterations = 6 (có rewrite 1 lần)

  Yếu tố 1 — Docs:
    len = 3 → min(3/5, 1.0) * 0.30 = 0.60 * 0.30 = +0.18

  Yếu tố 2 — Answer quality:
    has_numbers: True ("3.2", "15", "III")
    has_legal: True ("điều", "chương", "gpa")
    → both: +0.40

  Yếu tố 3 — Iterations:
    iterations = 6 → <= 6: +0.10

  Total = 0.18 + 0.40 + 0.10 = 0.68

  Gate → PASS (0.68 ≥ 0.65) → answer không thay đổi
```

---

## 6. HẠ TẦNG HỖ TRỢ (INFRASTRUCTURE)

### 6.1 LLM Factory

```
  _build_llm(llm_config)
  ═══════════════════════

  config.yaml:
    llm:
      provider: "gemini"   # hoặc "ollama"
      model_name: "gemini-2.5-flash"
      temperature: 0.3
      max_tokens: 2048

  ┌──────────────────────────────────────────────────────────┐
  │ provider == "gemini"                                     │
  │   → ChatGoogleGenerativeAI(model, api_key, temperature)  │
  │   → Đọc key từ env GEMINI_API_KEY hoặc config           │
  │   → _invoke_llm: asyncio event loop workaround           │
  │     (Streamlit threads không có asyncio loop)            │
  │                                                          │
  │ provider == "ollama" (default)                           │
  │   → OllamaLLM(model, base_url, temperature, timeout)    │
  │   → base_url: http://localhost:11434                     │
  └──────────────────────────────────────────────────────────┘

  _invoke_llm(llm, provider, prompt):
    response = llm.invoke(prompt)
    if hasattr(response, "content"):   # Gemini → AIMessage
        return response.content.strip()
    return str(response).strip()      # Ollama → str
```

### 6.2 Embedding Model & Vector Database

```
  ┌────────────────────────────────────────────────────────────────┐
  │              EMBEDDING & RETRIEVAL INFRASTRUCTURE              │
  │                                                                │
  │  ┌──────────────────────────────────────────┐                 │
  │  │ EmbeddingModelManager                   │                 │
  │  │   model: BAAI/bge-m3 (HuggingFace)      │                 │
  │  │   batch_size: 32                        │                 │
  │  │   → HuggingFaceEmbeddings(model_name)   │                 │
  │  └──────────────────────┬───────────────────┘                 │
  │                         │ embeddings object                   │
  │                         ▼                                     │
  │  ┌──────────────────────────────────────────┐                 │
  │  │ VectorDatabaseManager (ChromaDB)         │                 │
  │  │   persist_dir: ./data/chroma             │                 │
  │  │   collection: student_regulations        │                 │
  │  │                                          │                 │
  │  │   PersistentClient → Chroma vectorstore  │                 │
  │  │                                          │                 │
  │  │   search_similar(query, k, threshold):   │                 │
  │  │     1. similarity_search_with_score()    │                 │
  │  │     2. L2 distance → similarity score    │                 │
  │  │     3. Filter by threshold               │                 │
  │  │     4. Sort descending                   │                 │
  │  └──────────────────────────────────────────┘                 │
  └────────────────────────────────────────────────────────────────┘

  Embedding Model: BAAI/bge-m3
    ─ Đa ngôn ngữ (Tiếng Việt + Tiếng Anh)
    ─ Dimension: 1024
    ─ Phù hợp văn bản pháp lý

  Distance Formula (ChromaDB):
    L2 (Euclidean) → chuyển về similarity:
    sim = 1 / (1 + L2_distance) ∈ (0, 1]
```

### 6.3 SchemaLoader — Auto-Discovery

```
  SchemaLoader (Priority Chain)
  ══════════════════════════════

  Yêu cầu: Hệ thống có thể tái sử dụng cho bất kỳ trường nào
           mà không cần sửa code, chỉ cần cấp YAML schema.

  ┌─────────────────────────────────────────────────────────────┐
  │  SchemaLoader.load() — Ưu tiên 1:                           │
  │                                                             │
  │  university_schema.yaml (sinh bởi discover_schema.py)       │
  │  ─────────────────────────────────────────────────────      │
  │  university:                                                │
  │    name: "Đại học Bách khoa Hà Nội"                        │
  │    source_documents: [Quy_che_25.json, HOC_BONG_KKHT.json] │
  │                                                             │
  │  domain_entities:                                           │
  │    nganh_hoc:                                               │
  │      description: "Ngành học của sinh viên"                │
  │      examples: [CNTT, "Cơ điện tử"]                        │
  │      clarification_prompt: "Ngành học của bạn là gì?"      │
  │    khoa_hoc: ...                                            │
  │    gpa: ...                                                 │
  │                                                             │
  │  intents:                                                   │
  │    HOC_BONG_KKHT:                                          │
  │      description: "Câu hỏi về học bổng KKHT"               │
  │      requires_entities: true                               │
  │      required_fields: [nganh_hoc, khoa_hoc, gpa]           │
  │      clarification_template: "..."                         │
  │    GENERAL_REGULATION: ...                                  │
  └─────────────────────────────────────────────────────────────┘
           │ Nếu file không tồn tại
           ▼
  ┌─────────────────────────────────────────────────────────────┐
  │  Ưu tiên 2 (Fallback): config.yaml['intents']               │
  │  ─ Hoạt động ngay khi chưa chạy discover_schema.py          │
  │  ─ Không có domain_entities phong phú                      │
  └─────────────────────────────────────────────────────────────┘

  Lợi ích:
  ─ Hot-swap schema: thay university_schema.yaml = đổi trường
  ─ Backward compatible: hệ thống cũ vẫn chạy qua fallback
```

---

## 7. CẤU TRÚC DỮ LIỆU CHÍNH

### 7.1 IntentResult

```python
@dataclass
class IntentResult:
    intent_name: str             # "HOC_BONG_KKHT" | "GENERAL_REGULATION" | ...
    entities: Dict[str, Any]     # {"nganh_hoc": "CNTT", "khoa_hoc": "K68", "gpa": "3.5"}
    needs_clarification: bool    # True → trả về câu hỏi làm rõ
    clarification_question: str  # "Bạn vui lòng cho biết khóa học của bạn?"
    missing_fields: List[str]    # ["khoa_hoc"]
    confidence: float            # 0.0–1.0 (từ LLM phân loại)
    raw_llm_response: str        # JSON thô từ LLM (debug)
```

### 7.2 AgentState

```python
@dataclass
class AgentState:
    query: str                   # Câu hỏi gốc
    iterations: int              # Số bước đã thực hiện
    max_iterations: int          # Giới hạn (5)
    thoughts: List[str]
    actions: List[str]
    observations: List[str]
    confidence: float            # Confidence cuối cùng
    answer: Optional[str]        # Câu trả lời cuối
    steps: List[Step]            # Danh sách Step objects (for UI display)
    success: bool
    error: Optional[str]
    sources: List[str]           # Nguồn tài liệu đã dùng
    timestamp: str

@dataclass
class Step:
    iteration: int
    thought: str
    action: str                  # "retrieve_documents" | "evaluate_relevance" | ...
    action_input: str
    observation: str
```

### 7.3 ToolResult

```python
@dataclass
class ToolResult:
    success: bool
    data: Any                    # Linh hoạt: List[Tuple], str, Dict tùy tool
    message: str                 # Thông báo ngắn gọn
    metadata: Dict[str, Any]     # Dữ liệu phụ (mở rộng)
```

### 7.4 GateResult

```python
@dataclass
class GateResult:
    action: str                  # "reject" | "warn" | "pass"
    answer: str                  # Câu trả lời đã được xử lý
    confidence: float
    success: bool
```

### 7.5 ConversationTurn

```python
@dataclass
class ConversationTurn:
    question: str
    answer: str
    entities: Dict[str, Any]     # Entity đã bóc tách — carry-over qua các turn
    intent_name: str
    needs_clarification: bool
```

---

## 8. SƠ ĐỒ LUỒNG CON CHI TIẾT

### 8.1 Luồng Clarification (Hỏi làm rõ → Trả lời)

```
  MULTI-TURN CLARIFICATION FLOW
  ═══════════════════════════════

  Turn 1: User hỏi thiếu thông tin
  ─────────────────────────────────
  User: "Tôi có được học bổng KKHT không?"

  Preprocessing:
    Intent: HOC_BONG_KKHT
    LLM entities: { nganh_hoc: null, khoa_hoc: null, gpa: null }
    memory_entities: {}
    merged: {}
    required: [nganh_hoc, khoa_hoc, gpa]
    missing: [nganh_hoc, khoa_hoc, gpa]
    needs_clarification: True

  Memory.add_turn(..., needs_clarification=True, intent="HOC_BONG_KKHT")

  Response: "Để trả lời chính xác, bạn vui lòng cho biết:
             - Ngành học của bạn là gì? (ví dụ: CNTT...)
             - Bạn thuộc khóa nào? (ví dụ: K65, K68...)
             - GPA tích lũy của bạn là bao nhiêu?"

  ─────────────────────────────────────────────────────────────────
  Turn 2: User bổ sung thông tin
  ─────────────────────────────────
  User: "Tôi học CNTT K68, GPA 3.5"

  Preprocessing:
    memory_context: [Turn 1 Q&A]
    memory_entities: {} (turn 1 không có entity)
    previous_intent: "HOC_BONG_KKHT" (last turn needs_clarification=True)

    LLM call với hint "⚠️ LƯU Ý: Trước đó bot hỏi về HOC_BONG_KKHT"
    LLM entities: { nganh_hoc: "CNTT", khoa_hoc: "K68", gpa: "3.5" }

    Heuristic: len("Tôi học CNTT K68, GPA 3.5".split()) = 6 ≤ 15
               → is_clarification_response = True
               → intent = "HOC_BONG_KKHT" (giữ nguyên)

    merged: { nganh_hoc: "CNTT", khoa_hoc: "K68", gpa: "3.5" }
    missing: [] → needs_clarification = False

  → Chuyển sang Agent Reasoning với đầy đủ thông tin
```

### 8.2 Luồng Multi-Hop Retrieval

```
  MULTI-HOP RETRIEVAL FLOW (MAX_HOPS = 2)
  ════════════════════════════════════════

  HOP 1:
  ┌─────────────────────────────────────────────────────────────┐
  │  query = "Tôi bị đuổi học không nếu nợ 14 tín?"           │
  │                                                             │
  │  RetrieveTool:                                              │
  │    search("Tôi bị đuổi học không nếu nợ 14 tín?")          │
  │    → 2 docs, avg_sim = 0.38                                │
  │                                                             │
  │  EvaluateTool:                                              │
  │    avg_sim 0.38 < 0.45 → Tầng 2: LLM evaluate             │
  │    LLM: relevant=False, reason="Không đề cập buộc thôi học"│
  │                                                             │
  │  RewriteTool:                                               │
  │    "bị đuổi học" → "buộc thôi học do điểm tích lũy thấp"  │
  └─────────────────────────────────────────────────────────────┘
                              │ current_query = rewritten
                              ▼

  HOP 2:
  ┌─────────────────────────────────────────────────────────────┐
  │  query = "buộc thôi học do điểm tích lũy thấp"             │
  │                                                             │
  │  RetrieveTool:                                              │
  │    search("buộc thôi học do điểm tích lũy thấp")            │
  │    → 4 docs, avg_sim = 0.72                                │
  │                                                             │
  │  EvaluateTool:                                              │
  │    avg_sim 0.72 >= 0.45 → relevant=True → BREAK            │
  └─────────────────────────────────────────────────────────────┘
                              │
                              ▼

  GenerateTool: tổng hợp từ all_results (6 docs, dedup)

  Dedup logic: merge(hop1_results, hop2_results)
    ─ Loại bỏ doc trùng theo page_content
    ─ Giữ union của tất cả tài liệu liên quan
```

### 8.3 Luồng khởi tạo Agent (_initialize)

```
  StudentRegulationAgent.__init__(config_path)
  ══════════════════════════════════════════════

  Thứ tự khởi tạo (dependency order):

  1. _load_config(config_path)
     └─ Đọc config.yaml → self.config

  2. _build_llm(llm_config)
     └─ Khởi tạo LLM (Gemini/Ollama) → self.llm, self._provider

  3. _initialize_vector_db()
     └─ EmbeddingModelManager → HuggingFaceEmbeddings
     └─ VectorDatabaseManager → ChromaDB → self.vector_db_manager

  4. _initialize_schema_loader()
     └─ SchemaLoader(config) → self._schema_loader
     └─ load_university_info() → tên trường, tài liệu
     └─ build_system_prompt(university_name, doc_list)
     └─ self._system_prompt = personalized prompt

  5. _register_tools()
     └─ Tạo llm_invoker closure
     └─ self._tools = {
           "retrieve": RetrieveTool(vector_db, config),
           "evaluate": EvaluateTool(),
           "rewrite":  RewriteTool(llm_invoker),
           "generate": GenerateTool(llm_invoker, system_prompt),
        }

  6. _initialize_intent_classifier()
     └─ schema_loader.load() → intent_config
     └─ schema_loader.load_domain_entities() → domain_entities
     └─ IntentClassifier(intent_config, llm_invoker, domain_entities)

  7. _initialize_memory()
     └─ get_memory(window_size=5, max_context_chars=1500)

  8. _initialize_confidence_gate()
     └─ ConfidenceGate(high=0.65, low=0.35)

  ✅ Agent sẵn sàng: "Agent ready. Tools: [retrieve, evaluate, rewrite, generate]"
```

---

## 9. BẢNG TỔNG HỢP CẤU HÌNH

### 9.1 Các tham số quan trọng (config.yaml)

| Tham số | Mặc định | Ý nghĩa | Ảnh hưởng |
|---------|----------|---------|-----------|
| `llm.provider` | `ollama` | Provider LLM | Chọn Gemini/Ollama |
| `llm.temperature` | `0.3` | Độ ngẫu nhiên LLM | Thấp → deterministic |
| `llm.max_tokens` | `2048` | Token tối đa output | Giới hạn độ dài câu trả lời |
| `retrieval.top_k` | `3` | Số tài liệu trả về | Ảnh hưởng recall |
| `retrieval.similarity_threshold` | `0.35` | Ngưỡng filter | Tăng → chính xác hơn, ít hơn |
| `agent.max_iterations` | `5` | Số bước tối đa trong AgentState | Giới hạn độ sâu reasoning |
| `agent.min_avg_similarity` | `0.45` | Ngưỡng EvaluateTool tầng 1 | Quyết định có rewrite không |
| `agent.high_confidence_threshold` | `0.65` | Ngưỡng ConfidenceGate PASS | Dưới → thêm cảnh báo |
| `agent.low_confidence_threshold` | `0.35` | Ngưỡng ConfidenceGate REJECT | Dưới → từ chối trả lời |
| `memory.window_size` | `5` | Số turn nhớ | Ảnh hưởng carry-over entity |
| `memory.max_context_chars` | `1500` | Ký tự context tối đa | Tránh token bloat |
| `schema.auto_discovery` | `true` | Dùng university_schema.yaml | False → chỉ dùng config.yaml |

### 9.2 Hằng số trong code

| Hằng số | Giá trị | File | Ý nghĩa |
|---------|---------|------|---------|
| `MAX_RETRIEVAL_HOPS` | `2` | orchestrator.py:128 | Số lần Retrieve → Evaluate → Rewrite |
| `DEFAULT_HIGH` | `0.65` | confidence_gate.py:30 | Ngưỡng PASS của ConfidenceGate |
| `DEFAULT_LOW` | `0.35` | confidence_gate.py:31 | Ngưỡng REJECT của ConfidenceGate |
| `fallback_threshold` | `0.25` | retrieve_tool.py:36 | Ngưỡng tự động hạ khi < 2 kết quả |
| `max_doc_display` | `15` | prompts.py:193 | Số tài liệu tối đa trong system prompt |
| `context_max_chars` | `2000` | evaluate_tool.py:103 | Giới hạn context gửi vào LLM evaluate |

### 9.3 Bảng luồng quyết định tổng thể

```
  DECISION TREE — answer_question()
  ═══════════════════════════════════

  START
    │
    ├── intent_classifier == None?
    │     └── YES → skip Preprocessing, go to Reasoning
    │
    ├── needs_clarification == True?
    │     └── YES → return { answer: clarification_q, success: False }
    │
    ├── for hop in [0, 1]:
    │     ├── retrieve → 0 results? → BREAK
    │     ├── evaluate → relevant == True? → BREAK
    │     └── rewrite → new == old? → BREAK
    │
    ├── all_results == []?
    │     └── YES → return { answer: "Không tìm thấy...", confidence: 0.1 }
    │
    ├── generate → raw_answer
    │
    ├── confidence = calculate_confidence(results, answer, iterations)
    │
    ├── gate.evaluate(confidence):
    │     ├── REJECT → return { answer: no_result_msg, success: False }
    │     ├── WARN   → return { answer: raw + warning, success: True }
    │     └── PASS   → return { answer: raw, success: True }
    │
    └── save_memory(session_id, q, a, entities)

  END
```

---

## PHỤ LỤC — Sơ đồ phụ thuộc module

```
  src/
  ├── agent/
  │   ├── orchestrator.py ←── [CORE] StudentRegulationAgent
  │   │     depends on: pipeline.*, agent.tools.*, memory.*, agent.state
  │   ├── state.py         ─── AgentState, Step
  │   ├── prompts.py       ─── REACT_SYSTEM_PROMPT, build_system_prompt()
  │   └── tools/
  │       ├── base.py      ─── BaseTool (ABC), ToolResult
  │       ├── retrieve_tool.py  depends on: embeddings.vector_db
  │       ├── evaluate_tool.py  depends on: LLM invoker (closure)
  │       ├── rewrite_tool.py   depends on: LLM invoker
  │       └── generate_tool.py  depends on: LLM invoker
  │
  ├── pipeline/
  │   ├── intent_classifier.py ─── IntentClassifier, IntentResult
  │   ├── confidence_gate.py   ─── ConfidenceGate, GateResult
  │   └── schema_loader.py     ─── SchemaLoader
  │
  ├── memory/
  │   └── memory_manager.py    ─── ConversationMemory, ConversationTurn, get_memory()
  │
  └── embeddings/
      ├── model.py             ─── EmbeddingModelManager (BAAI/bge-m3)
      └── vector_db.py         ─── VectorDatabaseManager (ChromaDB)

  Phụ thuộc ngoài (external):
    langchain_google_genai    → ChatGoogleGenerativeAI (Gemini)
    langchain_ollama          → OllamaLLM (Ollama)
    langchain_chroma          → Chroma vectorstore
    langchain_huggingface     → HuggingFaceEmbeddings
    chromadb                  → PersistentClient
```

---

*Tài liệu này được tổng hợp dựa trên phân tích mã nguồn thực tế tại `src/` — AgenticRAG v6 (Tool-Based Orchestrator).*
