# Hệ Thống Chatbot Hỏi Đáp Quy Chế Đào Tạo — AgenticRAG
## Tài liệu kỹ thuật chi tiết cho Đồ Án Tốt Nghiệp

> **Vai trò tác giả**: Senior AI Engineer  
> **Phạm vi**: Toàn bộ pipeline từ Data Ingestion đến Production Deployment  
> **Phiên bản hệ thống**: AgenticRAG v4 (Hybrid Intent + Multi-hop + Confidence Gate)

---

## Mục Lục

1. [Tổng Quan Hệ Thống](#1-tổng-quan-hệ-thống)
2. [Kiến Trúc Tổng Thể](#2-kiến-trúc-tổng-thể)
3. [Data Ingestion Pipeline](#3-data-ingestion-pipeline)
   - 3.1 [Thu Thập Và Chuẩn Bị Tài Liệu PDF](#31-thu-thập-và-chuẩn-bị-tài-liệu-pdf)
   - 3.2 [Trích Xuất Và Làm Sạch Văn Bản](#32-trích-xuất-và-làm-sạch-văn-bản)
   - 3.3 [Chunking — Phân Đoạn Văn Bản](#33-chunking--phân-đoạn-văn-bản)
4. [Embedding Pipeline](#4-embedding-pipeline)
   - 4.1 [Lựa Chọn Mô Hình Embedding](#41-lựa-chọn-mô-hình-embedding)
   - 4.2 [Vector Database — ChromaDB](#42-vector-database--chromadb)
5. [Kiến Trúc Agent — ReACT Pattern](#5-kiến-trúc-agent--react-pattern)
   - 5.1 [AgentState — Theo Dõi Trạng Thái](#51-agentstate--theo-dõi-trạng-thái)
   - 5.2 [Tổng Quan Vòng Lặp Suy Luận](#52-tổng-quan-vòng-lặp-suy-luận)
6. [Hybrid Intent Classification (v3)](#6-hybrid-intent-classification-v3)
   - 6.1 [Thiết Kế Intent Schema](#61-thiết-kế-intent-schema)
   - 6.2 [Luồng Phân Loại Ba Tầng](#62-luồng-phân-loại-ba-tầng)
   - 6.3 [Clarification Flow](#63-clarification-flow)
7. [Retrieval Pipeline — Multi-hop](#7-retrieval-pipeline--multi-hop)
   - 7.1 [Semantic Search Với ChromaDB](#71-semantic-search-với-chromadb)
   - 7.2 [Avg-Similarity Check (v4)](#72-avg-similarity-check-v4)
   - 7.3 [LLM Evaluate — Đánh Giá Ngữ Nghĩa](#73-llm-evaluate--đánh-giá-ngữ-nghĩa)
   - 7.4 [Query Rewrite — Viết Lại Câu Hỏi](#74-query-rewrite--viết-lại-câu-hỏi)
8. [Answer Generation — Tổng Hợp Câu Trả Lời](#8-answer-generation--tổng-hợp-câu-trả-lời)
9. [Confidence Scoring & Gating (v4)](#9-confidence-scoring--gating-v4)
10. [Conversation Memory — Bộ Nhớ Hội Thoại](#10-conversation-memory--bộ-nhớ-hội-thoại)
11. [LLM Factory — Hỗ Trợ Đa Provider](#11-llm-factory--hỗ-trợ-đa-provider)
12. [Frontend — Giao Diện Streamlit](#12-frontend--giao-diện-streamlit)
13. [Cấu Hình Hệ Thống (config.yaml)](#13-cấu-hình-hệ-thống-configyaml)
14. [Triển Khai — Deployment](#14-triển-khai--deployment)
15. [Luồng Tích Hợp Toàn Bộ Hệ Thống](#15-luồng-tích-hợp-toàn-bộ-hệ-thống)

---

## 1. Tổng Quan Hệ Thống

### 1.1 Bài Toán

Sinh viên Đại học Bách khoa Hà Nội thường xuyên cần tra cứu quy chế đào tạo, chính sách học bổng, yêu cầu ngoại ngữ và học phí. Tuy nhiên, các tài liệu này phân tán trong nhiều văn bản PDF, mỗi văn bản có thể lên đến hàng chục trang với ngôn ngữ pháp lý phức tạp.

Hệ thống chatbot được xây dựng nhằm:
- Trả lời câu hỏi tự nhiên bằng tiếng Việt về quy chế đào tạo.
- Trích dẫn nguồn gốc cụ thể (số Điều, Chương, tên văn bản).
- Hoạt động hoàn toàn cục bộ (on-premise), không gửi dữ liệu ra ngoài khi dùng Ollama.
- Tự động làm rõ câu hỏi khi thiếu thông tin cần thiết.

### 1.2 Phương Pháp — AgenticRAG

Thay vì RAG truyền thống (truy xuất một lần → sinh câu trả lời), hệ thống sử dụng **AgenticRAG** với pattern **ReACT (Reasoning + Acting)**:

| Đặc điểm | RAG Truyền Thống | AgenticRAG (Hệ thống này) |
|---|---|---|
| Số lần retrieval | 1 lần cố định | 1–2 hops, adaptive |
| Đánh giá kết quả | Không | LLM tự đánh giá relevance |
| Xử lý câu hỏi mơ hồ | Bỏ qua | Clarification flow |
| Kiểm soát chất lượng | Không có | Confidence Gate 3 mức |
| Bộ nhớ hội thoại | Không | Sliding Window Memory |
| Phân loại câu hỏi | Không | Hybrid Intent Classification |

### 1.3 Phạm Vi Tài Liệu

Hệ thống xử lý 9 văn bản PDF chính thức của ĐHBK Hà Nội:

| Tên File | Loại Tài Liệu | Hiệu Lực |
|---|---|---|
| `Quy_che_25.pdf` | Quy chế đào tạo | 2025-05-28 |
| `Quy_che_CTSV_ĐHBK_HN_2025310_final.pdf` | Quy chế công tác sinh viên | 2025-03-10 |
| `Hoc_bong_TDN_2023.pdf` | QĐ Học bổng Trần Đại Nghĩa | 2023 |
| `Hoc_bong_KKHT_2023.pdf` | QĐ Học bổng KKHT | 2023 |
| `QD_NN_K65.pdf` | Quyết định ngoại ngữ K65+ | 2020 |
| `QD_NN_K68.pdf` | Quyết định ngoại ngữ K68+ | 2024 |
| `QD_NN_K70.pdf` | Quyết định ngoại ngữ K70+ | 2025 |
| `HD_hoc_chuyen_tiep_ky_su_180TC.pdf` | Hướng dẫn chuyển tiếp kỹ sư | 2025-05-28 |
| `QD_chuyen_doi_hoc_phan_tuong_duong.pdf` | QĐ Chuyển đổi học phần tương đương | 2021 |

---

## 2. Kiến Trúc Tổng Thể

### 2.1 Sơ Đồ Kiến Trúc Tổng Thể (Tích Hợp Đầy Đủ)

> **Ghi chú**: Hybrid Intent Classification (v3) là **Bước 0** của Online Phase — không phải
> một module độc lập. Nó nằm bên trong `StudentRegulationAgent`, chạy trước Retrieval, và
> tương tác hai chiều với Conversation Memory. Sơ đồ dưới biểu diễn đầy đủ vị trí này.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║                            OFFLINE PHASE                                    ║
║                    (Chạy một lần duy nhất — Build Time)                     ║
║                                                                              ║
║  ┌──────────────┐   ┌────────────────────┐   ┌───────────────────────────┐  ║
║  │  PDF Files   │   │   PDFProcessor     │   │      TextChunker          │  ║
║  │  (9 tài liệu)│──►│  pdfplumber        │──►│  MarkdownHeaderSplitter   │  ║
║  │              │   │  extract_text()    │   │  RecursiveCharSplitter    │  ║
║  │  Quy_che_25  │   │  extract_tables()  │   │  chunk_size=1000          │  ║
║  │  QD_NN_K68   │   │  regex cleanup     │   │  overlap=200              │  ║
║  │  Hoc_bong_*  │   │  (50+ patterns)    │   │  + metadata gắn vào chunk │  ║
║  │  ...         │   │  → Markdown format │   │    (source, chapter, ...)  │  ║
║  └──────────────┘   └────────────────────┘   └─────────────┬─────────────┘  ║
║                                                             │                ║
║                                              ┌─────────────▼─────────────┐  ║
║                                              │   EmbeddingModelManager   │  ║
║                                              │   BAAI/bge-m3             │  ║
║                                              │   → 1024-dim dense vector │  ║
║                                              └─────────────┬─────────────┘  ║
║                                                             │                ║
║                                              ┌─────────────▼─────────────┐  ║
║                                              │  VectorDatabaseManager    │  ║
║                                              │  ChromaDB (Persistent)    │  ║
║                                              │  collection: student_regs │  ║
║                                              └───────────────────────────┘  ║
╚══════════════════════════════════════════════════════════════════════════════╝
                                                       ▲ search_similar()
                                                       │ (at runtime)
╔══════════════════════════════════════════════════════╪═════════════════════╗
║                          ONLINE PHASE                │                     ║
║                  (Runtime — Mỗi câu hỏi người dùng)  │                     ║
║                                                      │                     ║
║  ┌──────────────────────────────────────────────┐    │                     ║
║  │             Streamlit UI (app.py)            │    │                     ║
║  │  st.chat_input() ─────────────────────────► question                   ║
║  │  session_id = uuid4()                        │    │                     ║
║  └────────────────────┬─────────────────────────┘    │                     ║
║                       │ question + session_id         │                     ║
║                       ▼                               │                     ║
║  ╔════════════════════════════════════════════════╗   │                     ║
║  ║       StudentRegulationAgent                   ║   │                     ║
║  ║        answer_question()                       ║   │                     ║
║  ║                                                ║   │                     ║
║  ║  ┌─────────────────────────────────────────┐  ║   │                     ║
║  ║  │  ① READ Conversation Memory            │  ║   │                     ║
║  ║  │   - get_context(session_id)            │  ║   │                     ║
║  ║  │     → plain text lịch sử hội thoại     │  ║   │                     ║
║  ║  │   - get_entities_from_memory()         │  ║   │                     ║
║  ║  │     → entity từ các turn trước         │  ║   │                     ║
║  ║  │   - get_last_clarification_intent()    │  ║   │                     ║
║  ║  │     → intent nếu turn trước cần rõ    │  ║   │                     ║
║  ║  └───────────────────┬─────────────────────┘  ║   │                     ║
║  ║                      │                         ║   │                     ║
║  ║  ┌───────────────────▼─────────────────────┐  ║   │                     ║
║  ║  │   BƯỚC 0: HYBRID INTENT CLASSIFICATION  │  ║   │                     ║
║  ║  │   (IntentClassifier.classify())         │  ║   │                     ║
║  ║  │                                         │  ║   │                     ║
║  ║  │   Tầng 1 — LLM Extraction:             │  ║   │                     ║
║  ║  │   question + memory_context ──► LLM    │  ║   │                     ║
║  ║  │   → {intent, entities, confidence}     │  ║   │                     ║
║  ║  │                                         │  ║   │                     ║
║  ║  │   Tầng 2 — Entity Merge:               │  ║   │                     ║
║  ║  │   LLM entities ⊕ memory_entities       │  ║   │                     ║
║  ║  │   → merged_entities (LLM ghi đè memory)│  ║   │                     ║
║  ║  │                                         │  ║   │                     ║
║  ║  │   Tầng 3 — YAML Validation:            │  ║   │                     ║
║  ║  │   intent_config[intent].required_fields │  ║   │                     ║
║  ║  │   → kiểm tra merged_entities đủ chưa  │  ║   │                     ║
║  ║  └───────────────────┬─────────────────────┘  ║   │                     ║
║  ║                      │                         ║   │                     ║
║  ║          needs_clarification?                  ║   │                     ║
║  ║                ┌─────┴──────┐                  ║   │                     ║
║  ║               YES           NO                 ║   │                     ║
║  ║                │             │                 ║   │                     ║
║  ║                ▼             │                 ║   │                     ║
║  ║  ┌─────────────────────┐    │                 ║   │                     ║
║  ║  │ ② WRITE Memory     │    │                 ║   │                     ║
║  ║  │  needs_clarif=True  │    │                 ║   │                     ║
║  ║  │  intent saved       │    │                 ║   │                     ║
║  ║  └──────────┬──────────┘    │                 ║   │                     ║
║  ║             │               ▼                 ║   │                     ║
║  ║             │   ┌───────────────────────────┐ ║   │                     ║
║  ║             │   │ BƯỚC 1–2: MULTI-HOP       │ ║   │                     ║
║  ║             │   │ RETRIEVAL (max 2 hops)    │ ║   │                     ║
║  ║             │   │                           │ ║   │                     ║
║  ║             │   │  ┌── Hop N ─────────────┐ │ ║   │                     ║
║  ║             │   │  │ search_similar()      │ ║───►│                     ║
║  ║             │   │  │ top_k=3, thr=0.35     │ │ ║   │                     ║
║  ║             │   │  │  ↓ len<2? → fallback  │ │ ║   │                     ║
║  ║             │   │  │  ↓ avg_sim >= 0.45?   │ │ ║   │                     ║
║  ║             │   │  │    YES → break        │ │ ║   │                     ║
║  ║             │   │  │    NO  → LLM Evaluate │ │ ║   │                     ║
║  ║             │   │  │         relevant?      │ │ ║   │                     ║
║  ║             │   │  │         YES → break    │ │ ║   │                     ║
║  ║             │   │  │         NO  → Rewrite  │ │ ║   │                     ║
║  ║             │   │  │              → next hop│ │ ║   │                     ║
║  ║             │   │  └────────────────────────┘ │ ║   │                     ║
║  ║             │   └─────────────┬─────────────── ┘ ║   │                     ║
║  ║             │                 │ all_results        ║   │                     ║
║  ║             │                 ▼                   ║   │                     ║
║  ║             │   ┌───────────────────────────┐     ║   │                     ║
║  ║             │   │ BƯỚC 3: ANSWER GENERATION │     ║   │                     ║
║  ║             │   │ _build_context(results)   │     ║   │                     ║
║  ║             │   │ _generate_answer() → LLM  │     ║   │                     ║
║  ║             │   │ _calculate_confidence()   │     ║   │                     ║
║  ║             │   └─────────────┬─────────────┘     ║   │                     ║
║  ║             │                 │ (answer, confidence)║   │                     ║
║  ║             │                 ▼                   ║   │                     ║
║  ║             │   ┌───────────────────────────┐     ║   │                     ║
║  ║             │   │ BƯỚC 4: CONFIDENCE GATE   │     ║   │                     ║
║  ║             │   │ < 35%  → reject (no info) │     ║   │                     ║
║  ║             │   │ 35–65% → answer + warning │     ║   │                     ║
║  ║             │   │ ≥ 65%  → clean answer     │     ║   │                     ║
║  ║             │   └─────────────┬─────────────┘     ║   │                     ║
║  ║             │                 │                   ║   │                     ║
║  ║             │   ┌─────────────▼─────────────┐     ║   │                     ║
║  ║             │   │ ② WRITE Memory            │     ║   │                     ║
║  ║             │   │  question, answer[:500]    │     ║   │                     ║
║  ║             │   │  entities, intent          │     ║   │                     ║
║  ║             │   │  needs_clarification=False │     ║   │                     ║
║  ║             │   └─────────────┬─────────────┘     ║   │                     ║
║  ║             │                 │                   ║   │                     ║
║  ║             └────────┬────────┘                   ║   │                     ║
║  ║                      │ result dict                ║   │                     ║
║  ╚══════════════════════╪════════════════════════════╝   │                     ║
║                         │                               │                     ║
║  ┌──────────────────────▼─────────────────────────────┐ │                     ║
║  │                  Streamlit UI                       │ │                     ║
║  │  st.markdown(answer)                                │ │                     ║
║  │  Confidence indicator (success / warning / error)   │ │                     ║
║  │  Expander: tài liệu nguồn (chunk + score + chapter) │ │                     ║
║  └─────────────────────────────────────────────────────┘ │                     ║
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 2.1.1 Giải Thích Vị Trí Của Hybrid Intent Classification

Intent Classification **không phải module độc lập** — nó là **cổng vào (gateway)** của Online Phase, nằm trước Retrieval Pipeline trong cùng vòng xử lý request:

| Bước | Component | Pha | Vai trò |
|---|---|---|---|
| ① READ | ConversationMemory | Online | Lấy ngữ cảnh + entity + intent cũ |
| **0** | **IntentClassifier** | **Online** | **Phân loại intent, kiểm tra entity, quyết định tiếp tục hay hỏi lại** |
| 1–2 | Retrieval (Multi-hop) | Online | Tìm kiếm tài liệu liên quan |
| 3 | Answer Generation | Online | LLM tổng hợp câu trả lời |
| 4 | Confidence Gate | Online | Quyết định reject/warn/accept |
| ② WRITE | ConversationMemory | Online | Lưu turn vào memory |

**Memory** là thành phần **xuyên suốt** (cross-cutting): được đọc ở đầu (feed vào Intent Classifier) và được ghi ở cuối mỗi turn — kể cả turn clarification lẫn turn trả lời bình thường.

### 2.2 Technology Stack

| Layer | Công nghệ | Phiên bản / Model |
|---|---|---|
| **Frontend** | Streamlit | 1.28+ |
| **Agent Framework** | LangChain | 0.x |
| **LLM — Local** | Ollama (Gemma, Mistral) | gemma-4-E4B, mistral |
| **LLM — Cloud** | Google Gemini | gemini-2.5-flash |
| **Embedding Model** | BAAI/bge-m3 (HuggingFace) | 1024 chiều |
| **Vector Database** | ChromaDB | 1.5.7+ |
| **PDF Processing** | pdfplumber | Latest |
| **Text Splitting** | LangChain Text Splitters | 0.x |
| **Containerization** | Docker + docker-compose | Latest |
| **Language** | Python | 3.10+ |

### 2.3 Cấu Trúc Thư Mục Dự Án

```
ĐATN/
├── app.py                          # Entry point — Streamlit UI
├── config.yaml                     # Trung tâm cấu hình toàn hệ thống
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── src/
│   ├── agent/
│   │   ├── orchestrator.py         # StudentRegulationAgent — logic chính
│   │   ├── state.py                # AgentState — tracking reasoning
│   │   ├── intent_classifier.py    # Hybrid Intent Classification
│   │   ├── memory_manager.py       # Sliding Window Memory
│   │   ├── tools.py                # LangChain Agent Tools
│   │   └── prompts.py              # Prompt templates
│   │
│   ├── embeddings/
│   │   ├── model.py                # EmbeddingModelManager
│   │   ├── processor.py            # PDFProcessor + TextChunker
│   │   ├── vector_db.py            # VectorDatabaseManager (Chroma)
│   │   └── example_pipeline.py     # DataPreparationPipeline
│   │
│   └── utils/
│       ├── config.py               # ConfigManager singleton
│       ├── logger.py               # UTF-8 logging
│       └── performance.py          # Monitoring
│
├── scripts/
│   ├── build_knowledge_base.py     # Script chạy offline pipeline
│   ├── reset_vector_db.py          # Xóa Chroma DB
│   └── test_performance.py         # Benchmark
│
├── knowledge_base/raw/             # PDF gốc (input)
├── data/
│   ├── raw_json/                   # JSON sau bước extract
│   ├── chunks/                     # Chunks JSON
│   └── chroma/                     # Vector DB persistent
├── pages/
│   └── performance_debug.py        # Streamlit debug page
└── docs/                           # Tài liệu
```

---

## 3. Data Ingestion Pipeline

Data Ingestion Pipeline là bước **offline**, chỉ cần chạy một lần (hoặc khi cập nhật tài liệu). Pipeline này chuyển đổi file PDF thô thành cơ sở dữ liệu vector có thể tìm kiếm theo ngữ nghĩa.

### Tổng Quan Pipeline

```
[PDF Files]
     │
     ▼  BƯỚC 1
[PDFProcessor]
 - pdfplumber.open()
 - extract_text() + extract_tables()
 - Regex cleanup (50+ patterns)
 - Format Markdown headers
     │
     ▼  BƯỚC 2
[JSON Intermediate]
 - content: full markdown text
 - metadata: doc_type, source_file, effective_date
     │
     ▼  BƯỚC 3
[TextChunker]
 - MarkdownHeaderTextSplitter (#, ##)
 - RecursiveCharacterTextSplitter (1000 chars, 200 overlap)
 - Bảng Markdown giữ nguyên (không tách)
 - Gắn metadata: chapter_title, article_title, is_table
     │
     ▼  BƯỚC 4
[EmbeddingModelManager]
 - BAAI/bge-m3 (HuggingFace)
 - batch_size=32
 - Output: 1024-dim dense vector
     │
     ▼  BƯỚC 5
[VectorDatabaseManager]
 - ChromaDB PersistentClient
 - Collection: "student_regulations"
 - Lưu: vector + page_content + metadata
```

### 3.1 Thu Thập Và Chuẩn Bị Tài Liệu PDF

Các tài liệu PDF được đặt trong thư mục `knowledge_base/raw/`. Mỗi file PDF được ánh xạ với metadata cụ thể trong `config.yaml`:

```yaml
# config.yaml — Phần pdf_processing.metadata_mapping
pdf_processing:
  metadata_mapping:
    "Quy_che_25.pdf":
      doc_type: "Quy chế đào tạo"
      effective_date: "2025-05-28"
      applicable_students: "ALL"
      status: "active"
    "QD_NN_K68.pdf":
      doc_type: "Quyết định ngoại ngữ K68"
      effective_date: "2024"
      applicable_students: ">=K68"
      status: "active"
    # ... (9 tài liệu tổng cộng)
```

Metadata này được gắn vào từng chunk sau khi phân đoạn, cho phép trích xuất nguồn gốc chính xác khi hiển thị kết quả.

### 3.2 Trích Xuất Và Làm Sạch Văn Bản

**Class `PDFProcessor`** (`src/embeddings/processor.py`) thực hiện hai nhiệm vụ:

#### a) Trích Xuất Text Và Bảng

```python
# Mở file PDF bằng pdfplumber
with pdfplumber.open(pdf_path) as pdf:
    for page in pdf.pages:
        # Trích xuất text thuần
        text = page.extract_text() or ""
        
        # Trích xuất bảng → chuyển sang Markdown
        tables = page.extract_tables()
        for table in tables:
            df = pd.DataFrame(table).dropna(how='all')
            table_md = df.to_markdown(index=False)
        
        # Ghép text + bảng
        page_content = cleaned_text + "\n\n[Bảng Biểu]:\n" + table_md
```

**Lý do chọn pdfplumber**: Thư viện này xử lý tốt cả text thông thường lẫn bảng biểu trong văn bản pháp lý Việt Nam, đặc biệt với các bảng có định dạng phức tạp.

#### b) Làm Sạch Văn Bản — Regex Cleanup

Văn bản PDF chứa nhiều boilerplate không có giá trị thông tin (số trang, tiêu đề lặp, chữ ký, nơi nhận). Hệ thống định nghĩa **50+ regex pattern** trong `config.yaml` để lọc bỏ chúng:

```yaml
# config.yaml — text_cleanup_patterns (trích đoạn đại diện)
text_cleanup_patterns:
  # Số trang đứng lẻ
  - "^\\d+\\s*$"
  
  # Header quốc gia/trường lặp lại
  - "BỘ GIÁO DỤC VÀ ĐÀO TẠO"
  - "ĐẠI HỌC BÁCH KHOA HÀ NỘI"
  - "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM"
  - "Độc lập\\s*[–-]\\s*Tự do\\s*[–-]\\s*Hạnh phúc"
  
  # Khối "Căn cứ" (pháp lý boilerplate)
  - "^Căn cứ"
  - "^việc Quy định"
  
  # Chữ ký, nơi nhận
  - "PGS\\.TS\\."
  - "^Nơi nhận:"
  - "^- Lưu:\\s*VT"
```

Sau khi xóa boilerplate, hệ thống **tái cấu trúc văn bản thành Markdown**:

```python
# Chuyển "CHƯƠNG I" thành "# CHƯƠNG I" (H1)
text = re.sub(r'(^|\n)(CHƯƠNG\s+[IVX0-9]+)', r'\1# \2', text)

# Chuyển "Điều 1." thành "## Điều 1." (H2)
text = re.sub(r'(^|\n)(Điều\s+\d+\.)', r'\1## \2', text)
```

**Ý nghĩa**: Cấu trúc Markdown này sau đó được `MarkdownHeaderTextSplitter` dùng để phân đoạn theo cấp độ Chương/Điều, đảm bảo mỗi chunk tương ứng với một đơn vị ý nghĩa trong văn bản pháp lý.

#### c) Lưu Trung Gian Dạng JSON

Sau khi làm sạch, mỗi tài liệu được lưu thành file JSON với cấu trúc:

```json
{
  "metadata": {
    "source_file": "Quy_che_25.pdf",
    "doc_type": "Quy chế đào tạo",
    "effective_date": "2025-05-28",
    "applicable_students": "ALL",
    "status": "active"
  },
  "content": "# CHƯƠNG I\n## Điều 1. Phạm vi điều chỉnh\n..."
}
```

### 3.3 Chunking — Phân Đoạn Văn Bản

**Class `TextChunker`** (`src/embeddings/processor.py`) thực hiện phân đoạn **hai cấp độ**:

#### Cấp 1: Phân đoạn theo cấu trúc Markdown (Header Splitting)

```python
header_to_split_on = [
    ("#", "chapter_title"),   # CHƯƠNG → lưu vào metadata
    ("##", "article_title"),  # Điều   → lưu vào metadata
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=header_to_split_on
)

# Output: List[Document] với metadata chứa chapter_title, article_title
md_header_splits = markdown_splitter.split_text(content)
```

#### Cấp 2: Phân đoạn kích thước cố định (Size-based Splitting)

Mỗi phần tử từ Cấp 1 tiếp tục được phân đoạn nhỏ hơn, **nhưng giữ nguyên bảng Markdown**:

```python
def split_text_keeping_tables(text, chunk_size=1000, chunk_overlap=200):
    # Phát hiện bảng Markdown bằng regex
    table_pattern = r'(?:\|.*\|\n\|[-:| ]+\|\n(?:\|.*\|\n?)*)'
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    
    # Tách phần text trước/sau bảng, giữ nguyên bảng
    for match in tables:
        pre_table_text = text[last_end:start]
        final_chunks.extend(text_splitter.split_text(pre_table_text))
        final_chunks.append(table_text)  # Bảng giữ nguyên, không split
```

**Tham số chunking** (config.yaml):
```yaml
chunking:
  chunk_size: 1000      # ~250 từ tiếng Việt
  chunk_overlap: 200    # 20% overlap để không mất ngữ cảnh
```

#### Metadata Gắn Vào Mỗi Chunk

```python
combined_metadata = {
    # Từ file JSON gốc (metadata cấp tài liệu)
    "source_file": "Quy_che_25.pdf",
    "doc_type": "Quy chế đào tạo",
    "effective_date": "2025-05-28",
    
    # Từ MarkdownHeaderTextSplitter (metadata cấp cấu trúc)
    "chapter_title": "CHƯƠNG III — HỌC PHÍ VÀ HỌC BỔNG",
    "article_title": "Điều 15. Mức học phí",
    
    # Flag phân biệt loại chunk
    "is_table": True/False
}
```

**Metadata này là chìa khóa** để hệ thống trích dẫn nguồn chính xác trong câu trả lời cuối cùng.

---

## 4. Embedding Pipeline

### 4.1 Lựa Chọn Mô Hình Embedding

Hệ thống sử dụng **BAAI/bge-m3** — mô hình embedding đa ngôn ngữ của Viện AI Bắc Kinh, được tối ưu đặc biệt cho tiếng Á Đông (bao gồm tiếng Việt).

| Thuộc tính | BAAI/bge-m3| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 |
|---|---|---|
| Vector dimension | 1024 | 384 |
| Ngôn ngữ | 100+ (bao gồm tiếng Việt) | 50+ |
| Chất lượng tiếng Việt | Xuất sắc | Khá |
| Tốc độ | Trung bình | Nhanh |
| Kích thước model | ~570MB | ~120MB |

**`EmbeddingModelManager`** (`src/embeddings/model.py`) khởi tạo model với pattern **lazy initialization**:

```python
class EmbeddingModelManager:
    def __init__(self, config_path="./config.yaml"):
        config = yaml.safe_load(...)
        self.embedding_config = config["embedding"]
        self._initialize_model()
    
    def _initialize_model(self):
        model_name = self.embedding_config.get("model_name", "BAAI/bge-m3")
        batch_size = self.embedding_config.get("batch_size", 32)
        
        self.model = HuggingFaceEmbeddings(
            model_name=model_name,
            encode_kwargs={"batch_size": batch_size}
        )
    
    def get_model(self) -> HuggingFaceEmbeddings:
        return self.model
```

**Tham số cấu hình** (`config.yaml`):
```yaml
embedding:
  model_name: "BAAI/bge-m3"
  batch_size: 32       # Xử lý 32 chunks cùng lúc khi embed
  dimension: 1024      # Chiều vector output
```

### 4.2 Vector Database — ChromaDB

**`VectorDatabaseManager`** (`src/embeddings/vector_db.py`) bọc ChromaDB với giao diện thống nhất.

#### Khởi Tạo

```python
class VectorDatabaseManager:
    def __init__(self, embeddings, persist_directory=None, 
                 collection_name=None, config_path="./config.yaml"):
        
        # Đọc config
        self.persist_directory = Path(
            persist_directory or 
            config["vectordb"]["persist_directory"]   # "./data/chroma"
        )
        self.collection_name = (
            collection_name or 
            config["vectordb"]["collection_name"]     # "student_regulations"
        )
        
        # Khởi tạo ChromaDB persistent client
        self.client = chromadb.PersistentClient(
            path=str(self.persist_directory)
        )
        
        # Tạo hoặc load collection
        self.vectorstore = Chroma(
            embedding_function=embeddings,
            collection_name=self.collection_name,
            persist_directory=str(self.persist_directory),
            client=self.client
        )
```

#### Semantic Search — Chuyển Đổi L2 Distance

ChromaDB trả về **L2 (Euclidean) distance** theo mặc định (nhỏ hơn = tốt hơn). Hệ thống chuyển đổi về **similarity score [0,1]** (lớn hơn = tốt hơn) để trực quan hơn:

```python
def search_similar(self, query, k=None, score_threshold=None):
    # Lấy L2 distance từ Chroma
    raw_results = self.vectorstore.similarity_search_with_score(query, k=k)
    
    # Chuyển L2 distance → similarity: sim = 1 / (1 + distance)
    # distance = 0.0 → sim = 1.00 (perfect match)
    # distance = 0.5 → sim = 0.67
    # distance = 1.0 → sim = 0.50
    # distance = 2.0 → sim = 0.33
    results = []
    for doc, distance in raw_results:
        similarity = round(1.0 / (1.0 + distance), 4)
        results.append((doc, similarity))
    
    # Lọc theo threshold (mặc định: 0.35)
    results = [(doc, score) for doc, score in results 
               if score >= score_threshold]
    
    # Sắp xếp giảm dần (tốt nhất trước)
    results.sort(key=lambda x: x[1], reverse=True)
    return results
```

**Tham số retrieval** (`config.yaml`):
```yaml
retrieval:
  top_k: 3                    # Lấy tối đa 3 documents
  similarity_threshold: 0.35  # Ngưỡng tối thiểu (lọc kết quả kém)
  semantic_weight: 0.6        # Trọng số tìm kiếm ngữ nghĩa
  keyword_weight: 0.4         # Trọng số tìm kiếm từ khóa
```

---

## 5. Kiến Trúc Agent — ReACT Pattern

**`StudentRegulationAgent`** (`src/agent/orchestrator.py`) là trung tâm điều phối toàn bộ hệ thống, hiện thực hóa pattern **ReACT (Reasoning + Acting)**.

### 5.1 AgentState — Theo Dõi Trạng Thái

**`AgentState`** (`src/agent/state.py`) là dataclass ghi lại toàn bộ hành trình suy luận của agent:

```python
@dataclass
class AgentState:
    query: str              # Câu hỏi gốc
    iterations: int = 0     # Số bước đã thực hiện
    max_iterations: int = 5 # Giới hạn
    
    thoughts: List[str]     # Suy nghĩ tại mỗi bước
    actions: List[str]      # Hành động: Retrieve/Evaluate/QueryRewrite/GenerateAnswer
    observations: List[str] # Kết quả quan sát từ mỗi hành động
    
    confidence: float = 0.0 # Độ tin cậy cuối cùng
    answer: Optional[str]   # Câu trả lời cuối
    sources: List[str]      # Danh sách tài liệu nguồn
    success: bool = False
```

Mỗi bước suy luận được ghi lại qua `add_iteration()`:

```python
state.add_iteration(
    thought="Tìm kiếm lần 1 với query gốc",
    action="Retrieve",
    action_input="GPA bao nhiêu thì bị cảnh cáo học vụ?",
    observation="Tìm được 3 đoạn tài liệu"
)
```

State này phục vụ hai mục đích:
1. **Điều khiển luồng**: `should_continue()`, `is_max_iterations_reached()`
2. **Minh bạch với người dùng**: UI hiển thị các bước suy luận

### 5.2 Tổng Quan Vòng Lặp Suy Luận

```
answer_question(question, session_id)
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  BƯỚC 0: HYBRID INTENT CLASSIFICATION               │
│                                                     │
│  memory_context ─────┐                              │
│  memory_entities ────┤──► IntentClassifier.classify()
│  previous_intent ────┘         │                    │
│                         ┌──────┴──────┐             │
│                  needs_clarification?  │             │
│                     │         │       │             │
│                    YES        NO      │             │
│                     │         │       │             │
│               Return        Continue  │             │
│               clarification  to RAG   │             │
│               question               │             │
└─────────────────────────────────────────────────────┘
        │
        ▼ (intent OK)
┌─────────────────────────────────────────────────────┐
│  VÒNG LẶP: for hop in range(MAX_RETRIEVAL_HOPS=2)  │
│                                                     │
│  current_query ──► _retrieve(query, top_k, thresh)  │
│                         │                           │
│              len(results) < 2 ?                     │
│                 │       │                           │
│                YES       NO                         │
│                 │        │                          │
│           Fallback:    Continue                     │
│           top_k+2,     │                            │
│           thresh=0.25  │                            │
│                 └───────┤                           │
│                         ▼                           │
│              avg_sim = mean(top scores)             │
│                         │                           │
│              avg_sim >= 0.45 ?                      │
│                 │       │                           │
│                YES       NO                         │
│                 │        │                          │
│           Break loop  LLM Evaluate                  │
│           → Generate   (relevant?)                  │
│                         │                           │
│                  is_relevant?                       │
│                    │    │                           │
│                   YES    NO                         │
│                    │     │                          │
│             Break loop  QueryRewrite               │
│             → Generate  (if hop < max-1)           │
│                          → new current_query       │
└─────────────────────────────────────────────────────┘
        │
        ▼ (all_results collected)
┌─────────────────────────────────────────────────────┐
│  GENERATE ANSWER                                    │
│  _build_context(all_results)                        │
│  _generate_answer(question, context)                │
│  _calculate_confidence(results, answer, iterations) │
└─────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  CONFIDENCE GATE                                    │
│  confidence < 0.35 → reject (no info found)         │
│  0.35 ≤ conf < 0.65 → answer + warning             │
│  confidence ≥ 0.65 → clean answer                  │
└─────────────────────────────────────────────────────┘
        │
        ▼
  Save to Memory + Return result
```

---

## 6. Hybrid Intent Classification (v3)

### 6.1 Thiết Kế Intent Schema

Hệ thống định nghĩa **5 loại intent** trong `config.yaml`, mỗi intent có thể yêu cầu entity cụ thể:

```yaml
intents:
  GENERAL_REGULATION:
    description: "Quy chế, quy định chung không phụ thuộc ngành/khóa cụ thể"
    requires_entities: false   # Không cần entity → pass thẳng vào RAG
    required_fields: []
    examples:
      - "GPA bao nhiêu thì bị cảnh cáo học vụ?"
      - "Điều kiện bảo lưu kết quả học tập?"

  LANGUAGE_REQUIREMENT:
    description: "Yêu cầu ngoại ngữ đầu vào, chuẩn đầu ra theo ngành và khóa"
    requires_entities: true    # BẮT BUỘC có entity
    required_fields:
      - nganh_hoc   # "CNTT", "Cơ điện tử", "Toán - Tin"
      - khoa_hoc    # "K65", "K68", "K70"
    clarification_template: |
      Để tra cứu yêu cầu ngoại ngữ chính xác, bạn vui lòng cho biết:
      - Ngành học của bạn là gì? (ví dụ: CNTT, Cơ điện tử, Toán - Tin...)
      - Bạn thuộc khóa nào? (ví dụ: K65, K68, K70...)

  TUITION_FEE:
    description: "Học phí, miễn giảm học phí, quy định đóng học phí"
    requires_entities: true
    required_fields: [nganh_hoc, khoa_hoc]
    clarification_template: "Để tra cứu học phí chính xác..."
```

**Thiết kế hợp lý**: `GENERAL_REGULATION`, `ACADEMIC_DISCIPLINE`, `SCHOLARSHIP` không cần entity vì câu trả lời áp dụng cho tất cả sinh viên. `LANGUAGE_REQUIREMENT` và `TUITION_FEE` bắt buộc có `nganh_hoc` và `khoa_hoc` vì quy định khác nhau theo từng ngành và khóa.

### 6.2 Luồng Phân Loại Ba Tầng

**`IntentClassifier`** (`src/agent/intent_classifier.py`) thực hiện phân loại theo 3 tầng:

#### Tầng 1: LLM Extraction

```python
_INTENT_EXTRACTION_PROMPT = """\
Bạn là bộ phân loại câu hỏi của hệ thống chatbot quy chế đào tạo ĐHBK Hà Nội.

## Danh sách Intent hợp lệ:
{intent_list}

## Lịch sử hội thoại gần đây:
{memory_context}

## Câu hỏi hiện tại:
"{question}"

## Nhiệm vụ:
1. Xác định intent phù hợp nhất
2. Bóc tách entity: nganh_hoc, khoa_hoc, gpa

Trả về JSON:
{"intent": "INTENT_NAME", "entities": {...}, "confidence": 0.0-1.0}
"""
```

LLM phân tích câu hỏi và **context từ memory** để bóc tách intent và entity. Ví dụ:

```
Câu hỏi: "Sinh viên Cơ điện tử K68 cần TOEIC bao nhiêu?"
→ LLM output: {
    "intent": "LANGUAGE_REQUIREMENT",
    "entities": {"nganh_hoc": "Cơ điện tử", "khoa_hoc": "K68"},
    "confidence": 0.95
  }
```

#### Tầng 2: Entity Merge Với Memory

```python
# Entity từ LLM (câu hỏi hiện tại) ghi đè entity từ memory (lịch sử)
merged_entities = {
    **memory_entities,    # Entity từ các turn trước
    **{k: v for k, v in llm_result["entities"].items() if v is not None}
}
```

**Ý nghĩa**: Người dùng có thể hỏi tiếp mà không cần lặp lại ngành/khóa đã cung cấp ở câu hỏi trước.

#### Tầng 3: YAML Business Logic Validation

```python
def _check_required_fields(self, intent_def, entities):
    if not intent_def.get("requires_entities", False):
        return False, []  # Không cần entity → pass luôn
    
    required = intent_def.get("required_fields", [])
    missing = [field for field in required 
               if not entities.get(field)]  # None hoặc empty
    
    return bool(missing), missing  # (needs_clarification, missing_fields)
```

#### Xử Lý Clarification Response (v3 mới)

Khi người dùng trả lời câu hỏi làm rõ (ví dụ: "Tôi học ngành CNTT K70"), hệ thống cần nhận biết đây là **response to clarification**, không phải câu hỏi mới:

```python
# Lấy intent từ turn trước nếu nó là clarification turn
previous_intent = memory.get_last_clarification_intent(session_id)

# Heuristic: câu ngắn + có từ khóa ngành/khóa → clarification response
is_clarification_response = (
    len(question.split()) <= 15 or
    ("là" in question.lower() and 
     any(kw in question.lower() for kw in ["ngành", "khóa", "k6", "k7"]))
)

if is_clarification_response:
    intent_name = previous_intent  # Reuse intent cũ
```

### 6.3 Clarification Flow

```
User: "Yêu cầu ngoại ngữ của tôi là gì?"
    │
    ▼
IntentClassifier.classify()
    │
    ├── LLM → intent = "LANGUAGE_REQUIREMENT"
    ├── Entities: {} (không có ngành/khóa)
    ├── Memory: {} (không có lịch sử)
    ├── missing_fields = ["nganh_hoc", "khoa_hoc"]
    └── needs_clarification = True
    │
    ▼
Agent returns:
{
  "answer": "Để tra cứu yêu cầu ngoại ngữ chính xác, bạn vui lòng cho biết:\n- Ngành học...\n- Bạn thuộc khóa...",
  "needs_clarification": True,
  "confidence": 0.0
}

Memory lưu turn này với needs_clarification=True, intent="LANGUAGE_REQUIREMENT"

    │
    ▼
User: "Ngành CNTT, khóa K70"
    │
    ▼
IntentClassifier.classify(
    question="Ngành CNTT, khóa K70",
    previous_intent="LANGUAGE_REQUIREMENT"  ← từ memory
)
    │
    ├── Detect: clarification response (ngắn + có từ khóa)
    ├── Reuse intent = "LANGUAGE_REQUIREMENT"
    ├── Entities: {"nganh_hoc": "CNTT", "khoa_hoc": "K70"}
    ├── missing_fields = []
    └── needs_clarification = False
    │
    ▼
Proceed to RAG với intent + entities đầy đủ
```

---

## 7. Retrieval Pipeline — Multi-hop

### 7.1 Semantic Search Với ChromaDB

Khi agent thực hiện retrieval, nó gọi `_retrieve()`:

```python
def _retrieve(self, query, k, threshold):
    return self.vector_db_manager.search_similar(
        query=query,
        k=k,              # top_k = 3 (từ config)
        score_threshold=threshold   # 0.35 mặc định
    )
```

Phương thức `search_similar` trong ChromaDB:
1. Embed câu hỏi thành vector 1024 chiều (BAAI/bge-m3)
2. Tìm k vectors gần nhất trong collection bằng L2 distance
3. Chuyển đổi `sim = 1/(1 + dist)`
4. Lọc `sim >= threshold`
5. Sắp xếp giảm dần

#### Fallback Threshold

Nếu kết quả trả về ít hơn 2 documents (quá ít để tổng hợp câu trả lời), hệ thống tự động mở rộng phạm vi:

```python
if len(results) < 2 and threshold > 0.25:
    # Giảm ngưỡng từ 0.35 → 0.25, tăng k từ 3 → 5
    results = self._retrieve(current_query, top_k + 2, 0.25)
```

### 7.2 Avg-Similarity Check (v4)

Đây là cải tiến quan trọng nhất trong v4 — thay vì luôn gọi LLM để đánh giá, hệ thống kiểm tra nhanh bằng ngưỡng similarity trung bình:

```python
# Tính avg similarity của top-k results
recent_scores = [score for _, score in results[:top_k]]
avg_sim = sum(recent_scores) / max(len(recent_scores), 1)

if avg_sim >= min_avg_similarity:  # Ngưỡng: 0.45 (từ config)
    # Documents đủ tốt → bỏ qua LLM Evaluate, tiến thẳng đến Generate
    break
else:
    # Similarity thấp → cần LLM kiểm tra kỹ hơn
    is_relevant, reason = self._evaluate_context(question, context)
```

**Lý do**: Gọi LLM mất ~1-3 giây. Nếu cosine similarity đã cao (≥ 0.45), việc gọi thêm LLM để xác nhận là lãng phí. Avg-similarity check chỉ tốn vài millisecond.

**Tham số** (`config.yaml`):
```yaml
agent:
  min_avg_similarity: 0.45  # avg sim ≥ 45% → docs tốt, skip evaluate
```

### 7.3 LLM Evaluate — Đánh Giá Ngữ Nghĩa

Khi avg similarity thấp, agent gọi LLM để đánh giá sâu hơn liệu documents có *liên quan* đến câu hỏi không:

```python
_EVALUATE_PROMPT = """\
Câu hỏi của sinh viên: "{question}"

Các đoạn tài liệu tìm được:
{context}

Nhiệm vụ: Đánh giá xem tài liệu có ĐỀ CẬP đến chủ đề câu hỏi hay không.
Lưu ý:
- KHÔNG cần trả lời hoàn chỉnh 100%, chỉ cần có liên quan là ĐỦ.
- Chỉ trả về relevant=false nếu hoàn toàn nói về chủ đề khác.

Trả về JSON: {"relevant": true/false, "reason": "Lý do ngắn gọn"}
"""
```

**Thiết kế quan trọng**: Câu hỏi là **"có liên quan không?"** thay vì **"có đủ thông tin không?"** — vì LLM thường kén chọn và sẽ luôn trả về `false` nếu hỏi về sự đầy đủ. Tiêu chí "liên quan" thực tế hơn và giảm false negative.

```python
def _evaluate_context(self, question, context):
    raw = _invoke_llm(self.llm, self._provider, prompt)
    # Parse JSON với regex
    match = re.search(r'\{.*?\}', raw, re.DOTALL)
    data = json.loads(match.group())
    is_relevant = bool(data.get("relevant", True))  # Default True (fallback an toàn)
    return is_relevant, data.get("reason", "")
```

### 7.4 Query Rewrite — Viết Lại Câu Hỏi

Khi documents không liên quan, agent yêu cầu LLM viết lại câu hỏi với thuật ngữ học thuật/pháp lý chính xác hơn:

```python
_REWRITE_PROMPT = """\
Câu hỏi gốc: "{question}"
Lý do tìm kiếm chưa đủ: "{reason}"

Viết lại câu hỏi dùng thuật ngữ pháp lý/học thuật chính xác hơn.
Chỉ trả về 1 câu duy nhất.

Ví dụ:
- "trượt 14 tín" → "cảnh cáo học tập tín chỉ nợ không đạt yêu cầu"
- "bị đuổi học vì học kém" → "xử lý học vụ buộc thôi học điểm TBCTL thấp"
"""
```

**Ví dụ thực tế**:

| Câu gốc (informal) | Câu viết lại (formal) |
|---|---|
| "trượt 14 tín" | "cảnh cáo học tập tín chỉ nợ không đạt yêu cầu" |
| "bị đuổi học vì học kém" | "xử lý học vụ buộc thôi học do điểm TBCTL thấp" |
| "học lại được không?" | "quy định đăng ký học lại học phần chưa đạt" |

Query rewrite chỉ xảy ra khi: `hop < MAX_RETRIEVAL_HOPS - 1` và kết quả không liên quan, tức là chỉ ở hop đầu tiên của vòng lặp 2-hop.

---

## 8. Answer Generation — Tổng Hợp Câu Trả Lời

### 8.1 Xây Dựng Context

```python
def _build_context(self, results):
    parts = []
    for i, (doc, score) in enumerate(results, 1):
        meta = doc.metadata
        source = meta.get("source_file") or "Không rõ"
        chapter = meta.get("chapter_title", "")
        article = meta.get("article_title", "")
        
        header = f"--- Đoạn {i} | Nguồn: {source} | Độ liên quan: {score:.1%} ---"
        if chapter:
            header += f"\nChương: {chapter}"
        if article:
            header += f"\nĐiều: {article}"
        
        parts.append(f"{header}\n{doc.page_content}")
    
    return "\n\n".join(parts)
```

Context được cấu trúc rõ ràng với **tiêu đề mỗi đoạn** chứa thông tin nguồn gốc và độ liên quan, giúp LLM dễ dàng trích dẫn chính xác.

### 8.2 Generation Prompt

```python
_ANSWER_PROMPT = """\
{system_prompt}   # REACT_SYSTEM_PROMPT — vai trò và nguyên tắc

=== TÀI LIỆU THAM KHẢO ===
{context}         # Các đoạn tài liệu với metadata

=== CÂU HỎI ===
{question}

=== YÊU CẦU ===
- Trả lời trực tiếp, rõ ràng, đúng trọng tâm
- Trích dẫn cụ thể số Điều, Chương, tên văn bản nếu có
- KHÔNG bịa đặt thông tin ngoài tài liệu
- Nếu thông tin không đủ, thừa nhận giới hạn
- Phát hiện ngôn ngữ câu hỏi, trả lời bằng ĐÚNG ngôn ngữ đó

=== CÂU TRẢ LỜI ===
"""
```

**System Prompt** định nghĩa vai trò của agent:
```python
REACT_SYSTEM_PROMPT = """Bạn là trợ lý AI chuyên về quy định và chính sách đào tạo 
tại Đại học Bách khoa Hà Nội (HUST/ĐHBK Hà Nội).

Tài liệu bạn có quyền truy cập:
- Quy chế đào tạo (Quy_che_25.pdf)
- Quy chế công tác sinh viên
- Học bổng Trần Đại Nghĩa, Học bổng KKHT
- Quyết định ngoại ngữ K65, K68, K70
- ...

Nguyên tắc:
1. Chỉ dùng thông tin từ tài liệu được cung cấp, KHÔNG bịa đặt
2. Trích dẫn: số Điều, Chương, tên văn bản
3. Thừa nhận giới hạn nếu không đủ thông tin
4. Trả lời bằng tiếng Việt, rõ ràng, có cấu trúc"""
```

---

## 9. Confidence Scoring & Gating (v4)

### 9.1 Tính Toán Confidence Score

Confidence score được tính từ **3 yếu tố độc lập**:

```python
def _calculate_confidence(self, results, answer, iterations):
    score = 0.0
    
    # ── Yếu tố 1: Số lượng documents (trọng số 30%) ──────────────────
    doc_count = len(results)
    score += min(doc_count / 5, 1.0) * 0.30
    # 1 doc → +0.06, 3 docs → +0.18, 5+ docs → +0.30
    
    # ── Yếu tố 2: Chất lượng câu trả lời (trọng số 40%) ─────────────
    answer_lower = answer.lower()
    has_numbers = any(c.isdigit() for c in answer)
    has_legal   = any(t in answer_lower for t in [
        "điều", "khoản", "chương", "tín chỉ", "gpa", "cpa",
        "%", "học kỳ", "năm học", "quyết định"
    ])
    is_negative = any(t in answer_lower for t in [
        "không biết", "không tìm thấy", "xin lỗi"
    ])
    
    if is_negative:       score += 0.0   # Câu trả lời từ chối
    elif has_numbers and has_legal: score += 0.40  # Có số liệu + điều khoản
    elif has_numbers or has_legal:  score += 0.25  # Có một trong hai
    elif len(answer) > 100:         score += 0.15  # Dài nhưng không cụ thể
    
    # ── Yếu tố 3: Hiệu quả suy luận (trọng số 30%) ───────────────────
    if iterations <= 2:   score += 0.30  # Tìm ngay từ hop đầu
    elif iterations <= 4: score += 0.20  # Cần một lần rewrite
    elif iterations <= 6: score += 0.10  # Nhiều hop
    
    return round(min(max(score, 0.0), 1.0), 2)
```

**Ví dụ**:
- Câu trả lời có số liệu + điều khoản + 3 documents + 2 iterations:
  `0.18 + 0.40 + 0.30 = 0.88` → High confidence ✅
- Câu trả lời dài nhưng không cụ thể + 1 document + 4 iterations:
  `0.06 + 0.15 + 0.20 = 0.41` → Medium confidence ⚠️

### 9.2 Confidence Gate — Ba Mức Quyết Định

```python
# Đọc threshold từ config.yaml
high_conf = agent_config.get("high_confidence_threshold", 0.65)  # ≥ 65%
low_conf  = agent_config.get("low_confidence_threshold", 0.35)   # < 35%

if confidence < low_conf:
    # ── MỨC THẤP: Từ chối ────────────────────────────────────────
    answer = (
        f"Xin lỗi, tôi không tìm thấy thông tin liên quan...\n"
        f"Bạn có thể:\n"
        f"• Thử hỏi lại với từ khóa khác\n"
        f"• Liên hệ Phòng Đào tạo ĐHBK Hà Nội\n"
        f"• Tra cứu trực tiếp: https://hust.edu.vn"
    )
    success = False

elif confidence < high_conf:
    # ── MỨC TRUNG BÌNH: Cảnh báo ────────────────────────────────
    answer = (
        raw_answer
        + f"\n\n---\n⚠️ *Lưu ý: Độ tin cậy ở mức trung bình ({confidence:.0%}). "
        + "Vui lòng kiểm tra lại với tài liệu gốc.*"
    )
    success = True

else:
    # ── MỨC CAO: Trả lời bình thường ────────────────────────────
    answer = raw_answer
    success = True
```

**Thiết kế này giải quyết vấn đề quan trọng**: Thay vì để LLM ảo giác (hallucinate) với câu trả lời tự tin nhưng sai, hệ thống chủ động từ chối khi không đủ bằng chứng.

---

## 10. Conversation Memory — Bộ Nhớ Hội Thoại

### 10.1 Sliding Window Strategy

**`ConversationMemory`** (`src/agent/memory_manager.py`) lưu trữ lịch sử hội thoại theo chiến lược cửa sổ trượt:

```python
class ConversationMemory:
    def __init__(self, window_size=5, max_context_chars=1500):
        # Storage: {session_id: List[ConversationTurn]}
        self._store: Dict[str, List[ConversationTurn]] = {}
        self.window_size = window_size          # Giữ 5 turns gần nhất
        self.max_context_chars = max_context_chars  # Giới hạn 1500 ký tự

@dataclass
class ConversationTurn:
    question: str
    answer: str
    entities: Dict[str, Any]      # Entity đã bóc tách được
    intent_name: str              # Intent được classify
    needs_clarification: bool     # Turn này có cần làm rõ không?
```

### 10.2 Entity Propagation Across Turns

Tính năng quan trọng nhất của memory: **tự động truyền entity từ turn trước** sang turn sau, giúp người dùng không phải lặp lại thông tin:

```python
def get_entities_from_memory(self, session_id):
    """
    Gộp entity từ toàn bộ window.
    Turn gần nhất ghi đè entity cũ hơn.
    
    Turn 1: {"nganh_hoc": "CNTT"}
    Turn 2: {"khoa_hoc": "K65"}
    → Output: {"nganh_hoc": "CNTT", "khoa_hoc": "K65"}
    """
    merged = {}
    for turn in self._store.get(session_id, []):  # cũ → mới
        for key, value in turn.entities.items():
            if value:
                merged[key] = value  # Mới ghi đè cũ
    return merged
```

**Kịch bản thực tế**:
```
Turn 1: "Ngành CNTT K68 cần học bổng gì?" 
        → entities: {nganh_hoc: "CNTT", khoa_hoc: "K68"}
Turn 2: "Còn yêu cầu ngoại ngữ thì sao?"
        → LLM extract: {} (không có entity mới)
        → memory_entities: {nganh_hoc: "CNTT", khoa_hoc: "K68"} ← từ Turn 1
        → merged: {nganh_hoc: "CNTT", khoa_hoc: "K68"}
        → No clarification needed → proceed to RAG
```

### 10.3 Context Injection Vào Prompt

```python
def get_context(self, session_id):
    """Inject context vào prompt với giới hạn ký tự."""
    turns = self._store.get(session_id, [])
    chars_per_turn = max(100, self.max_context_chars // len(turns))
    
    parts = []
    total_chars = 0
    for turn in turns:
        text = f"Người dùng: {turn.question[:chars_per_turn]}\nBot: {turn.answer[:chars_per_turn]}"
        if total_chars + len(text) > self.max_context_chars:
            break
        parts.append(text)
        total_chars += len(text)
    
    return "\n---\n".join(parts)
```

Context này được inject vào **Intent Extraction Prompt**, giúp LLM hiểu ngữ cảnh hội thoại.

### 10.4 Singleton Pattern

```python
_global_memory: Optional[ConversationMemory] = None

def get_memory(window_size=5, max_context_chars=1500) -> ConversationMemory:
    """Factory function — đảm bảo toàn app dùng chung một instance."""
    global _global_memory
    if _global_memory is None:
        _global_memory = ConversationMemory(window_size, max_context_chars)
    return _global_memory
```

Singleton đảm bảo tất cả components (orchestrator, intent classifier) dùng **cùng một vùng nhớ**, không bị phân mảnh state.

---

## 11. LLM Factory — Hỗ Trợ Đa Provider

Hệ thống hỗ trợ hai LLM provider thông qua **factory pattern**, cho phép chuyển đổi dễ dàng chỉ bằng thay đổi `config.yaml`:

```python
def _build_llm(llm_config):
    provider = llm_config.get("provider", "ollama").lower()
    
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        api_key = os.environ.get(llm_config["api_key_env"])  # GEMINI_API_KEY
        
        llm = ChatGoogleGenerativeAI(
            model=llm_config.get("model_name", "gemini-2.5-flash"),
            google_api_key=api_key,
            temperature=llm_config.get("temperature", 0.3),
            max_output_tokens=llm_config.get("max_tokens", 2048)
        )
    
    else:  # ollama (default)
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(
            model=llm_config.get("model_name", "mistral"),
            base_url=llm_config.get("base_url", "http://localhost:11434"),
            temperature=llm_config.get("temperature", 0.3),
            timeout=llm_config.get("timeout_seconds", 120)
        )
    
    return llm, provider
```

### Unified Invocation

```python
def _invoke_llm(llm, provider, prompt):
    """Gọi LLM, trả về plain text — tương thích cả hai provider."""
    if provider == "gemini":
        # Xử lý asyncio issue khi chạy trong Streamlit thread
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    
    response = llm.invoke(prompt)
    
    # Gemini → AIMessage (có .content), Ollama → str
    if hasattr(response, "content"):
        return response.content.strip()
    return str(response).strip()
```

### So Sánh Hai Provider

| Tiêu chí | Ollama (Local) | Google Gemini (Cloud) |
|---|---|---|
| Quyền riêng tư | Hoàn toàn cục bộ | Gửi data lên cloud |
| Chi phí | Miễn phí | Theo API usage |
| Tốc độ | Phụ thuộc GPU/CPU | Nhanh (server-side) |
| Chất lượng | Gemma/Mistral | Gemini 2.5 Flash |
| Khi nào dùng | Môi trường nhạy cảm | Dev/Test nhanh |

**Cấu hình** (`config.yaml`):
```yaml
llm:
  provider: "gemini"              # Hoặc "ollama"
  model_name: "gemini-2.5-flash"  # Ollama: "gemma_nothink", "mistral"
  temperature: 0.3                # Thấp → ít sáng tạo, nhiều chính xác
  max_tokens: 2048
  api_key_env: "GEMINI_API_KEY"   # Tên biến env chứa API key
```

---

## 12. Frontend — Giao Diện Streamlit

### 12.1 Session Management

`app.py` sử dụng **`st.cache_resource`** để cache agent (khởi tạo một lần duy nhất), và UUID cho mỗi session người dùng:

```python
@st.cache_resource
def load_agent():
    return StudentRegulationAgent(config_path="./config.yaml")

# Mỗi browser tab/user có một session_id riêng
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
```

### 12.2 Chat Interface Flow

```python
# Hiển thị lịch sử chat
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input người dùng
if prompt := st.chat_input("Hỏi về quy chế đào tạo..."):
    # Hiển thị ngay tin nhắn người dùng
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Xử lý và hiển thị câu trả lời
    with st.chat_message("assistant"):
        with st.status("Đang xử lý...") as status:
            result = agent.answer_question(
                question=prompt,
                session_id=st.session_state.session_id,
                status_callback=lambda msg: status.update(label=msg)
            )
        
        # Hiển thị câu trả lời
        st.markdown(result["answer"])
        
        # Hiển thị confidence indicator
        conf = result["confidence"]
        if conf >= 0.65:
            st.success(f"Độ tin cậy: {conf:.0%}")
        elif conf >= 0.35:
            st.warning(f"Độ tin cậy: {conf:.0%}")
        else:
            st.error(f"Độ tin cậy thấp: {conf:.0%}")
        
        # Hiển thị tài liệu nguồn (expander)
        if result.get("retrieved_chunks"):
            with st.expander("Xem tài liệu nguồn"):
                for chunk in result["retrieved_chunks"]:
                    st.caption(f"{chunk['source']} | {chunk['score']:.0%}")
                    st.text(chunk["content"][:300] + "...")
```

### 12.3 Status Callback — Real-time UI Updates

Agent nhận một `status_callback` function để cập nhật UI theo thời gian thực:

```python
# Trong orchestrator.py
def notify(msg: str):
    logger.info(msg)
    if status_callback:
        status_callback(msg)

notify("🔎 Đang phân loại câu hỏi...")     # Bước 0
notify("🔍 [1/2] Đang tìm kiếm...")        # Retrieval hop 1
notify("🧐 Đang đánh giá tài liệu...")     # LLM Evaluate
notify("✏️ Đang viết lại câu hỏi...")      # Query Rewrite
notify("🧠 Đang tổng hợp câu trả lời...") # Generation
```

---

## 13. Cấu Hình Hệ Thống (config.yaml)

`config.yaml` là **single source of truth** cho toàn bộ hệ thống. Mọi tham số quan trọng đều có thể điều chỉnh mà không cần sửa code:

```yaml
# ═══════════════════════════════════════════
# AGENT BEHAVIOR — Điều chỉnh reasoning logic
# ═══════════════════════════════════════════
agent:
  type: "react"
  max_iterations: 5
  high_confidence_threshold: 0.65  # Trả lời sạch
  low_confidence_threshold: 0.35   # Từ chối
  min_avg_similarity: 0.45         # Ngưỡng skip LLM evaluate

# ═══════════════════════════════════════════
# RETRIEVAL — Điều chỉnh tìm kiếm
# ═══════════════════════════════════════════
retrieval:
  top_k: 3
  similarity_threshold: 0.35
  semantic_weight: 0.6
  keyword_weight: 0.4

# ═══════════════════════════════════════════
# MEMORY — Điều chỉnh bộ nhớ hội thoại
# ═══════════════════════════════════════════
memory:
  enabled: true
  strategy: "sliding_window"
  window_size: 5
  max_context_chars: 1500

# ═══════════════════════════════════════════
# LLM — Chọn provider và model
# ═══════════════════════════════════════════
llm:
  provider: "gemini"              # Hoặc "ollama"
  model_name: "gemini-2.5-flash"
  temperature: 0.3
  max_tokens: 2048

# ═══════════════════════════════════════════
# EMBEDDING — Model vectorhóa văn bản
# ═══════════════════════════════════════════
embedding:
  model_name: "BAAI/bge-m3"
  batch_size: 32
  dimension: 1024
```

---

## 14. Triển Khai — Deployment

### 14.1 Cài Đặt Thủ Công (Development)

```bash
# 1. Clone và cài dependencies
git clone <repo>
cd ĐATN
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# 2. Cấu hình môi trường
cp .env.example .env
# Sửa .env: GEMINI_API_KEY=your_key (nếu dùng Gemini)

# 3. Build knowledge base (chạy một lần)
python scripts/build_knowledge_base.py

# 4. Khởi động app
streamlit run app.py
# → http://localhost:8501
```

### 14.2 Docker Deployment (Production)

**Dockerfile**:
```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8501
HEALTHCHECK CMD curl -f http://localhost:8501/_stcore/health
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**docker-compose.yml** triển khai hai service:
```yaml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]

  chatbot:
    build: .
    ports:
      - "8501:8501"
    volumes:
      - ./knowledge_base:/app/knowledge_base
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - LLM_MODEL=mistral
      - LLM_SERVICE_URL=http://ollama:11434
    depends_on:
      ollama:
        condition: service_healthy
    networks:
      - chatbot-network
```

```bash
docker-compose up -d --build
```

### 14.3 Biến Môi Trường

```bash
# .env
GEMINI_API_KEY=AIzaSy...         # Google Gemini API key
LLM_MODEL=mistral                # Override model khi dùng Ollama
LLM_SERVICE_URL=http://localhost:11434
STREAMLIT_SERVER_PORT=8501
LOG_LEVEL=INFO
```

---

## 15. Luồng Tích Hợp Toàn Bộ Hệ Thống

### 15.1 Offline Pipeline (Build Time)

```
PDF files (9 docs)
    │
    ▼
scripts/build_knowledge_base.py
    │
    ├─ Step 1: PDFProcessor.process_pdf_file()
    │   ├─ pdfplumber → extract text + tables
    │   ├─ Regex cleanup (50+ patterns)
    │   ├─ Markdown formatting (# CHƯƠNG, ## Điều)
    │   └─ Save → data/raw_json/*.json
    │
    ├─ Step 2: TextChunker.chunk_all_documents()
    │   ├─ MarkdownHeaderTextSplitter → section splits
    │   ├─ RecursiveCharacterTextSplitter (1000/200)
    │   ├─ Table detection → preserve intact
    │   ├─ Attach metadata (source_file, chapter, article, is_table)
    │   └─ Save → data/chunks/*.json
    │
    └─ Step 3: VectorDatabaseManager.add_documents()
        ├─ EmbeddingModelManager → BAAI/bge-m3
        ├─ Embed each chunk → 1024-dim vector
        └─ Persist → data/chroma/ (ChromaDB)
```

### 15.2 Online Pipeline (Runtime — Per Question)

```
Người dùng gõ câu hỏi trên Streamlit
    │
    ▼
app.py → agent.answer_question(question, session_id)
    │
    ▼ BƯỚC 0: INTENT CLASSIFICATION
memory.get_context(session_id) ──────┐
memory.get_entities_from_memory() ───┤
memory.get_last_clarification_intent()┘
    │
IntentClassifier.classify(question, memory_context, memory_entities, previous_intent)
    │
    ├─ _call_llm(prompt) → JSON {intent, entities, confidence}
    ├─ Merge entities (LLM + memory)
    ├─ intent_config[intent_name] → check required_fields
    │
    ├─ needs_clarification = True?
    │   ├── YES → Save to memory (needs_clarification=True)
    │   │         Return clarification_question
    │   └── NO  → Continue to retrieval
    │
    ▼ BƯỚC 1-2: MULTI-HOP RETRIEVAL (max 2 hops)
for hop in range(2):
    │
    VectorDatabaseManager.search_similar(current_query, k=3, threshold=0.35)
    │
    ├─ len(results) < 2?
    │   └── Fallback: k=5, threshold=0.25
    │
    AgentState.add_iteration(Retrieve, ...)
    Merge results (dedup by content)
    │
    avg_sim = mean(top scores)
    │
    ├─ avg_sim >= 0.45?
    │   └── YES → Break loop → Go to Generate
    │
    LLM Evaluate: _EVALUATE_PROMPT → {relevant, reason}
    AgentState.add_iteration(Evaluate, ...)
    │
    ├─ is_relevant = True?
    │   └── YES → Break loop → Go to Generate
    │
    QueryRewrite: _REWRITE_PROMPT → new_query
    AgentState.add_iteration(QueryRewrite, ...)
    current_query = new_query
    │ (next hop)
    │
    ▼ BƯỚC 3: GENERATE ANSWER
_build_context(all_results) → formatted context string
_generate_answer(question, context) → _ANSWER_PROMPT → LLM → raw_answer
_calculate_confidence(results, answer, iterations) → 0.0 - 1.0
    │
    ▼ BƯỚC 4: CONFIDENCE GATE
confidence < 0.35 → reject_answer (no info found)
0.35 ≤ conf < 0.65 → raw_answer + warning_text
confidence ≥ 0.65 → raw_answer (clean)
    │
    ▼ BƯỚC 5: SAVE TO MEMORY
memory.add_turn(session_id, question, answer[:500], entities, intent, False)
    │
    ▼ RETURN TO UI
{
  answer, confidence, success,
  retrieved_chunks: [{index, content, score, source, chapter, article}],
  intent_name, entities,
  needs_clarification: False,
  state: AgentState (reasoning steps)
}
    │
    ▼
Streamlit renders:
├─ Chat message với answer (markdown)
├─ Confidence indicator (success/warning/error)
├─ Expander "Xem tài liệu nguồn" (chunks + scores)
└─ (optional) Reasoning steps
```

### 15.3 Sơ Đồ Các Class và Quan Hệ

```
StudentRegulationAgent
├── llm: OllamaLLM | ChatGoogleGenerativeAI
├── vector_db_manager: VectorDatabaseManager
│       └── vectorstore: Chroma
│               └── embeddings: HuggingFaceEmbeddings (BAAI/bge-m3)
├── intent_classifier: IntentClassifier
│       ├── intent_config: Dict (từ config.yaml)
│       └── _llm: Callable (wrapper around agent's llm)
└── memory: ConversationMemory (singleton)
        └── _store: {session_id: [ConversationTurn, ...]}

Per request:
└── state: AgentState
        └── steps: [Step(thought, action, action_input, observation), ...]
```

---

## Appendix A: Các Tham Số Quan Trọng Cần Điều Chỉnh

| Tham số | File | Giá trị mặc định | Ảnh hưởng |
|---|---|---|---|
| `retrieval.top_k` | config.yaml | 3 | Số docs lấy ra mỗi lần search |
| `retrieval.similarity_threshold` | config.yaml | 0.35 | Ngưỡng tối thiểu để giữ doc |
| `agent.min_avg_similarity` | config.yaml | 0.45 | Ngưỡng skip LLM evaluate |
| `agent.high_confidence_threshold` | config.yaml | 0.65 | Trả lời bình thường |
| `agent.low_confidence_threshold` | config.yaml | 0.35 | Từ chối trả lời |
| `agent.max_iterations` | config.yaml | 5 | Giới hạn reasoning steps |
| `memory.window_size` | config.yaml | 5 | Số turn nhớ |
| `chunking.chunk_size` | config.yaml | 1000 | Kích thước mỗi đoạn văn |
| `chunking.chunk_overlap` | config.yaml | 200 | Overlap giữa các đoạn |
| `llm.temperature` | config.yaml | 0.3 | Độ sáng tạo LLM (thấp = ổn định) |

## Appendix B: Hướng Phát Triển Tương Lai

1. **BM25 Hybrid Search**: Framework keyword search đã có sẵn (`keyword_weight: 0.4`), nhưng chưa kích hoạt. Tích hợp BM25Retriever sẽ cải thiện truy xuất với từ khóa chính xác (số điều, mã học phần).

2. **LangGraph State Machine**: Thay thế vòng lặp `for hop in range()` bằng LangGraph graph để quản lý state phức tạp hơn và hỗ trợ parallel retrieval.

3. **Summary Buffer Memory**: Hiện tại dùng sliding window (giữ K turn). Summary buffer sẽ tóm tắt các turn cũ, cho phép ngữ cảnh dài hơn.

4. **FastAPI REST API**: `api.enabled: false` trong config — đã thiết kế sẵn, chỉ cần bật để expose chatbot dưới dạng REST service.

5. **Re-ranking**: Sau retrieval, thêm cross-encoder re-ranking (ví dụ: `cross-encoder/ms-marco-MiniLM-L-6-v2`) để sắp xếp lại kết quả chính xác hơn.

6. **Evaluation Framework**: Xây dựng test set Q&A để đo RAGAS metrics: faithfulness, answer relevancy, context precision.
