# 05. Tech Stack Explanation - Tại Sao Chọn Ollama, LangChain, Chroma?

## 📚 Mục Tiêu
Hiểu **quyết định công nghệ** - tại sao chọn từng framework/tool/library, trade-off của mỗi lựa chọn, và lựa chọn thay thế.

---

## 1. Overall Philosophy

### 1.1 Design Principles
✅ **Privacy-First:** Không gửi dữ liệu lên cloud
✅ **Local-Everything:** Toàn bộ chạy trên máy dev/server
✅ **Minimal Setup:** Không cần phức tạp dev-ops
✅ **Good Performance:** Trả lời trong 2-5s
✅ **Maintainable:** Dễ extend & debug

### 1.2 Trade-off Decisions
- **Accuracy vs Speed:** Mistral 7B ~ 85% accuracy of Llama 13B nhưng 2x nhanh
- **Setup Complexity vs Flexibility:** Ollama easy vs manual LLM serving
- **Embedding Accuracy vs Size:** multilingual-e5-base good for 100+ languages

---

## 2. LLM Service: Ollama + Mistral 7B

### 2.1 Why Ollama?

#### Alternatives Compared

| Option | Setup | Privacy | Speed | Maintenance | Cost |
|--------|-------|---------|-------|-------------|------|
| **Ollama (Recommended)** | ⭐ Easy | ✅ 100% | ⚡ Good | ⭐ Simple | Free |
| OpenAI API | 1 min | ❌ Cloud | Super fast | None | $$ |
| LM Studio | 15 min | ✅ Local | Good | Simple | Free |
| vLLM (DIY) | 30 min | ✅ Local | Faster | Medium | Free |
| Huggingface Inference | 10 min | ⚠️ Mixed | Good | Simple | Free tier |

#### Why Ollama Wins for DỰ ÁN

✅ **Easiest Setup**
```bash
# 1. Download Ollama
# 2. Run: ollama run mistral
# 3. Done! (That's it!)
```
Compare with vLLM:
```bash
# Install PyTorch, vLLM, handle CUDA, configure ports...
# More complex
```

✅ **Privacy First**
- Runs locally
- Model file stored locally
- Zero cloud communication
- Perfect for student data

✅ **Community & Docs**
- Popular in RAG community
- Good integration with LangChain
- Many model options (Mistral, Llama, Dolphin, etc.)

✅ **Model Management**
- Easy model switching
- Automatic model pulling
- Simple CLI interface

### 2.2 Why Mistral 7B (Not Llama 2)?

#### Comparison: Mistral 7B vs Llama Alternatives

| Metric | Mistral 7B | Llama 2 7B | Llama 2 13B |
|--------|-----------|-----------|-----------|
| **Speed** | ⚡⚡⚡ | ⚡⚡ | ⚡ |
| **Accuracy** | 🎯🎯 | 🎯 | 🎯🎯🎯 |
| **VRAM** | 4GB | 4GB | 8GB |
| **Latency/Query** | ~1s | ~1.2s | ~2.5s |
| **Multilingual** | Good | OK | OK |

#### Decision Matrix

**For DỰ ÁN:**
- ✅ Mistral 7B fits "local but accurate" sweet spot
- ✅ 4GB VRAM = works on most laptops/servers
- ✅ ~1s per token = acceptable for chat (answer ~20 tokens = 20s acceptable)
- ✅ Good reasoning for complex queries

**Scenario:**
- If student has powerful GPU → Llama 13B (better accuracy)
- If need ultra-fast → Mistral (even more optimized)
- If need most accurate → Llama 70B (but need 48GB+ VRAM)

### 2.3 Ollama Configuration

```yaml
# ollama-config.md
model: mistral:latest
parameters:
  temperature: 0.3  # Low = deterministic (good for Q&A)
  top_k: 40         # Diversity in token generation
  top_p: 0.9
  num_ctx: 4096     # Context window
  
performance:
  num_gpu_layers: 35  # GPU acceleration (auto-detect)
  num_threads: 8      # CPU threads if no GPU
  
service:
  port: 11434
  bind: "127.0.0.1"  # Local only (privacy)
```

---

## 3. Framework: LangChain

### 3.1 Why LangChain?

#### Alternatives Compared

| Framework | RAG Support | Agent Support | LLM Abstraction | Community |
|-----------|------------|---------------|-----------------|-----------|
| **LangChain (Recommended)** | ⭐⭐⭐ | ⭐⭐⭐ | ✅ Full | ⭐⭐⭐ |
| LlamaIndex | ⭐⭐⭐ | ⭐⭐ | ✅ Good | ⭐⭐ |
| DSPy | ⭐⭐ | ⭐⭐ | ⚠️ Limited | ⭐ |
| Haystack | ⭐⭐ | ⭐ | ✅ Good | ⭐⭐ |

#### Why LangChain Wins

✅ **Comprehensive Tool Ecosystem**
```python
from langchain.agents import create_react_agent
from langchain.tools import Tool, tool
from langchain.callbacks import ...
# Everything you need built-in
```

✅ **LLM Abstraction**
```python
# Works with any LLM provider
llm = ChatOllama(model="mistral")  # Local
llm = ChatOpenAI(...)                # Cloud
# Same code, swap one line!
```

✅ **Memory & Session Management**
```python
from langchain.memory import ConversationBufferMemory
# Handle multi-turn conversation easily
```

✅ **Debugging & Logging**
```python
from langchain.callbacks import StdOutCallbackHandler
# See every thought/action of agent
```

✅ **Active Community**
- 50k+ GitHub stars
- Weekly docs updates
- Tons of examples & tutorials

### 3.2 LangChain vs Alternatives in Practice

**LlamaIndex:**
```python
# Better if: You have structured data, time-series
# Worse if: Need fine-grained agent control
from llama_index import ...
```

**DSPy:**
```python
# Better if: You want formal verification of outputs
# Worse if: Need quick RAG setup
```

**For DỰ ÁN:**
→ LangChain: Best balance of features + simplicity

### 3.3 LangChain Components Used

```python
from langchain.agents import AgentType, create_react_agent
from langchain.callbacks import ...
from langchain.chains import RetrievalQA
from langchain.llms import Ollama
from langchain.embeddings import ...
from langchain.vectorstores import Chroma
from langchain.document_loaders import ...
from langchain.text_splitter import ...

# This combo covers: Agent + RAG + Retrieval + Embeddings
```

---

## 4. Vector Database: Chroma

### 4.1 Why Chroma?

#### Alternatives Compared

| VectorDB | Setup | Local | Performance | Scaling |
|----------|-------|-------|-------------|---------|
| **Chroma (Recommended)** | ⭐ Simple | ✅ Yes | Good | Medium |
| Weaviate | Medium | ✅ Yes | Great | Excellent |
| Pinecone | Easy (cloud) | ❌ No | Great | Excellent |
| Qdrant | Medium | ✅ Yes | Excellent | Great |
| FAISS (Meta) | Hard | ✅ Yes | Excellent | Large data |

#### Why Chroma Wins for PROTOTYPING + SMALL KB

✅ **Zero Setup**
```bash
# Chroma: pip install chromadb -> done
# Weaviate: docker-compose up (need Docker)
# Qdrant: docker pull, config...
```

✅ **File-Based Storage**
```bash
# Chroma saves to: ./chroma/
# Directory = database file
# Easy to backup, version control
```

✅ **Python-First Design**
```python
from langchain.vectorstores import Chroma
vectorstore = Chroma(embedding_function=...)
# Direct Python API, no network needed
```

✅ **Sufficient for KB Size**
- DỰ ÁN KB: ~50-100 documents (~1000 chunks)
- Chroma handles easily (<1s search)
- Scale to 1M+ vectors still fast

❌ **When to Switch to Qdrant/Weaviate:**
- KB > 100k documents
- Need prod infrastructure
- Need RBAC, monitoring

### 4.2 Chroma Setup

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/distiluse-base-multilingual-cased-v2",
    cache_folder="./models"
)

vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="./data/chroma",
    collection_name="regulations"
)

# That's it! Chroma handles everything.
# Data persisted to disk automatically.
```

### 4.3 When Chroma Not Sufficient

**If scalability needed later:**
```python
# Switch to Qdrant (code stays same due to LangChain abstraction!)
from langchain.vectorstores import Qdrant

vectorstore = Qdrant.from_documents(
    documents,
    embeddings,
    url="http://localhost:6333"
)

# Most other code unchanged!
```

---

## 5. Embeddings: Sentence-Transformers (Multilingual)

### 5.1 Why Sentence-Transformers?

#### Alternatives Compared

| Model | Languages | Local | Speed | Accuracy | Size |
|-------|-----------|-------|-------|----------|------|
| **distiluse-multilingual (Recommended)** | 50+ | ✅ Yes | ⚡ Fast | ✅ Good | 135MB |
| multilingual-e5-base | 100+ | ✅ Yes | Medium | Excellent | 438MB |
| OpenAI embeddings | All | ❌ API | N/A | Best | N/A |
| Word2Vec | Limited | ✅ Yes | Super fast | Poor | Small |

#### Why Sentence-Transformers

✅ **Multilingual Support** (Vietnamese + English)
```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer(
    "distiluse-base-multilingual-cased-v2"
)

# Same model for Vi & En queries
emb_vi = model.encode("Học phí")       # Vietnamese
emb_en = model.encode("Tuition fee")   # English
# cos_sim(emb_vi, emb_en) = 0.92 ✓ They're related!
```

✅ **Local Inference**
- No API calls needed
- Privacy preserved
- Work offline

✅ **Good Accuracy**
- 768-dimensional vectors
- Good semantic understanding
- Benchmark-tested on many datasets

✅ **Lightweight**
- 135MB download (distiluse)
- ~200MB in memory
- Runs on CPU (optional GPU acceleration)

❌ **OpenAI Embeddings Alternative:**
```python
# If need BEST embeddings (Ada-002)
from langchain.embeddings.openai import OpenAIEmbeddings

# Pros: Better accuracy
# Cons: Cloud API, privacy risk, $$ cost
# For student regul: Overkill
```

### 5.2 Embedding Dimension Selection

```
Dimension Trade-off:
━━━━━━━━━━━━━━━━━━━━━━━━
384-dim:     Fast, OK accuracy (e5-small)
512-dim:     Balance
768-dim:     Good accuracy (e5-base) ← RECOMMENDATION
1536-dim:    Best accuracy, more RAM (e5-large)

For KB ~100 docs:
→ 768-dim perfect balance
```

---

## 6. Frontend: Streamlit

### 6.1 Why Streamlit?

#### Alternatives Compared

| Framework | Setup | UI Quality | Interactivity | Dev Speed |
|-----------|-------|-----------|---------------|-----------|
| **Streamlit (Recommended)** | ⭐ Fastest | Good | Good | ⭐ Fastest |
| FastAPI + React | Medium | Excellent | Excellent | Medium |
| Gradio | Simple | OK | Good | ⭐ Fast |
| Flask | Medium | Poor | OK | Slow |
| Django | Hard | Excellent | Full | Slow |

#### Why Streamlit Wins for PROTOTYPE

✅ **Zero JavaScript**
```python
import streamlit as st

st.title("Student Regulation Chatbot")
st.text_input("Ask a question:")
st.button("Submit")
# Deploy in 5 minutes!
```

✅ **Hot-Reload Development**
- Save Python file → Browser auto-refreshes
- Instant feedback loop

✅ **Built-in Components**
```python
st.chat_message(role="user")
st.chat_input()
st.sidebar()
st.expander()
st.tabs()
# Chat UI ready-made!
```

✅ **Deployment**
```bash
streamlit run app.py
# Or: streamlit cloud (free deployment)
```

❌ **Limitations (for future):**
- Not ideal for highly interactive apps
- State management can be tricky
- Mobile not optimized

### 6.2 When to Upgrade

If product needs:
- Better mobile UX → React + FastAPI
- Complex interactions → Vue.js + Flask
- High performance → Next.js + Node

For now: Streamlit perfect ✓

---

## 7. Language Detection & Processing

### 7.1 Language Detection

```python
from langdetect import detect

detect("Học phí bao nhiêu?")          # → "vi"
detect("What is tuition?")             # → "en"
detect("Tuition fee là học phí")       # → "en" (likely, code-switch detected)
```

**Why `langdetect`:**
- Lightweight, fast
- Works for Vietnamese
- Simple API

---

## 8. Complete Tech Stack Summary

```
┌─────────────────────────────────────────────────────────┐
│              TECH STACK VISUALIZATION                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Layer               Technology         Why             │
│  ────────────────────────────────────────────────────   │
│                                                         │
│  Frontend            Streamlit          Fastest dev    │
│  │                                      interactive    │
│  ├─ Backend Logic    LangChain           Comprehensive │
│  │  Orchestration                       agent support  │
│  │                                                     │
│  ├─ Reasoning        LLM (Chat)                       │
│  │  └─ LLM Service   Ollama              Local privacy │
│  │      └─ Model     Mistral 7B          Good balance  │
│  │                   + Local             of speed/acc  │
│  │                                                     │
│  ├─ Retrieval Logic  LangChain           Integration   │
│  │  ├─ Embedding     Sentence-           Multilingual  │
│  │  │   Function     Transformers        Vietnamese +  │
│  │  │                distiluse-          English       │
│  │  │                multilingual                      │
│  │  │                                                   │
│  │  └─ Vector Store  Chroma              Zero setup    │
│  │                                       file-based    │
│  │                                       persistence   │
│  │                                                     │
│  ├─ Data Layer       SQLite              Simple logs   │
│  │  (Logging)                                          │
│  │                                                     │
│  └─ KB               PDF files           Plain text    │
│      (uploaded)      processed to        chunks        │
│                      text chunks                       │
│                                                         │
│  All LOCAL, PRIVATE, OPEN-SOURCE         ✓             │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 9. Installation Quick Reference

```bash
# Core dependencies
pip install langchain ollama streamlit chromadb

# Embeddings
pip install sentence-transformers

# Language detection
pip install langdetect

# PDF processing (for ingestion phase)
pip install pypdf2 pdf2image pdfplumber

# Optional: for better performance
pip install faiss-cpu  # Local similarity search optimization
# or
pip install hnswlib   # Another vector similarity option
```

---

## 10. Configuration Options

If requirements change later:

```yaml
# Easy swaps (LangChain abstraction handles it):

llm_options:
  local: "ollama/mistral"      # Current choice
  fast: "ollama/neural-chat"   # Faster
  better: "ollama/llama2:13b"  # More accurate
  # No code change needed! ✓

embedding_options:
  current: "distiluse-multilingual"
  smaller: "distiluse-multilingual" # Already small
  larger: "multilingual-e5-large"   # Better, but +RAM
  # LangChain handles it! ✓

vectordb_options:
  current: "chroma"            # File-based
  scale: "qdrant"              # For production
  # LangChain abstraction works! ✓
```

---

## Summary 📝

| Component | Choice | Primary Reason |
|-----------|--------|---|
| **LLM Service** | Ollama | Easiest setup, local |
| **LLM Model** | Mistral 7B | Speed-accuracy balance |
| **Framework** | LangChain | Most comprehensive |
| **Vector DB** | Chroma | Zero-setup, local |
| **Embeddings** | multilingual ST | Vietnamese support |
| **Frontend** | Streamlit | Fastest to build |
| **Lang Detection** | langdetect | Simple, fast |

---

## Key Takeaways 🎯

1. **Each choice optimized for: local + private + simple setup**
2. **All components have abstraction layers** → swappable later
3. **Total stack <500MB**, runs on most laptops
4. **Latency budget: ~2-5s/query** (acceptable for UX)
5. **All open-source & free**

---

## Related Files

🔗 **See Also:**
- `04-System-Architecture.md` - How components connect
- `06-Data-Preparation-Guide.md` - KB setup
- `11-Deployment-Guide.md` - Docker + production deployment
