# Agentic RAG - Kiến Trúc Tổng Thể (Mermaid Diagram)

## 1. Toàn Bộ Luồng Hệ Thống (Tối Ưu cho PDF - Ngang)

```mermaid
graph LR
    QUERY["📝 Query Input<br/>Student Question"]
    
    AGENT["<b>🤖 AGENT REASONING LOOP</b><br/>Think → Decide → Act"]
    
    subgraph TOOLS["🔧 TOOLS"]
        RET["🔍 Retrieve<br/>Search"]
        REF["✏️ Refine<br/>Rephrase"]
        VER["✓ Verify<br/>Check"]
    end
    
    subgraph EMBEDDING["🧬 EMBEDDING & RETRIEVAL"]
        EMB["Embedding Model<br/>BAAI/bge-m3"]
        VDB["Chroma DB<br/>Vector Store"]
    end
    
    LLM["🧠 LLM<br/>Mistral 7B<br/>Ollama"]
    
    CONFIG["⚙️ Config.yaml<br/>Settings"]
    
    ANSWER["✅ Final Answer<br/>+ Sources<br/>+ Confidence"]
    
    QUERY --> AGENT
    
    AGENT -->|Decide:| RET
    AGENT -->|Decide:| REF
    AGENT -->|Decide:| VER
    
    RET --> EMB
    REF --> RET
    VER --> ANSWER
    
    EMB --> VDB
    VDB -->|Top-K Docs| AGENT
    
    AGENT -->|Reasoning| LLM
    LLM -->|Response| AGENT
    
    CONFIG -.->|Load| EMB
    CONFIG -.->|Load| VDB
    CONFIG -.->|Load| LLM
    CONFIG -.->|Load| AGENT
    
    AGENT --> ANSWER
    
    style QUERY fill:#e3f2fd,color:#000
    style ANSWER fill:#c8e6c9,color:#000
    style AGENT fill:#fff9c4,color:#000
    style LLM fill:#ffccbc,color:#000
    style CONFIG fill:#f3e5f5,color:#000
    style EMB fill:#ffe0b2,color:#000
    style VDB fill:#ffe0b2,color:#000
    style RET fill:#f3e5f5,color:#000
    style REF fill:#f3e5f5,color:#000
    style VER fill:#f3e5f5,color:#000
```

### 📊 Chi Tiết Các Thành Phần:

| Thành Phần | Chức Năng |
|-----------|-----------|
| **🤖 AGENT** | Reasoning loop: Analyze query → Decide action → Execute tools → Loop until confident |
| **🔧 TOOLS** (3 công cụ) | **Retrieve**: Tìm docs từ KB; **Refine**: Sửa query; **Verify**: Kiểm tra quality |
| **🧬 Embedding** | BAAI/bge-m3 model: chuyển text → 768-dim vectors |
| **📦 Chroma DB** | Vector store: lưu embeddings + docs, tìm similarity |
| **🧠 LLM** | Mistral 7B: Reasoning, generating answers, answering queries |
| **⚙️ Config** | YAML: Quản lý tất cả settings (model, paths, thresholds) |
| **✅ Answer** | Output cuối cùng: Answer + Sources + Confidence score |

---

## 2. Agent Reasoning Loop (Tối Ưu cho PDF - Hình Chữ Nhật)

```mermaid
graph TB
    START["🚀 START<br/>Query Input"]
    
    THINK["<b>💭 THINK</b><br/>Analyze docs<br/>Plan action"]
    
    DECIDE{{"<b>🎯 DECIDE</b><br/>Action?<br/>1/2/3/4"}}
    
    subgraph TOOLS["🔧 ACTION TOOLS"]
        RET["<b>🔍 Retrieve</b><br/>Search<br/>docs"]
        REF["<b>✏️ Refine</b><br/>Rephrase<br/>query"]
        VER["<b>✓ Verify</b><br/>Check<br/>quality"]
    end
    
    subgraph EMBD["🧬 EMBEDDING & RETRIEVAL"]
        EMB["Embedding Model<br/>BAAI/bge-m3"]
        VDB["Chroma DB<br/>Vector Store"]
    end
    
    COMBINE["🧠 UPDATE STATE<br/>Store docs + Track history"]
    
    CHECK{{"<b>✓ CHECK</b><br/>Ready?<br/>Conf > 0.8"}}
    
    GEN["📊 GENERATE<br/>Create Final Answer"]
    
    RETURN["✅ RETURN<br/>Answer + Sources"]
    
    START --> THINK
    THINK --> DECIDE
    
    DECIDE -->|Action 1| RET
    DECIDE -->|Action 2| REF
    DECIDE -->|Action 3| VER
    DECIDE -->|Action 4| GEN
    
    RET --> EMB
    REF -->|Refined Query| RET
    VER -.->|align| EMB
    
    EMB --> VDB
    VDB -->|Top-K Docs| COMBINE
    VER --> COMBINE
    
    COMBINE --> CHECK
    
    CHECK -->|❌ No| THINK
    CHECK -->|✅ Yes| GEN
    
    GEN --> RETURN
    
    style START fill:#4caf50,color:#fff
    style RETURN fill:#4caf50,color:#fff
    style THINK fill:#fff9c4,color:#000
    style DECIDE fill:#2196f3,color:#fff
    style CHECK fill:#2196f3,color:#fff
    style COMBINE fill:#f3e5f5,color:#000
    style TOOLS fill:none,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5
    style RET fill:#e8f5e9,color:#000
    style REF fill:#e8f5e9,color:#000
    style VER fill:#e8f5e9,color:#000
    style EMBD fill:none,stroke:#666,stroke-width:2px,stroke-dasharray: 5 5
    style EMB fill:#ffe0b2,color:#000
    style VDB fill:#ffe0b2,color:#000
    style GEN fill:#c8e6c9,color:#000
```

### 📋 Giải Thích Chức Năng Các Node:

| Node | Chức Năng | Chi Tiết |
|------|-----------|----------|
| **🧠 LLM REASONING** | Subgraph chứa THINK + DECIDE (gọi LLM) | Mistral 7B xử lý reasoning logic |
| **💭 THINK** | LLM phân tích tài liệu, lập kế hoạch | Nhập: docs hiện có, query; Xuất: suy luận, plan hành động |
| **🎯 DECIDE** | LLM chọn 1 trong 4 actions | Dựa trên suy luận từ THINK |
| **🔧 ACTION TOOLS** | Subgraph gồm 3 công cụ chính | Được gọi theo quyết định từ DECIDE |
| **🔍 Retrieve** | Embed query → Tìm docs từ Chroma | Action 1: Tìm kiếm tài liệu |
| **✏️ Refine** | Tạo query thay thế | Action 2: Cải thiện query nếu cần |
| **✓ Verify** | Đánh giá confidence score | Action 3: Kiểm tra chất lượng answer |
| **🧬 EMBEDDING & RETRIEVAL** | Subgraph: Embedding Model + Chroma DB | Được gọi từ Retrieve tool |
| **🧠 UPDATE STATE** | Lưu docs, track iteration history | Cập nhật state sau mỗi action |
| **✓ CHECK** | Kiểm tra điều kiện dừng | Nếu confidence > 0.8 → GENERATE; Else → THINK |
| **📊 GENERATE** | Tổng hợp docs, tạo answer cuối | Gọi LLM tạo answer final |

**Loop Logic:**
- START → THINK (gọi LLM)
- THINK → DECIDE (gọi LLM chọn action)
- DECIDE → Chọn 1 trong 4 Actions
  - Action 1 (Retrieve) → gọi Embedding + Chroma
  - Action 2 (Refine) → tạo query mới → gọi lại Retrieve
  - Action 3 (Verify) → gọi LLM check quality
  - Action 4 (Generate) → tạo final answer
- UPDATE STATE → lưu kết quả
- CHECK → (No) → quay THINK | (Yes) → GENERATE

---

## 3. Data Flow: Query → Retrieval → Answer

```mermaid
graph LR
    subgraph PHASE1["Phase 1: Query Processing"]
        Q1["Student Query"]
        Q2["Embed Query<br/>BAAI/bge-m3"]
        Q3["Query Vector<br/>768-dim"]
    end
    
    subgraph PHASE2["Phase 2: Retrieval"]
        R1["Search in Chroma<br/>similarity_search_with_score"]
        R2["Get top-K candidates<br/>k=5"]
        R3["Filter by threshold<br/>score > 0.5"]
        R4["Retrieved Documents<br/>+ Similarity Scores"]
    end
    
    subgraph PHASE3["Phase 3: Agent Reasoning"]
        A1["Agent Process:"]
        A2["- Extract key facts"]
        A3["- Combine information"]
        A4["- Check gaps"]
        A5["Decide: Need more<br/>or Ready to answer?"]
    end
    
    subgraph PHASE4["Phase 4: LLM Generation"]
        G1["Feed context to Mistral"]
        G2["System Prompt: You are<br/>regulation expert..."]
        G3["Context: [Retrieved docs]"]
        G4["Generate Answer<br/>with reasoning"]
        G5["Final Answer<br/>with sources cited"]
    end
    
    Q1 --> Q2
    Q2 --> Q3
    Q3 --> R1
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> A1
    A1 --> A2
    A2 --> A3
    A3 --> A4
    A4 --> A5
    A5 -->|Need More| R1
    A5 -->|Ready| G1
    G1 --> G2
    G2 --> G3
    G3 --> G4
    G4 --> G5
    
    style PHASE1 fill:#e3f2fd
    style PHASE2 fill:#f3e5f5
    style PHASE3 fill:#fff9c4
    style PHASE4 fill:#e8f5e9
```

---

## 4. Component Architecture

```mermaid
graph TB
    subgraph APP_LAYER["Application Layer"]
        APP["app.py<br/>Streamlit UI"]
        API["api.py<br/>REST API"]
    end
    
    subgraph AGENT_LAYER["Agent & Orchestration Layer"]
        AGENT_CORE["AgentCore<br/>- reasoning_loop()<br/>- think()<br/>- decide()<br/>- act()"]
        PROMPT_MGR["PromptManager<br/>- system prompts<br/>- reasoning templates<br/>- decision prompts"]
        STATE_MGR["StateManager<br/>- track iterations<br/>- store docs<br/>- confidence score"]
    end
    
    subgraph TOOLS_LAYER["Tools Layer"]
        RETRIEVER_TOOL["RetrieverTool<br/>query → top-k docs"]
        REFINER_TOOL["RefinerTool<br/>query → refined queries"]
        EXTRACTOR_TOOL["ExtractorTool<br/>docs → facts"]
        VERIFIER_TOOL["VerifierTool<br/>answer → confidence"]
    end
    
    subgraph EMBEDDING_LAYER["Embedding & Retrieval"]
        EMBEDDINGS["EmbeddingModelManager<br/>- Load BAAI/bge-m3<br/>- Cache models<br/>- Batch embedding"]
        VDB_MGR["VectorDatabaseManager<br/>- Chroma client<br/>- similarity_search()<br/>- add_documents()"]
    end
    
    subgraph DATA_LAYER["Data Processing Layer"]
        PDF_PROC["PDFProcessor<br/>- Extract text<br/>- Clean data<br/>- Extract tables"]
        CHUNKER["TextChunker<br/>- Split by headers<br/>- Chunk by size<br/>- Preserve tables"]
        PIPELINE["DataPreparationPipeline<br/>- Orchestrate steps<br/>- Save chunks"]
    end
    
    subgraph STORAGE_LAYER["Storage Layer"]
        VECTOR_STORE["🗃️ Chroma DB<br/>./data/chroma"]
        CONFIG_FILE["⚙️ config.yaml<br/>All settings"]
        CHUNK_STORE["📦 Chunks JSON<br/>./data/chunks"]
        RAW_DATA["📄 PDF Files<br/>./knowledge_base/raw"]
    end
    
    subgraph LLM_LAYER["LLM Backend"]
        OLLAMA_SVC["Ollama Service<br/>mistral:7b"]
    end
    
    APP --> AGENT_CORE
    API --> AGENT_CORE
    
    AGENT_CORE --> PROMPT_MGR
    AGENT_CORE --> STATE_MGR
    
    AGENT_CORE --> RETRIEVER_TOOL
    AGENT_CORE --> REFINER_TOOL
    AGENT_CORE --> EXTRACTOR_TOOL
    AGENT_CORE --> VERIFIER_TOOL
    
    RETRIEVER_TOOL --> EMBEDDINGS
    RETRIEVER_TOOL --> VDB_MGR
    
    REFINER_TOOL --> OLLAMA_SVC
    VERIFIER_TOOL --> OLLAMA_SVC
    AGENT_CORE --> OLLAMA_SVC
    
    VDB_MGR --> VECTOR_STORE
    EMBEDDINGS --> CONFIG_FILE
    
    PDF_PROC --> CHUNKER
    CHUNKER --> PIPELINE
    PIPELINE --> CHUNK_STORE
    PIPELINE --> VDB_MGR
    
    RAW_DATA --> PDF_PROC
    CONFIG_FILE -.-> EMBEDDINGS
    CONFIG_FILE -.-> VDB_MGR
    CONFIG_FILE -.-> OLLAMA_SVC
    
    style APP_LAYER fill:#e3f2fd
    style AGENT_LAYER fill:#fff9c4
    style TOOLS_LAYER fill:#f3e5f5
    style EMBEDDING_LAYER fill:#ffe0b2
    style DATA_LAYER fill:#ffccbc
    style STORAGE_LAYER fill:#c8e6c9
    style LLM_LAYER fill:#ffebee
```

---

## 5. Iteration Control & Termination

```mermaid
graph TD
    A["Start Iteration"]
    B["iteration_count++"]
    C{"Max iterations<br/>reached?<br/>count >= 5"}
    D{"Confidence<br/>score<br/>> 0.80?"}
    E{"New docs<br/>retrieved?"}
    F["No new docs<br/>& iteration > 1"]
    
    G["Continue to<br/>next iteration"]
    H["Confidence<br/>achieved ✓"]
    I["Force generate<br/>answer<br/>(timeout)"]
    J["No improvement<br/>detected"]
    
    K["Generate Final<br/>Answer"]
    
    A --> B
    B --> C
    C -->|Yes| I
    C -->|No| D
    D -->|Yes| H
    D -->|No| E
    E -->|Yes| G
    E -->|No| F
    F -->|True| J
    F -->|False| G
    
    H --> K
    I --> K
    J --> K
    G --> A
    
    style H fill:#4caf50,color:#fff
    style I fill:#ff9800,color:#fff
    style J fill:#f44336,color:#fff
    style K fill:#2196f3,color:#fff
```

---

## 6. Query Example: Complex Regulation Question

```mermaid
graph LR
    Q["Q: 'Nếu tôi chưa đạt GPA 2.0<br/>sau 2 năm, quy định gì?<br/>Có thể hoãn học?'"]
    
    I1["🔄 Iteration 1<br/>Thought: Need GPA policy<br/>& deferment info<br/>Action: RETRIEVE<br/>Query: GPA 2.0"]
    
    D1["Docs: GPA Policy<br/>but no deferment"]
    
    I2["🔄 Iteration 2<br/>Thought: Found GPA,<br/>but deferment missing<br/>Action: RETRIEVE<br/>Query: 'hoãn học'"]
    
    D2["Docs: Deferment<br/>Policy found ✓"]
    
    I3["🔄 Iteration 3<br/>Thought: Have both infos<br/>Confidence: 0.88<br/>Action: ANSWER"]
    
    GEN["Generate with Mistral<br/>Context: [GPA docs +<br/>Deferment docs]"]
    
    ANS["Answer: 'Yes, you can<br/>defer up to 1 year.<br/>GPA < 2.0 prevents<br/>normal continuation,<br/>but deferment available<br/>per Section 5.'<br/>Sources: Sec 3, Sec 5"]
    
    Q --> I1
    I1 --> D1
    D1 --> I2
    I2 --> D2
    D2 --> I3
    I3 --> GEN
    GEN --> ANS
    
    style Q fill:#e3f2fd
    style I1 fill:#fff9c4
    style I2 fill:#fff9c4
    style I3 fill:#fff9c4
    style ANS fill:#c8e6c9
```

---

## 7. System Configuration Flow

```mermaid
graph TD
    CONFIG["config.yaml<br/>Master Config"]
    
    EMBEDDING_CFG["embedding:<br/>- model_name<br/>- cache_folder<br/>- batch_size<br/>- dimension"]
    
    RETRIEVAL_CFG["retrieval:<br/>- top_k: 5<br/>- similarity_threshold: 0.5<br/>- semantic_weight<br/>- keyword_weight"]
    
    CHUNKING_CFG["chunking:<br/>- chunk_size: 1000<br/>- chunk_overlap: 200<br/>- markdown_headers"]
    
    PDF_CFG["pdf_processing:<br/>- text_cleanup_patterns<br/>- metadata_mapping"]
    
    VDB_CFG["vectordb:<br/>- persist_directory<br/>- collection_name<br/>- provider: chroma"]
    
    LLM_CFG["llm:<br/>- model: mistral<br/>- temperature: 0.3<br/>- max_tokens"]
    
    AGENT_CFG["agent:<br/>- max_iterations: 5<br/>- confidence_threshold<br/>- reasoning_type"]
    
    EM["EmbeddingModelManager<br/>reads embedding"]
    VDB_MGR["VectorDatabaseManager<br/>reads retrieval<br/>+ vectordb"]
    PDF_PROC["PDFProcessor<br/>reads pdf_processing<br/>+ chunking"]
    AGENT["AgentCore<br/>reads agent<br/>+ llm"]
    
    CONFIG --> EMBEDDING_CFG
    CONFIG --> RETRIEVAL_CFG
    CONFIG --> CHUNKING_CFG
    CONFIG --> PDF_CFG
    CONFIG --> VDB_CFG
    CONFIG --> LLM_CFG
    CONFIG --> AGENT_CFG
    
    EMBEDDING_CFG --> EM
    RETRIEVAL_CFG --> VDB_MGR
    VDB_CFG --> VDB_MGR
    PDF_CFG --> PDF_PROC
    CHUNKING_CFG --> PDF_PROC
    LLM_CFG --> AGENT
    AGENT_CFG --> AGENT
    
    style CONFIG fill:#2196f3,color:#fff
    style EM fill:#4caf50,color:#fff
    style VDB_MGR fill:#4caf50,color:#fff
    style PDF_PROC fill:#4caf50,color:#fff
    style AGENT fill:#4caf50,color:#fff
```

---

## 📋 Chú Thích

- **🤖 Agent**: Quyết định what to do next dựa trên LLM reasoning
- **🔄 Iteration Loop**: Tối đa 5 vòng, dừng khi confident hoặc hết vòng
- **🔍 Retriever**: Lấy top-K documents từ Chroma vector store
- **✏️ Refiner**: Tạo query synonyms nếu cần tìm lại
- **✓ Verifier**: Kiểm tra confidence score của answer
- **📦 Chroma DB**: Vector database lưu embeddings của tất cả chunks
- **🧬 BAAI/bge-m3**: Multilingual embedding model 768-dim
- **🔌 Mistral 7B**: Local LLM via Ollama, không qua cloud

---

## 🎯 Key Features

✅ **Multi-iteration reasoning** - Agent tự refine query nếu cần  
✅ **Confidence-based** - Dừng khi confidence > 0.80  
✅ **Tool-based** - Modular tools (retrieve, refine, verify, extract)  
✅ **Config-driven** - Tất cả settings từ config.yaml  
✅ **Local & Private** - Ollama + Chroma, no cloud APIs  
✅ **Source attribution** - Trả lại source của mỗi answer
