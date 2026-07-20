# 04. System Architecture - Kiến Trúc Hệ Thống Chatbot AgenticRAG

## 📚 Mục Tiêu
Hiểu **kiến trúc toàn bộ hệ thống** chatbot của bạn - các thành phần, cách chúng liên kết, data flow, và deployment architecture.

---

## 1. High-Level System Architecture

### 1.1 Logical Architecture (What Does What)

```
┌─────────────────────────────────────────────────────────────────────┐
│                     STUDENT CHATBOT SYSTEM                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐                                                   │
│  │   FRONTEND   │  (Streamlit UI)                                   │
│  │   Layer      │  └─ User Input/Output                            │
│  │              │  └─ Chat History (session)                       │
│  │              │  └─ Language Display                             │
│  └────────┬─────┘                                                   │
│           │ API Call: query + session_id                           │
│           ▼                                                         │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         ORCHESTRATION LAYER (Main Logic)                   │   │
│  │                                                            │   │
│  │  [Query Processor]                                         │   │
│  │  ├─ Language Detection                                    │   │
│  │  ├─ Input Cleaning/Validation                             │   │
│  │  └─ Session Management                                    │   │
│  │                                                            │   │
│  │  [AGENT ORCHESTRATOR] ⭐ Main Decision Maker              │   │
│  │  ├─ Initialize Agent with query                           │   │
│  │  ├─ Loop (max 5 iterations):                              │   │
│  │  │  ├─ Agent.think() → Decide action                      │   │
│  │  │  ├─ If RETRIEVE → Call Retriever                       │   │
│  │  │  ├─ If REFINE → Call Query Refiner                     │   │
│  │  │  ├─ If VERIFY → Call Verifier                          │   │
│  │  │  └─ If ANSWER → Exit loop                              │   │
│  │  └─ Return collected context                              │   │
│  │                                                            │   │
│  └────────┬──────────────────────────────────────────────────┘   │
│           │                                                        │
│        ┌──┴────────────────────────────────────────────────┐      │
│        │                                                  │        │
│        ▼                                                  ▼        │
│  ┌──────────────────┐                        ┌───────────────┐   │
│  │ RETRIEVAL LAYER  │                        │ REASONING     │   │
│  │                  │                        │ LAYER         │   │
│  │ [Retriever Tool] │                        │               │   │
│  │ ├─ Query Embed   │                        │ [LLM Calls]   │   │
│  │ ├─ Semantic Ser  │                        │ ├─ Agent      │   │
│  │ ├─ BM25 Search   │                        │ │  Logic      │   │
│  │ ├─ Hybrid Rank   │                        │ ├─ Query      │   │
│  │ ├─ Re-rank       │                        │ │  Refining   │   │
│  │ └─ Return Docs   │                        │ └─ Answer     │   │
│  │                  │                        │    Generation │   │
│  │ [Refiner Tool]   │                        │               │   │
│  │ └─ Query improve │                        │ [Local LLM:   │   │
│  │                  │                        │  Ollama +     │   │
│  │ [Verifier Tool]  │                        │  Mistral 7B]  │   │
│  │ └─ Score anwer   │                        │               │   │
│  │                  │                        │               │   │
│  └────────┬─────────┘                        └────────┬──────┘   │
│           │                                          │            │
│           └──────────────────┬───────────────────────┘            │
│                              ▼                                     │
│                    ┌──────────────────┐                            │
│                    │ GENERATION LAYER │                            │
│                    │                  │                            │
│                    │ [Answer Builder] │                            │
│                    │ ├─ Combine docs  │                            │
│                    │ ├─ Format answer │                            │
│                    │ ├─ Add sources   │                            │
│                    │ ├─ Detect output │                            │
│                    │ │  language      │                            │
│                    │ └─ Return result │                            │
│                    │                  │                            │
│                    └─────────┬────────┘                            │
│                              ▼                                     │
│                    ┌──────────────────┐                            │
│                    │ LOGGING LAYER    │                            │
│                    │ ├─ Query log     │                            │
│                    │ ├─ Answer log    │                            │
│                    │ ├─ Retrieval log │                            │
│                    │ ├─ Agent iters   │                            │
│                    │ └─ User feedback │                            │
│                    │                  │                            │
│                    └─────────┬────────┘                            │
│                              ▼                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         STORAGE LAYER                                      │   │
│  │                                                            │   │
│  │  [Vector Store]        [LLM Service]      [Logs]          │   │
│  │  └─ Chroma DB          └─ Ollama          └─ SQLite       │   │
│  │     (cached              (local LLM)         (metrics)     │   │
│  │     embeddings           model serving)                    │   │
│  │                                                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐   │
│  │         KNOWLEDGE BASE LAYER                               │   │
│  │                                                            │   │
│  │  [PDF Docs]            [Processed Chunks]                 │   │
│  │  └─ Regulations PDF    └─ .txt files                      │   │
│  │  └─ Policies.pdf          (split by section)              │   │
│  │  └─ ...                   (metadata tagged)                │   │
│  │                                                            │   │
│  └────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow: Query → Answer

### 2.1 Complete Data Flow Diagram

```
ENTRY POINT:
  Student types: "Học phí năm nhất bao nhiêu?"
  (in Streamlit UI)
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 1: Query Input & Processing                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Input: {                                                      │
│    "query": "Học phí năm nhất bao nhiêu?",                    │
│    "session_id": "session_xyz",                               │
│    "language": "auto"  # auto-detect                          │
│  }                                                              │
│                                                                │
│  Processing:                                                   │
│  ├─ Validate input                                             │
│  ├─ Detect language: Vietnamese ✓                             │
│  ├─ Clean text (optional normalization)                        │
│  └─ Pass to Agent                                              │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 2: Agent Reasoning Loop (Iteration 1)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Agent.think()                                                 │
│  ├─ LLM Call #1: "Given this query, what should I do?"        │
│  ├─ LLM Response: "RETRIEVE docs about 'tuition' + '1st year'"│
│  │                                                              │
│  └─ Decision: RETRIEVE ✓                                       │
│                                                                │
│  (Note: If decision was REFINE/ANSWER/VERIFY, branch differ) │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 3: Retrieve Relevant Documents                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Call: Retriever.search(                                       │
│    query="Học phí năm nhất bao nhiêu?",                       │
│    top_k=5                                                     │
│  )                                                              │
│                                                                │
│  Process:                                                      │
│  ├─ Embed query: "Học phí..." → [0.12, -0.34, ...]           │
│  │                                                              │
│  ├─ Semantic Search (Cosine similarity)                        │
│  │  ├─ Compare with doc embeddings in Chroma DB              │
│  │  ├─ Get scores: [0.92, 0.87, 0.75, 0.68, 0.55]           │
│  │  └─ Top 5 docs                                             │
│  │                                                              │
│  ├─ BM25 Keyword Search                                        │
│  │  ├─ Search: "học phí" OR "tuition"                        │
│  │  └─ BM25 scores: [0.88, 0.82, ...]                        │
│  │                                                              │
│  └─ Hybrid Re-ranking                                          │
│     └─ Combined score = 0.6*semantic + 0.4*bm25               │
│        Final ranking: [Doc_A, Doc_B, Doc_C, Doc_D, Doc_E]     │
│                                                                │
│  Result: {                                                     │
│    "docs": [                                                   │
│      {                                                         │
│        "content": "Học phí năm nhất: 8 triệu VND...",        │
│        "source": "Regulations.pdf:page_12",                   │
│        "score": 0.90,                                          │
│        "lang": "vi"                                            │
│      },                                                        │
│      {...},                                                    │
│      ...                                                       │
│    ]                                                           │
│  }                                                              │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 4: Agent Decision Check                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Agent.check_confidence()                                      │
│  ├─ LLM Call #2: "Is retrieved info sufficient?"              │
│  ├─ Confidence score: 0.92                                     │
│  │                                                              │
│  └─ Decision:                                                  │
│     if confidence > 0.85: ANSWER ✓                             │
│     else: REFINE & RETRIEVE again                              │
│                                                                │
│  → Sufficient info found! Proceed to answer.                   │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 5: Answer Generation                                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Prepare Augmented Prompt:                                     │
│  """                                                           │
│  You are a helpful student advisor chatbot.                    │
│  Answer based ONLY on the provided documents.                  │
│  If info not available, say "I don't know".                    │
│  Answer in Vietnamese (as user asked).                        │
│                                                                │
│  User Query: Học phí năm nhất bao nhiêu?                      │
│                                                                │
│  Relevant Documents:                                           │
│  1. Regulations.pdf:page_12                                    │
│     "Học phí năm nhất: 8 triệu VND, 
│      không bao gồm dorm + meals"                              │
│  2. TuitionPolicy.txt                                          │
│     "Payment deadline: September 15..."                        │
│                                                                │
│  Answer:                                                       │
│  """                                                           │
│                                                                │
│  Call LLM:                                                     │
│  ├─ LLM Call #3: Generate answer using above prompt           │
│  ├─ LLM Response: "Học phí năm nhất là 8 triệu VND."         │
│  │               "Deadline thanh toán: 15/9."                │
│  │               "(Source: Regulations.pdf:p12)"              │
│  │                                                              │
│  └─ Answer generated ✓                                         │
│                                                                │
│  Format Output:                                                │
│  {                                                             │
│    "answer": "Học phí năm nhất là 8 triệu VND...",           │
│    "sources": [                                                │
│      {"file": "Regulations.pdf", "page": 12},                 │
│      {"file": "TuitionPolicy.txt", "section": 2}              │
│    ],                                                          │
│    "confidence": 0.92,                                         │
│    "iterations": 1,                                            │
│    "output_language": "vi"                                     │
│  }                                                              │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
┌─────────────────────────────────────────────────────────────────┐
│ STEP 6: Logging & Return                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                │
│  Log to Database:                                              │
│  ├─ query: "Học phí năm nhất bao nhiêu?"                      │
│  ├─ query_language: "vi"                                       │
│  ├─ retrieved_docs_count: 5                                    │
│  ├─ agent_iterations: 1                                        │
│  ├─ llm_calls: 3                                               │
│  ├─ latency_ms: 2340                                           │
│  ├─ answer: "Học phí năm nhất là 8 triệu VND..."             │
│  ├─ confidence: 0.92                                           │
│  └─ timestamp: 2025-04-09T10:30:45Z                           │
│                                                                │
│  Return to Frontend:                                           │
│  ├─ Display answer in Streamlit                               │
│  ├─ Show sources (clickable)                                  │
│  ├─ Add "Helpful?" feedback buttons                           │
│  └─ Add to conversation history                               │
│                                                                │
└────────────────┬────────────────────────────────────────────────┘
                 ▼
          END: Answer displayed to user ✓
```

---

## 3. Component Breakdown

### 3.1 Frontend Service
**Technology:** Streamlit
**Responsibilities:**
- Display chat interface
- Accept user input (Vietnamese or English)
- Show retrieved sources
- Conversation history
- Feedback mechanism

**Files:** `app.py`

### 3.2 Agent Orchestrator
**Technology:** LangChain Agent
**Responsibilities:**
- Invoke reasoning loop
- Manage tool calls (retrieve, refine, verify)
- Track iterations
- Confidence scoring
- Termination condition

**Files:** `src/agent/orchestrator.py`

### 3.3 Retriever Component
**Technology:** LangChain Retriever + Chroma
**Sub-components:**
- Semantic search (embeddings)
- BM25 search (keyword)
- Hybrid ranking
- Re-ranker

**Files:** `src/retrieval/retriever.py`

### 3.4 LLM Service
**Technology:** Ollama + Mistral 7B
**Responsibilities:**
- Agent reasoning (think/decide)
- Query refinement
- Answer generation
- Zero-knowledge responses

**Service:** Ollama runs locally on port 11434

### 3.5 Knowledge Base
**Storage:** Chroma Vector DB (local)
**Content:**
- Embedded student regulation documents
- Metadata (source, page, language, etc.)

**Data:** `knowledge_base/` folder

### 3.6 Logging Service
**Technology:** SQLite
**Tracks:**
- All queries & answers
- Retrieval metrics
- Agent iterations
- Latency

**Files:** `logs/chatbot.db`

---

## 4. Deployment Architecture

### 4.1 Local Development Setup

```
Developer Machine:
├─ Ollama (LLM service)
│  ├─ Runs on localhost:11434
│  └─ Mistral 7B model
│
├─ Python Application
│  ├─ Streamlit (frontend)
│  ├─ LangChain (orchestration)
│  └─ Application logic
│
├─ Chroma Vector DB
│  └─ Local storage (data/chroma/)
│
└─ SQLite Logs
   └─ Local storage (logs/chatbot.db)

All in-process, zero network calls outside.
Security: Max ✓
```

### 4.2 Production Setup (Optional)

```
Docker Compose:
├─ ollama-service
│  └─ Image: ollama:latest-mistral
│     Port: 11434
│
├─ chatbot-api
│  └─ Image: chatbot:latest
│     Port: 8501 (Streamlit)
│     Uses: ollama-service
│
├─ chroma-vector-store
│  └─ Image: chromadb/chroma:latest (if separate)
│     Port: 8000
│
└─ postgres (optional, for logs)
   └─ Image: postgres:15
      Port: 5432
```

---

## 5. Technology Choices Justification

| Component | Technology | Why |
|-----------|-----------|-----|
| **Frontend** | Streamlit | Fast prototyping, interactive, no frontend skills needed |
| **Framework** | LangChain | Standard for RAG/Agents, good community |
| **LLM** | Ollama + Mistral 7B | Local, private, 7B = balance accuracy/speed |
| **Embeddings** | Sentence-Transformers | Local, multilingual, lightweight |
| **Vector DB** | Chroma | Zero-setup, local, good for prototyping |
| **Logs** | SQLite | Simple, local, no extra dependencies |

---

## 6. Configuration File Structure

```yaml
# config.yaml
system:
  name: "Student Regulation Chatbot"
  version: "1.0.0"
  
frontend:
  framework: "streamlit"
  port: 8501
  theme: "light"
  
llm:
  provider: "ollama"
  model_name: "mistral"
  model_url: "http://localhost:11434"
  temperature: 0.3  # Lower = more deterministic
  max_tokens: 1024
  
embedding:
  model: "sentence-transformers/distiluse-base-multilingual-cased-v2"
  dimension: 768
  
vector_db:
  provider: "chroma"
  path: "./data/chroma"
  
retrieval:
  top_k: 5
  semantic_weight: 0.6
  keyword_weight: 0.4
  
agent:
  type: "react"  # Reasoning + Act
  max_iterations: 5
  confidence_threshold: 0.75
  
logging:
  level: "INFO"
  database: "./logs/chatbot.db"
  
knowledge_base:
  path: "./knowledge_base"
  languages: ["vi", "en"]
```

---

## 7. Key Metrics to Track

```
Performance:
├─ Query latency (target: <3s)
├─ Agent iterations (avg: 1-2)
├─ LLM calls per query (avg: 2-3)
├─ Retrieval accuracy (precision/recall)
└─ Answer quality (confidence > 0.75)

Usage:
├─ Queries/day
├─ Unique users/day
├─ Query languages (% Vi vs En)
└─ User feedback (helpful/not helpful)

System:
├─ API uptime
├─ Query error rate
├─ LLM response time
└─ Vector DB query time
```

---

## Summary 📝

| Layer | Purpose | Technology |
|-------|---------|-----------|
| **Frontend** | User interface | Streamlit |
| **Orchestration** | Agent logic | LangChain |
| **Reasoning** | LLM calls | Ollama + Mistral |
| **Retrieval** | Search KB | Semantic + BM25 |
| **Storage** | Vector + Logs | Chroma + SQLite |
| **KB** | Source data | PDF + embeddings |

---

## Next Steps

🔗 **Related Files:**
- `05-Tech-Stack-Explanation.md` - Why each technology choice
- `06-Data-Preparation-Guide.md` - How to build KB
- `08-Agent-Design.md` - Agent implementation details
- `11-Deployment-Guide.md` - Docker setup
