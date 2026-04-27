# Agentic RAG - Kiến Trúc Tổng Thể (Mermaid Diagram)

## 1. Toàn Bộ Luồng Hệ Thống

```mermaid
graph LR
    Q["<b>📝 User Query</b><br/>Có thể hoãn học<br/>nếu GPA < 2.0?"]
    
    AGENT["<b>🤖 Agent</b><br/>Think<br/>Decide<br/>Act"]
    
    RETRIEVER["<b>🔍 Retriever</b><br/>Embed query<br/>Search Chroma<br/>Get top-K"]
    
    EMBED["<b>🧬 Embedding</b><br/>BAAI/bge-m3<br/>768-dim"]
    
    VDB["<b>📦 Chroma DB</b><br/>Vector Store<br/>./data/chroma"]
    
    LLM["<b>🧠 Mistral 7B</b><br/>Ollama<br/>Local LLM"]
    
    VERIFY["<b>✓ Verify</b><br/>Check<br/>Confidence"]
    
    ANSWER["<b>✅ Answer</b><br/>With Sources<br/>& Score"]
    
    Q -->|Query| AGENT
    AGENT -->|Retrieve| RETRIEVER
    RETRIEVER -->|Embed| EMBED
    EMBED -->|Vector| VDB
    VDB -->|Top-K Docs| AGENT
    
    AGENT -->|Context| LLM
    LLM -->|Thought| AGENT
    LLM -->|Answer| VERIFY
    
    VERIFY -->|High Confidence| ANSWER
    VERIFY -->|Low Confidence| AGENT
    
    ANSWER -->|Result| Q
    
    style Q fill:#e1f5ff
    style ANSWER fill:#c8e6c9
    style AGENT fill:#fff9c4
    style LLM fill:#ffccbc
    style VDB fill:#ffe0b2
    style EMBED fill:#f3e5f5
    style RETRIEVER fill:#e8f5e9
    style VERIFY fill:#f3e5f5
```

---

## 2. Agent Reasoning Loop (Chi Tiết)

```mermaid
graph TD
    START["🚀 START"]
    THINK["💭 THINK<br/>Analyze query<br/>Review docs"]
    DECIDE{"What<br/>next?"}
    RETRIEVE["🔍 RETRIEVE<br/>Get docs"]
    REFINE["✏️ REFINE<br/>Better query"]
    CHECK{"Enough<br/>info?"}
    CONFIDENCE{"Confidence<br/>> 0.80?"}
    ANSWER["✅ GENERATE<br/>Final answer"]
    VERIFY["✓ VERIFY<br/>Check quality"]
    RETURN["🎁 RETURN<br/>to User"]
    MAXITER{"Max iter<br/>reached?"}
    
    START --> THINK
    THINK --> DECIDE
    
    DECIDE -->|Need docs| RETRIEVE
    DECIDE -->|Query unclear| REFINE
    DECIDE -->|Ready| CHECK
    
    RETRIEVE --> CHECK
    REFINE --> RETRIEVE
    
    CHECK -->|No| THINK
    CHECK -->|Yes| CONFIDENCE
    
    CONFIDENCE -->|No| THINK
    CONFIDENCE -->|Yes| ANSWER
    MAXITER -->|Yes| ANSWER
    MAXITER -->|No| THINK
    
    ANSWER --> VERIFY
    VERIFY --> RETURN
    
    THINK -.->|After iteration| MAXITER
    
    style START fill:#4caf50,color:#fff
    style RETURN fill:#4caf50,color:#fff
    style DECIDE fill:#fff9c4
    style CHECK fill:#fff9c4
    style CONFIDENCE fill:#fff9c4
    style MAXITER fill:#ff9800,color:#fff
    style ANSWER fill:#c8e6c9
```

---

## 3. Data Flow: Query → Retrieval → Answer

```mermaid
graph LR
    Q["📝 Query"]
    EMBED["🧬 Embed<br/>BAAI/bge-m3"]
    SEARCH["🔍 Search<br/>Chroma"]
    DOCS["📦 Top-K Docs<br/>k=5"]
    FILTER["Filter<br/>score > 0.5"]
    REASON["🧠 Reason<br/>Extract facts"]
    DECIDE{"Ready?"}
    LLM["🧠 Mistral"]
    ANSWER["✅ Answer<br/>+ Sources"]
    
    Q --> EMBED
    EMBED --> SEARCH
    SEARCH --> DOCS
    DOCS --> FILTER
    FILTER --> REASON
    REASON --> DECIDE
    DECIDE -->|No| SEARCH
    DECIDE -->|Yes| LLM
    LLM --> ANSWER
    
    style Q fill:#e1f5ff
    style ANSWER fill:#c8e6c9
    style DECIDE fill:#fff9c4
    style LLM fill:#ffccbc
```

---

## 4. Component Architecture

```mermaid
graph TB
    APP["🖥️ UI Layer<br/>Streamlit App"]
    AGENT["🤖 Agent Core<br/>Think/Decide/Act"]
    TOOLS["🔧 Tools<br/>Retrieve/Refine/Verify"]
    EMBED["🧬 Embeddings<br/>BAAI/bge-m3"]
    VDB["📦 Vector DB<br/>Chroma"]
    LLM["🧠 LLM<br/>Mistral 7B"]
    DATA["📄 Data Pipeline<br/>PDF→Chunks"]
    CONFIG["⚙️ Config"]
    STORAGE["💾 Storage<br/>Chroma + JSON"]
    
    APP --> AGENT
    AGENT --> TOOLS
    AGENT --> LLM
    TOOLS --> EMBED
    EMBED --> VDB
    VDB --> STORAGE
    DATA --> STORAGE
    CONFIG -.-> AGENT
    CONFIG -.-> EMBED
    CONFIG -.-> VDB
    CONFIG -.-> LLM
    
    style APP fill:#e3f2fd
    style AGENT fill:#fff9c4
    style TOOLS fill:#f3e5f5
    style EMBED fill:#ffe0b2
    style VDB fill:#e8f5e9
    style LLM fill:#ffccbc
    style STORAGE fill:#c8e6c9
    style CONFIG fill:#2196f3,color:#fff
```

---

## 5. Iteration Control & Termination

```mermaid
graph TD
    START["Start Iteration"]
    ITER{"iteration<br/>count++"}
    MAXCHECK{"count >= 5?"}
    CONFCHECK{"Confidence<br/>> 0.80?"}
    NEWDOCS{"New docs<br/>found?"}
    
    CONTINUE["Continue<br/>Next iter"]
    SUCCESS["✓ Done<br/>High confidence"]
    TIMEOUT["⏱️ Timeout<br/>Force answer"]
    NOIMPROVE["ℹ️ No new info<br/>Answer now"]
    ANSWER["📊 Generate<br/>Final Answer"]
    
    START --> ITER
    ITER --> MAXCHECK
    MAXCHECK -->|Yes| TIMEOUT
    MAXCHECK -->|No| CONFCHECK
    CONFCHECK -->|Yes| SUCCESS
    CONFCHECK -->|No| NEWDOCS
    NEWDOCS -->|Yes| CONTINUE
    NEWDOCS -->|No| NOIMPROVE
    
    SUCCESS --> ANSWER
    TIMEOUT --> ANSWER
    NOIMPROVE --> ANSWER
    CONTINUE --> START
    
    style SUCCESS fill:#4caf50,color:#fff
    style TIMEOUT fill:#ff9800,color:#fff
    style NOIMPROVE fill:#f44336,color:#fff
    style ANSWER fill:#2196f3,color:#fff
```

---

## 6. Query Example: Complex Regulation Question

```mermaid
graph LR
    Q["<b>Q:</b><br/>GPA < 2.0<br/>+ Hoãn học?"]
    
    I1["<b>Iter 1:</b><br/>🔍 Retrieve<br/>GPA 2.0"]
    D1["GPA docs<br/>✓<br/>No deferment<br/>❌"]
    
    I2["<b>Iter 2:</b><br/>🔍 Retrieve<br/>Hoãn học"]
    D2["Deferment docs<br/>✓"]
    
    I3["<b>Iter 3:</b><br/>✓ Confident<br/>0.88"]
    
    ANS["<b>Answer:</b><br/>Yes, defer<br/>up to 1 year<br/>Sources: Sec 3,5"]
    
    Q --> I1
    I1 --> D1
    D1 --> I2
    I2 --> D2
    D2 --> I3
    I3 --> ANS
    
    style Q fill:#e3f2fd
    style I1 fill:#fff9c4
    style I2 fill:#fff9c4
    style I3 fill:#fff9c4
    style ANS fill:#c8e6c9
    style D1 fill:#ffecb3
    style D2 fill:#c8e6c9
```

---

## 7. System Configuration Flow

```mermaid
graph TD
    CONFIG["<b>⚙️ config.yaml</b><br/>Master Config"]
    
    EMBED_SET["🧬 Embedding<br/>model_name<br/>cache_folder"]
    RET_SET["🔍 Retrieval<br/>top_k: 5<br/>threshold: 0.5"]
    CHUNK_SET["✂️ Chunking<br/>size: 1000<br/>overlap: 200"]
    PDF_SET["📄 PDF<br/>cleanup patterns<br/>metadata"]
    VDB_SET["📦 VectorDB<br/>Chroma<br/>directory"]
    LLM_SET["🧠 LLM<br/>mistral<br/>temperature"]
    AGENT_SET["🤖 Agent<br/>max_iter: 5<br/>confidence"]
    
    EM["EmbeddingModelManager"]
    VDB_MGR["VectorDatabaseManager"]
    PDF_PROC["PDFProcessor"]
    AGENT["AgentCore"]
    
    CONFIG --> EMBED_SET
    CONFIG --> RET_SET
    CONFIG --> CHUNK_SET
    CONFIG --> PDF_SET
    CONFIG --> VDB_SET
    CONFIG --> LLM_SET
    CONFIG --> AGENT_SET
    
    EMBED_SET --> EM
    RET_SET --> VDB_MGR
    VDB_SET --> VDB_MGR
    CHUNK_SET --> PDF_PROC
    PDF_SET --> PDF_PROC
    LLM_SET --> AGENT
    AGENT_SET --> AGENT
    
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
