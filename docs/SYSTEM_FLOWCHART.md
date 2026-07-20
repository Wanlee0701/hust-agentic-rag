# 📊 HUST AgenticRAG Chatbot — Sơ Đồ Luồng Hoạt Động (v6)

> Kiến trúc **Tool-Based Modular** với 3 tầng rõ ràng:
> **Preprocessing (Pipeline)** → **Agent Reasoning (Tools)** → **Postprocessing (Pipeline)**

---

## 1️⃣ **SƠ ĐỒ TỔNG THỂ (HIGH-LEVEL ARCHITECTURE)**

```mermaid
graph TB
    User["👤 User"] -->|Nhập câu hỏi| Frontend["🎨 Streamlit Frontend\napp.py"]
    Frontend -->|answer_question| Agent["🤖 StudentRegulationAgent\norchestrator.py"]

    Agent -->|Preprocessing| Pipeline["🔀 Pipeline Layer\nsrc/pipeline/"]
    Agent -->|Retrieve| VectorDB["📚 ChromaDB\nVector Database"]
    Agent -->|LLM calls| LLM["🧠 LLM Server\nOllama / Gemini"]
    Agent -->|Postprocessing| Gate["🚦 Confidence Gate\nsrc/pipeline/confidence_gate.py"]
    Agent -->|Read/Write| Memory["💾 Conversation Memory\nsrc/memory/"]

    VectorDB -->|Documents + Scores| Agent
    LLM -->|Text Response| Agent
    Pipeline -->|Intent + Entities| Agent
    Gate -->|Filtered Answer| Agent

    Agent -->|answer, confidence, sources| Frontend
    Frontend -->|Display| User

    KB["📁 Knowledge Base\n9+ PDFs"] -->|build_knowledge_base.py| Embed["🔄 Embedding Pipeline\nBAAI/bge-m3"]
    Embed -->|Store| VectorDB

    style User fill:#e1f5ff
    style Frontend fill:#fff3e0
    style Agent fill:#f3e5f5
    style Pipeline fill:#e0f7fa
    style VectorDB fill:#e8f5e9
    style LLM fill:#fce4ec
    style Gate fill:#fff9c4
    style Memory fill:#ede7f6
    style KB fill:#f1f8e9
    style Embed fill:#f9fbe7
```

---

## 2️⃣ **LUỒNG XỬ LÝ CHÍNH (MAIN FLOW)**

```mermaid
sequenceDiagram
    participant User as 👤 User
    participant UI as 🎨 Streamlit
    participant Orch as 🤖 Orchestrator
    participant IC as 🔎 IntentClassifier
    participant Mem as 💾 Memory
    participant RT as 🔧 RetrieveTool
    participant ET as 🔧 EvaluateTool
    participant RW as 🔧 RewriteTool
    participant GT as 🔧 GenerateTool
    participant CG as 🚦 ConfidenceGate

    User->>UI: 📝 Nhập câu hỏi
    UI->>Orch: answer_question(question, session_id)

    Orch->>Mem: get_context(session_id)
    Mem-->>Orch: memory_context, memory_entities

    Orch->>IC: classify(question, context, entities)
    IC-->>Orch: IntentResult {intent, entities, needs_clarification}

    alt needs_clarification = True
        Orch->>Mem: save clarification turn
        Orch-->>UI: ❓ clarification_question
        UI-->>User: "Bạn đang hỏi về ngành nào?"
    else Pass to RAG
        loop Multi-hop (tối đa 2 hops)
            Orch->>RT: execute(query)
            RT-->>Orch: List[(Document, score)]

            Orch->>ET: execute(question, results, min_avg_sim)
            ET-->>Orch: {relevant, avg_sim, reason}

            alt relevant = False AND hop < MAX
                Orch->>RW: execute(question, reason)
                RW-->>Orch: rewritten_query
                Note over Orch: Dùng query mới để retrieve lại
            end
        end

        Orch->>GT: execute(question, results)
        GT-->>Orch: raw_answer

        Orch->>CG: evaluate(confidence, raw_answer, question)
        CG-->>Orch: GateResult {action, answer}

        Orch->>Mem: add_turn(session_id, question, answer)
        Orch-->>UI: {answer, confidence, sources, intent}
        UI-->>User: 💬 Hiển thị kết quả
    end
```

---

## 3️⃣ **LUỒNG AGENT REASONING CHI TIẾT**

```mermaid
graph TD
    START(["🔴 START\nNhận question + session_id"]) --> Step0

    Step0["⚙️ BƯỚC 0: PREPROCESSING\nsrc/pipeline/"] --> IC

    IC["🔎 IntentClassifier.classify()\n• Đọc memory context\n• LLM phân loại intent + entity\n• Kiểm tra required_fields"] --> Gate0{needs_clarification?}

    Gate0 -->|YES| Clarify["❓ Sinh câu hỏi làm rõ\nVí dụ: 'Bạn hỏi về ngành nào?'"]
    Clarify --> SaveMem0["💾 Memory.add_turn()"]
    SaveMem0 --> RETURN_CLARIFY(["📤 Trả về clarification\nkèm needs_clarification=True"])

    Gate0 -->|NO - Pass to RAG| HopLoop

    HopLoop["🔁 MULTI-HOP LOOP\nhop = 0 → MAX_HOPS-1"] --> Tool1

    Tool1["🔧 Tool 1: RetrieveTool.execute(query)\n• ChromaDB search top_k\n• Nếu < 2 docs → fallback threshold thấp hơn\n• Return List[(Document, score)]"] --> Tool2

    Tool2["🔧 Tool 2: EvaluateTool.execute()\nTầng 1: avg_sim >= min_avg_sim?\n  → YES: relevant = True\n  → NO: gọi LLM evaluate"] --> EvalGate{relevant?}

    EvalGate -->|YES| Tool4
    EvalGate -->|NO AND hop < MAX| Tool3

    Tool3["🔧 Tool 3: RewriteTool.execute()\n• LLM viết lại query\n• Dùng thuật ngữ pháp lý chính xác hơn\n• Return rewritten_query"] --> NextHop["hop++ → retrieve với query mới"]
    NextHop --> Tool1

    EvalGate -->|NO AND hop = MAX| Tool4

    Tool4["🔧 Tool 4: GenerateTool.execute()\n• Build context từ all results\n• Gọi LLM tổng hợp câu trả lời\n• Return raw_answer"] --> CalcConf

    CalcConf["📊 Tính Confidence Score\n• Factor 1: Số docs (max 0.30)\n• Factor 2: Chất lượng answer (max 0.40)\n• Factor 3: Số hops (max 0.30)"] --> GateCG

    GateCG["🚦 ConfidenceGate.evaluate()\nsrc/pipeline/confidence_gate.py"] --> GateAction{confidence?}

    GateAction -->|"< low (0.35)"| Reject["❌ ACTION: reject\nTrả về thông báo không tìm thấy\n+ gợi ý hỏi lại"]
    GateAction -->|"low ≤ x < high (0.65)"| Warn["⚠️ ACTION: warn\nGiữ nguyên answer\n+ thêm cảnh báo độ tin cậy"]
    GateAction -->|">= high (0.65)"| Pass["✅ ACTION: pass\nGiữ nguyên answer"]

    Reject --> SaveMem
    Warn --> SaveMem
    Pass --> SaveMem

    SaveMem["💾 Memory.add_turn()\nLưu Q&A + entities vào session"] --> RETURN(["📤 Return\n{answer, confidence, success,\nstate, retrieved_chunks,\nintent_name, entities}"])

    style START fill:#ffcdd2
    style RETURN fill:#c8e6c9
    style RETURN_CLARIFY fill:#fff9c4
    style Tool1 fill:#e3f2fd
    style Tool2 fill:#e8f5e9
    style Tool3 fill:#fff3e0
    style Tool4 fill:#f3e5f5
    style GateCG fill:#fff9c4
    style Reject fill:#ffcdd2
    style Warn fill:#fff9c4
    style Pass fill:#c8e6c9
```

---

## 4️⃣ **CẤU TRÚC MODULE (SRC/)**

```mermaid
graph TD
    SRC["📦 src/"] --> Agent & Pipeline & Memory & Embeddings & Utils

    Agent["🤖 src/agent/\nAgent Reasoning"] --> A1["orchestrator.py\nStudentRegulationAgent"]
    Agent --> A2["state.py\nAgentState + Step"]
    Agent --> A3["prompts.py\nREACT_SYSTEM_PROMPT"]
    Agent --> ToolsDir["tools/\nBaseTool interface"]

    ToolsDir --> T1["base.py\nBaseTool ABC\nToolResult dataclass"]
    ToolsDir --> T2["retrieve_tool.py\nRetrieveTool"]
    ToolsDir --> T3["evaluate_tool.py\nEvaluateTool"]
    ToolsDir --> T4["rewrite_tool.py\nRewriteTool"]
    ToolsDir --> T5["generate_tool.py\nGenerateTool"]

    Pipeline["🔀 src/pipeline/\nPre+Postprocessing"] --> P1["intent_classifier.py\nIntentClassifier\n(hybrid LLM+Schema)"]
    Pipeline --> P2["schema_loader.py\nSchemaLoader\n(load từ YAML)"]
    Pipeline --> P3["confidence_gate.py\nConfidenceGate\n(3-level: reject/warn/pass)"]

    Memory["💾 src/memory/\nConversation Memory"] --> M1["memory_manager.py\nConversationMemory\n(Sliding Window K=5)"]

    Embeddings["🔢 src/embeddings/\nVector DB Layer"] --> E1["model.py\nEmbeddingModelManager"]
    Embeddings --> E2["vector_db.py\nVectorDatabaseManager"]
    Embeddings --> E3["processor.py\nPDFProcessor"]

    Utils["🛠️ src/utils/\nUtilities"] --> U1["config.py"]
    Utils --> U2["logger.py"]
    Utils --> U3["performance.py"]

    style Agent fill:#f3e5f5
    style ToolsDir fill:#e3f2fd
    style Pipeline fill:#e0f7fa
    style Memory fill:#ede7f6
    style Embeddings fill:#e8f5e9
    style Utils fill:#fff3e0
```

---

## 5️⃣ **CHI TIẾT INTENT GATE (PREPROCESSING)**

```mermaid
graph TD
    Q["❓ Câu hỏi user"] --> ReadMem["📖 Đọc memory context\n+ memory_entities từ K turns trước"]

    ReadMem --> LLMClassify["🧠 LLM phân loại\nJSON: {intent, entities}"]
    LLMClassify --> Schema["📋 Schema kiểm tra\nrequires_fields của intent"]

    Schema --> CheckField{Còn thiếu entity?}
    CheckField -->|"entity có trong memory"| FillMem["🔄 Bổ sung từ memory\nkhông hỏi lại user"]
    FillMem --> CheckField2{Vẫn còn thiếu?}

    CheckField -->|"entity KHÔNG có"| AskClarify["❓ Sinh clarification_question\ntừ schema.clarification_template"]
    CheckField2 -->|YES| AskClarify
    CheckField2 -->|NO| PassRAG

    AskClarify --> Return1(["📤 IntentResult\nneeds_clarification=True\nclarification_question=..."])
    PassRAG["✅ Đủ thông tin"] --> Return2(["📤 IntentResult\nneeds_clarification=False\nentities={...}"])

    style Return1 fill:#fff9c4
    style Return2 fill:#c8e6c9
```

---

## 6️⃣ **DATA PIPELINE (PDF → CHROMADB)**

```mermaid
graph LR
    A["📁 knowledge_base/raw/\nPDF files"] -->|PDFProcessor| B["📝 Extracted Text\n+ Metadata\n{source, chapter, article}"]

    B -->|Regex cleaning\nconfig.yaml rules| C["🧹 Cleaned Text\nXóa header pháp lý\nXóa số trang..."]

    C -->|TextSplitter\nchunk_size=1000\noverlap=200| D["📑 Text Chunks\nMeta: chapter_title\narticle_title, source_file"]

    D -->|EmbeddingModel\nBAAI/bge-m3| E["🔢 Embeddings\n768-dim vectors"]

    E -->|ChromaDB| F["💾 Vector Store\n./data/chroma/\nPersistent"]

    F -->|search_similar\nquery, k, threshold| G["🔍 Top-k Results\nList[(Document, score)]"]

    G -->|RetrieveTool| H["🤖 Agent"]

    style A fill:#fff3e0
    style C fill:#e0f2f1
    style F fill:#e8f5e9
    style H fill:#f3e5f5
```

---

## 7️⃣ **CONFIDENCE GATE — 3 MỨC XỬ LÝ**

```mermaid
graph TD
    IN["📥 raw_answer + confidence score\ntính từ 3 factors"] --> Calc

    Calc["📊 calculate_confidence()\n• docs count  → max 0.30\n• answer quality → max 0.40\n  (has_numbers AND has_legal → +0.40)\n• iterations efficiency → max 0.30"] --> Gate

    Gate{Confidence?}

    Gate -->|"< 0.35 (LOW)"| R1["❌ REJECT\nKhông đủ thông tin\nTrả về default message:\n• Gợi ý từ khóa khác\n• Link hust.edu.vn\n• Liên hệ Phòng Đào tạo"]

    Gate -->|"0.35 ≤ x < 0.65 (MID)"| R2["⚠️ WARN\nGiữ nguyên raw_answer\nAppend cảnh báo:\n'Độ tin cậy ở mức trung bình ({x}%)...'"]

    Gate -->|">= 0.65 (HIGH)"| R3["✅ PASS\nGiữ nguyên raw_answer\nKhông thêm gì"]

    R1 --> Out(["📤 GateResult\naction, answer, confidence, success"])
    R2 --> Out
    R3 --> Out

    style R1 fill:#ffcdd2
    style R2 fill:#fff9c4
    style R3 fill:#c8e6c9
```

---

## 8️⃣ **CONVERSATION MEMORY — SLIDING WINDOW**

```mermaid
graph LR
    Turn["💬 Mỗi Q&A turn\n{question, answer, entities, intent}"]

    Turn --> Win["📋 Sliding Window\nGiữ K=5 turns gần nhất\nStorage: Python in-memory dict"]

    Win --> Usage["Các cách sử dụng:"]

    Usage --> U1["get_context(session_id)\n→ Tóm tắt text để inject vào LLM"]
    Usage --> U2["get_entities_from_memory()\n→ Dict gộp entity từ toàn bộ window\n→ Tránh hỏi lại user"]
    Usage --> U3["get_last_clarification_intent()\n→ Biết intent của lần clarify trước\n→ Xử lý khi user trả lời làm rõ"]
    Usage --> U4["reset(session_id)\n→ Xóa khi user bắt đầu chat mới"]

    style Win fill:#ede7f6
```

---

## 9️⃣ **SƠ ĐỒ XỬ LÝ LỖI & FALLBACK**

```mermaid
graph TD
    Q["🔍 Query Processing"] --> R{Tìm được docs?}

    R -->|"0 docs"| F1["⚠️ Fallback Retrieve\nGiảm threshold → 0.25\nTăng top_k += 2"]
    F1 --> R2{Vẫn không có?}
    R2 -->|NO| Empty["❌ Không có tài liệu\nConfidence ≈ 0.0\nGate: REJECT"]
    R2 -->|YES| Eval

    R -->|"Có docs"| Eval["🔧 EvaluateTool"]

    Eval --> ER{relevant?}
    ER -->|YES| Gen["🔧 GenerateTool"]
    ER -->|"NO + hops < MAX"| Rew["🔧 RewriteTool → retry"]
    Rew --> Q
    ER -->|"NO + hops = MAX"| Gen

    Gen --> GE{LLM error?}
    GE -->|ERROR| Err["❌ ToolResult.success=False\nReturn lỗi hệ thống"]
    GE -->|OK| CG["🚦 ConfidenceGate"]

    CG --> Final["📤 Trả về kết quả\n(reject / warn / pass)"]
    Empty --> Final
    Err --> Final

    style Empty fill:#ffcdd2
    style Err fill:#ffcdd2
    style Final fill:#c8e6c9
```

---

## 🔟 **BẢNG TÓM TẮT MODULES**

| Tầng | Module | File | Vai trò | Class/Function chính |
|------|--------|------|---------|----------------------|
| **Preprocessing** | `src/pipeline/` | `intent_classifier.py` | Phân loại intent + bóc tách entity | `IntentClassifier.classify()` |
| **Preprocessing** | `src/pipeline/` | `schema_loader.py` | Load schema từ YAML | `SchemaLoader.load()` |
| **Postprocessing** | `src/pipeline/` | `confidence_gate.py` | Lọc câu trả lời theo độ tin cậy | `ConfidenceGate.evaluate()` |
| **Agent** | `src/agent/` | `orchestrator.py` | Điều phối toàn bộ luồng | `StudentRegulationAgent.answer_question()` |
| **Agent** | `src/agent/` | `state.py` | Lưu trạng thái reasoning | `AgentState`, `Step` |
| **Agent** | `src/agent/` | `prompts.py` | Prompt templates | `REACT_SYSTEM_PROMPT`, `build_system_prompt()` |
| **Tools** | `src/agent/tools/` | `base.py` | Interface chuẩn | `BaseTool`, `ToolResult` |
| **Tools** | `src/agent/tools/` | `retrieve_tool.py` | ChromaDB search + fallback | `RetrieveTool.execute()` |
| **Tools** | `src/agent/tools/` | `evaluate_tool.py` | avg-sim + LLM evaluate | `EvaluateTool.execute()` |
| **Tools** | `src/agent/tools/` | `rewrite_tool.py` | LLM query rewrite | `RewriteTool.execute()` |
| **Tools** | `src/agent/tools/` | `generate_tool.py` | LLM answer synthesis | `GenerateTool.execute()` |
| **Memory** | `src/memory/` | `memory_manager.py` | Sliding window memory | `ConversationMemory`, `get_memory()` |
| **Embeddings** | `src/embeddings/` | `model.py` | Load & cache embedding model | `EmbeddingModelManager` |
| **Embeddings** | `src/embeddings/` | `vector_db.py` | ChromaDB operations | `VectorDatabaseManager.search_similar()` |
| **Embeddings** | `src/embeddings/` | `processor.py` | Extract & clean PDF | `PDFProcessor.process_pdf_file()` |
| **Frontend** | `.` | `app.py` | Streamlit UI | `load_agent()`, chat interface |
| **Config** | `.` | `config.yaml` | Tất cả tham số hệ thống | LLM, retrieval, agent, memory, intents |

---

## 1️⃣1️⃣ **VÒNG ĐỜI HỆ THỐNG (LIFECYCLE)**

```mermaid
timeline
    title Vòng đời từ Startup đến Query

    section 🚀 Startup
        Load config.yaml : Đọc cấu hình LLM, retrieval, agent, memory
        Init LLM : Kết nối Ollama / Gemini API
        Load Embedding Model : BAAI/bge-m3 từ ./models/
        Load ChromaDB : Mở ./data/chroma/ (persistent)
        Init SchemaLoader : Load intent schema từ config.yaml
        Init IntentClassifier : Gắn schema + LLM invoker
        Register Tools : RetrieveTool, EvaluateTool, RewriteTool, GenerateTool
        Init ConfidenceGate : high=0.65, low=0.35
        Init Memory : Sliding window K=5

    section 👤 User Query
        User Input : Người dùng nhập câu hỏi
        Load Memory Context : K turns gần nhất của session
        Intent Gate : LLM classify + Schema validate
        Clarification? : Hỏi lại nếu thiếu entity

    section 🤖 Agent Reasoning
        Hop 1 : RetrieveTool → EvaluateTool
        Hop 2 nếu cần : RewriteTool → RetrieveTool → EvaluateTool
        GenerateTool : LLM tổng hợp từ context
        ConfidenceGate : reject / warn / pass

    section 💬 Response
        Save Memory : Lưu turn vào session
        Return Response : answer, confidence, sources, intent
        Display : Streamlit UI hiển thị kết quả
```

---

*Sơ đồ cập nhật theo kiến trúc v6 — Tool-Based Modular Agent* 🎯
