# 📊 Config.yaml - Bảng Tóm Tắt Toàn Bộ

## 🎯 Tóm Tắt 1 Dòng
**Config.yaml** chứa **TẤT CẢ** parameters. Các modules load config → không cần hardcode.

---

## 📋 Config Sections & Triển Khai

### 1. data_paths

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `knowledge_base_raw` | `./knowledge_base/raw` | Thư mục PDF gốc | `example_pipeline.py` line init |
| `output_base` | `./data` | Thư mục output chính | `example_pipeline.py` line init |
| `json_output` | `./data` | Lưu JSON từ PDF | `example_pipeline.py` step_1 |
| `chunks_output` | `./data/chunks` | Lưu chunks JSON | `example_pipeline.py` step_2 |
| `chroma_db` | `./data/chroma` | Vector database | `vector_db.py` `__init__` |
| `logs_output` | `./logs` | Log files | `logging.py` setup |

**Cách Triển Khai:**
```python
# example_pipeline.py - __init__()
data_paths = self.config.get("data_paths", {})
self.kb_path = Path(data_paths.get("knowledge_base_raw", "./knowledge_base/raw"))
self.output_path = Path(data_paths.get("output_base", "./data"))
```

---

### 2. embedding

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `model_name` | `BAAI/bge-m3` | HuggingFace model | `model.py` `_initialize_model()` |
| `cache_folder` | `./models` | Model cache dir | `model.py` `_initialize_model()` |
| `batch_size` | `32` | Batch size embedding | `model.py` `_initialize_model()` |
| `dimension` | `768` | Vector dimension | Info chỉ |

**Cách Triển Khai:**
```python
# model.py - _initialize_model()
model_name = self.embedding_config.get("model_name", "BAAI/bge-m3")
cache_folder = self.embedding_config.get("cache_folder", "./models")
batch_size = self.embedding_config.get("batch_size", 32)

self.model = HuggingFaceEmbeddings(
    model_name=model_name,
    cache_folder=cache_folder,
    encode_kwargs={"batch_size": batch_size}
)
```

---

### 3. chunking

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `chunk_size` | `1000` | Kích thước chunk | `processor.py` `chunk_all_documents()` |
| `chunk_overlap` | `200` | Overlap giữa chunks | `processor.py` `chunk_all_documents()` |
| `markdown_headers` | List | Markdown levels | `processor.py` `chunk_json_document()` |
| `separators` | List | Text separators | `processor.py` (fallback) |

**Cách Triển Khai:**
```python
# processor.py - chunk_all_documents()
chunking_config = config.get("chunking", {})
chunk_size = chunking_config.get("chunk_size", 1000)
chunk_overlap = chunking_config.get("chunk_overlap", 200)

chunks = TextChunker.chunk_all_documents(
    data_path=data_path,
    chunk_size=chunk_size,
    chunk_overlap=chunk_overlap
)
```

---

### 4. vectordb

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `provider` | `chroma` | DB provider | Info chỉ |
| `persist_directory` | `./data/chroma` | Nơi lưu DB | `vector_db.py` `__init__()` |
| `collection_name` | `student_regulations` | Collection name | `vector_db.py` `__init__()` |
| `options` | Dict | Advanced options | `vector_db.py` `_initialize_database()` |

**Cách Triển Khai:**
```python
# vector_db.py - __init__()
vectordb_config = config.get("vectordb", {})
self.persist_directory = Path(
    vectordb_config.get("persist_directory", "./data/chroma")
)
self.collection_name = vectordb_config.get(
    "collection_name", "student_regulations"
)
```

---

### 5. retrieval

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `top_k` | `5` | Số documents trả về | `vector_db.py` `search_similar()` |
| `similarity_threshold` | `0.5` | Ngưỡng similarity | `vector_db.py` `search_similar()` |
| `semantic_weight` | `0.6` | Trọng số semantic | Info (future) |
| `keyword_weight` | `0.4` | Trọng số keyword | Info (future) |

**Cách Triển Khai:**
```python
# vector_db.py - search_similar()
if k is None:
    k = self.retrieval_config.get("top_k", 5)

threshold = self.retrieval_config.get("similarity_threshold", 0.5)

results = self.vectorstore.similarity_search_with_score(query, k=k)
results = [(doc, score) for doc, score in results 
           if score >= threshold]
```

---

### 6. pdf_processing

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `metadata_mapping` | Dict | PDF metadata | `example_pipeline.py` `__init__()` |
| `text_cleanup_patterns` | List | Regex patterns | `processor.py` `extract_pdf_text()` |

**Cách Triển Khai:**
```python
# example_pipeline.py - __init__()
pdf_processing = self.config.get("pdf_processing", {})
self.metadata_mapping = pdf_processing.get("metadata_mapping", {})

# Sử dụng
for pdf_name in pdf_files:
    meta = self.metadata_mapping.get(pdf_name, {})
```

---

### 7. logging

| Key | Giá Trị | Sử Dụng | Triển Khai |
|-----|--------|--------|-----------|
| `level` | `INFO` | Log level | Utility function |
| `file` | `./logs/chatbot.log` | Log file path | Utility function |
| `format` | String | Log format | Utility function |

**Cách Triển Khai:**
```python
# Utility function
logging_config = config.get("logging", {})
logging.basicConfig(
    level=logging_config.get("level", "INFO"),
    filename=logging_config.get("file"),
    format=logging_config.get("format")
)
```

---

## 🔄 Flow: Config → Code

```
┌─────────────────────────────────────┐
│         config.yaml                 │
│  (Tất cả parameters)                │
└────────────┬────────────────────────┘
             │
             ├─→ data_paths ──────→ example_pipeline.py
             │
             ├─→ embedding ──────→ model.py
             │
             ├─→ chunking ──────→ processor.py
             │
             ├─→ vectordb ──────→ vector_db.py
             │
             ├─→ retrieval ──────→ vector_db.py
             │
             ├─→ pdf_processing ──────→ example_pipeline.py
             │
             └─→ logging ──────→ logging setup
```

---

## ✅ Implementation Checklist

### Phase 1: Chuẩn Bị (Đã Hoàn Thành ✅)
- [x] config.yaml được tạo với tất cả sections
- [x] Documentation được viết (ARCHITECTURE.md, CONFIG_IMPLEMENTATION.md, v.v.)
- [x] Ví dụ được chuẩn bị (CONFIG_USE_CASES.md)

### Phase 2: Code Updates (Cần Làm 🔴)

| File | Method | Changes | Priority |
|------|--------|---------|----------|
| model.py | `_initialize_model()` | ✅ Đã có - load từ config | Done |
| processor.py | `process_pdf_file()` | 🟡 Optional - thêm patterns param | Later |
| processor.py | `chunk_all_documents()` | 🟡 Optional - load từ config | Later |
| vector_db.py | `__init__()` | 🔴 **ADD: Load vectordb từ config** | **NOW** |
| vector_db.py | `search_similar()` | 🔴 **ADD: Dùng top_k, threshold từ config** | **NOW** |
| example_pipeline.py | `__init__()` | 🔴 **UPDATE: Load tất cả paths, metadata** | **NOW** |
| example_pipeline.py | `step_2_chunk_documents()` | 🔴 **ADD: Lấy chunk settings từ config** | **NOW** |

### Phase 3: Testing (Sau Updates)
- [ ] Test load config.yaml
- [ ] Test model loading từ config
- [ ] Test chunking với config
- [ ] Test vector DB với config
- [ ] Test pipeline toàn bộ với config
- [ ] Test multiple configs (dev, prod, test)

### Phase 4: Deployment
- [ ] Commit config.yaml + code changes
- [ ] Setup config for dev environment
- [ ] Setup config for production environment
- [ ] Document config in README

---

## 📌 Cách Sử Dụng - Quick Start

```python
# Tất cả tự động load từ config.yaml
from src.embeddings import (
    EmbeddingModelManager,
    TextChunker,
    VectorDatabaseManager
)
from src.embeddings.example_pipeline import DataPreparationPipelineRefactored

# 1. Run full pipeline
pipeline = DataPreparationPipelineRefactored(config_path="./config.yaml")
pipeline.run_full_pipeline()

# 2. Manual usage
model_mgr = EmbeddingModelManager(config_path="./config.yaml")
embeddings = model_mgr.get_model()

chunks = TextChunker.chunk_all_documents(Path("./data"), config_path="./config.yaml")

vector_db = VectorDatabaseManager(embeddings, config_path="./config.yaml")
vector_db.add_documents(chunks)

# 3. Search with config defaults
results = vector_db.search_similar("Học bổng là gì?")  # k=5 từ config
```

---

## 💼 Real-World Scenarios

### Scenario 1: Thêm PDF
```diff
# config.yaml
pdf_processing:
  metadata_mapping:
    "Existing.pdf": {...}
+   "New.pdf":
+     doc_type: "Type"
+     effective_date: "2025-04-20"
+     applicable_students: "ALL"
+     status: "active"
```

### Scenario 2: Đổi Model
```diff
# config.yaml
embedding:
-  model_name: "BAAI/bge-m3"
+  model_name: "intfloat/multilingual-e5-large"
```

### Scenario 3: Tuning Chunk Size
```diff
# config.yaml
chunking:
-  chunk_size: 1000
+  chunk_size: 2000
-  chunk_overlap: 200
+  chunk_overlap: 400
```

### Scenario 4: Dev vs Prod
```bash
# Development
ENVIRONMENT=dev python app.py  # Dùng config_dev.yaml

# Production
ENVIRONMENT=prod python app.py  # Dùng config_prod.yaml
```

---

## 🎯 Lợi Ích Tóm Tắt

| Khía Cạnh | Lợi Ích |
|----------|--------|
| **Flexibility** | Đổi settings không cần sửa code |
| **Maintainability** | Settings tập trung ở 1 file |
| **Deployment** | Easy dev/staging/prod setup |
| **Non-technical Updates** | DevOps có thể quản lý config |
| **A/B Testing** | Dễ test multiple configurations |
| **Version Control** | Config có thể version như code |
| **Scalability** | Thêm PDF/model mà không phức tạp |

---

## 📚 Documentation Files

| File | Nội Dung |
|------|---------|
| CONFIG_IMPLEMENTATION.md | Chi tiết triển khai trong từng module |
| CODE_UPDATES_GUIDE.md | Cách update code để sử dụng config |
| CONFIG_USE_CASES.md | Real-world scenarios |
| Tệp này | Tóm tắt toàn bộ |

---

## 🚀 Next Steps

1. **Hiểu** config.yaml structure (đọc document này)
2. **Implement** Code updates (xem CODE_UPDATES_GUIDE.md)
3. **Test** Configuration (xem CONFIG_USE_CASES.md)
4. **Deploy** (dùng dev/prod configs)

---

**Tóm lại**: Config.yaml là **single source of truth** cho tất cả settings. Không cần hardcode, dễ maintain, dễ mở rộng! 🎯
