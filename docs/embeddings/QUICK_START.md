# 🚀 Hướng Dẫn Sử Dụng Module Embedding - Quick Start

## 📂 Cấu trúc Thư mục Đã Tạo

```
src/embeddings/
├── __init__.py              ✅ Export modules
├── model.py                 ✅ Load embeddings model
├── processor.py             ✅ Xử lý PDF + chunking  
├── vector_db.py             ✅ Quản lý Chroma DB
├── example_pipeline.py      ✅ Ví dụ sử dụng toàn bộ pipeline
└── ARCHITECTURE.md          ✅ Giải thích chi tiết
```

---

## 🎯 Cách Sử Dụng - 3 Cách

### **Cách 1: Chạy Pipeline Đầy Đủ (Khuyến nghị)**

```bash
python src/embeddings/example_pipeline.py
```

✅ Sẽ tự động:
1. Xử lý tất cả PDF
2. Tách thành chunks
3. Lưu vào vector database
4. Test retrieval

---

### **Cách 2: Sử Dụng Từng Module Riêng Lẻ**

```python
from pathlib import Path
from src.embeddings import EmbeddingModelManager, PDFProcessor, TextChunker, VectorDatabaseManager

# 1. Load model
model_mgr = EmbeddingModelManager(config_path="./config.yaml")
embeddings = model_mgr.get_model()

# 2. Xử lý PDF
content = PDFProcessor.process_pdf_file("knowledge_base/raw/Quy_che_25.pdf")

# 3. Chunking
chunks = TextChunker.chunk_all_documents(Path("./data"))

# 4. Vector DB
vector_db = VectorDatabaseManager(embeddings)
vector_db.add_documents(chunks)

# 5. Tìm kiếm
results = vector_db.search_similar("Học bổng là gì?", k=3)
for doc, score in results:
    print(f"Score: {score:.4f} - {doc.page_content[:100]}")
```

---

### **Cách 3: Tích Hợp vào app.py**

```python
# app.py
from src.embeddings import EmbeddingModelManager, VectorDatabaseManager

class StudentRegulationChatbot:
    def __init__(self):
        # Load model
        self.model_mgr = EmbeddingModelManager()
        self.embeddings = self.model_mgr.get_model()
        
        # Init vector DB
        self.vector_db = VectorDatabaseManager(self.embeddings)
    
    def retrieve_documents(self, query: str):
        """Lấy tài liệu liên quan"""
        return self.vector_db.search_similar(query, k=5)
```

---

## 📚 Mô Tả Từng Module

### **1. model.py - EmbeddingModelManager**

| Method | Mục đích |
|--------|---------|
| `__init__()` | Load config và khởi tạo model |
| `get_model()` | Trả về HuggingFaceEmbeddings model |
| `get_config()` | Trả về toàn bộ config |
| `get_embedding_config()` | Trả về embedding config section |

**Ví dụ:**
```python
model_mgr = EmbeddingModelManager("./config.yaml")
embeddings = model_mgr.get_model()
config = model_mgr.get_embedding_config()
print(f"Model: {config['model_name']}")
```

---

### **2. processor.py - PDFProcessor & TextChunker**

#### **PDFProcessor**

| Method | Mục đích |
|--------|---------|
| `extract_pdf_text()` | Làm sạch text PDF |
| `extract_tables_as_markdown()` | Trích bảng thành Markdown |
| `process_pdf_file()` | Xử lý toàn bộ file PDF |

#### **TextChunker**

| Method | Mục đích |
|--------|---------|
| `split_text_keeping_tables()` | Tách text nhưng giữ bảng |
| `chunk_json_document()` | Tách một JSON document |
| `chunk_all_documents()` | Tách tất cả documents |
| `save_chunks_to_json()` | Lưu chunks vào JSON |

**Ví dụ:**
```python
# Xử lý PDF
content = PDFProcessor.process_pdf_file("file.pdf")

# Chunking
chunks = TextChunker.chunk_json_document(
    Path("data/file.json"),
    chunk_size=1000,
    chunk_overlap=200
)
```

---

### **3. vector_db.py - VectorDatabaseManager**

| Method | Mục đích |
|--------|---------|
| `add_documents()` | Thêm documents vào DB |
| `search_similar()` | Tìm kiếm documents tương tự |
| `get_collection_info()` | Lấy thông tin collection |
| `delete_collection()` | Xóa collection |
| `persist()` | Lưu trữ DB |

**Ví dụ:**
```python
vector_db = VectorDatabaseManager(embeddings)
vector_db.add_documents(chunks)

# Tìm kiếm
results = vector_db.search_similar(
    query="Tiêu chí xét duyệt học bổng",
    k=5
)

# Xem thông tin
info = vector_db.get_collection_info()
print(f"Total docs: {info['count']}")
```

---

## ⚙️ Cấu Hình (config.yaml)

Các thiết lập quan trọng:

```yaml
embedding:
  model_name: "BAAI/bge-m3"        # Model HuggingFace
  cache_folder: "./models"         # Cache model
  batch_size: 32                   # Batch size
  dimension: 768                   # Vector dimension

vectordb:
  provider: "chroma"
  persist_directory: "./data/chroma"
  collection_name: "regulations"

data_preparation:
  chunk_size: 1000                 # Kích thước chunk
  chunk_overlap: 200               # Overlap giữa chunks
```

---

## 🔄 Luồng Hoạt Động Chi Tiết

```
┌─────────────────────────────────────────────────┐
│ 1. LOAD EMBEDDINGS MODEL (model.py)             │
│    config.yaml → HuggingFaceEmbeddings          │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│ 2. PROCESS PDF (processor.py - PDFProcessor)    │
│    - Extract text                               │
│    - Clean data                                 │
│    - Extract tables                             │
│    → Save as JSON                               │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│ 3. CHUNK DOCUMENTS (processor.py - TextChunker) │
│    - Split by headers (Chương/Điều)            │
│    - Split by size (1000 chars)                 │
│    - Keep tables intact                         │
│    - Attach metadata                            │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│ 4. EMBED & STORE (vector_db.py)                 │
│    - Embedding: text → vector                   │
│    - Store in Chroma DB                         │
│    - Persist to disk                            │
└─────────────────┬───────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────────┐
│ 5. SEARCH & RETRIEVE                            │
│    - User query → vector                        │
│    - Find similar vectors                       │
│    - Return top-k documents                     │
└─────────────────────────────────────────────────┘
```

---

## 📊 Metadata Structure

Mỗi chunk sẽ có metadata như sau:

```python
{
    # Metadata gốc (từ JSON document)
    "doc_type": "Quy chế đào tạo",
    "effective_date": "2025-05-28",
    "applicable_students": "ALL",
    "status": "active",
    "source_file": "Quy_che_25.pdf",
    "processed_date": "2025-04-20T10:30:00",
    
    # Metadata từ chunking
    "chapter_title": "CHƯƠNG I",
    "article_title": "Điều 1.",
    "is_table": False
}
```

---

## ⚠️ Lưu Ý Quan Trọng

1. **Lần đầu chạy**: Sẽ tải model HuggingFace (~2GB), mất vài phút
2. **PDF format**: Cần PDF text-based (có thể copy text), không phải scanned PDF
3. **Memory**: Khi chunking toàn bộ documents, cần RAM đủ (~2-4GB)
4. **Tìm kiếm**: Query nên bằng tiếng Việt để embedding chính xác

---

## 🧪 Testing

```python
# Test model loading
from src.embeddings import EmbeddingModelManager
model_mgr = EmbeddingModelManager()
print("✅ Model loaded successfully")

# Test processing
from src.embeddings import PDFProcessor
content = PDFProcessor.process_pdf_file("test.pdf")
print(f"✅ Extracted {len(content)} characters")

# Test chunking
from src.embeddings import TextChunker
chunks = TextChunker.chunk_all_documents(Path("data"))
print(f"✅ Created {len(chunks)} chunks")

# Test vector DB
from src.embeddings import VectorDatabaseManager
vector_db = VectorDatabaseManager(model_mgr.get_model())
print(f"✅ Vector DB initialized")
```

---

## 🚀 Tiếp Theo

1. **Chạy pipeline**: `python src/embeddings/example_pipeline.py`
2. **Kiểm tra dữ liệu**: `data/chroma/` → Vector database
3. **Tích hợp với agent**: Import `VectorDatabaseManager` trong `app.py`
4. **Tùy chỉnh**: Sửa config.yaml cho embedding settings

---

## 📞 Troubleshooting

| Lỗi | Giải pháp |
|-----|----------|
| `config.yaml not found` | Kiểm tra đường dẫn config_path |
| `PDF không được xử lý` | Đảm bảo PDF có text (không phải scanned) |
| `Out of memory` | Giảm chunk_size hoặc batch_size |
| `Module not found` | Kiểm tra `src/embeddings/__init__.py` có đúng imports |
| `Model download lâu` | Model sẽ cache lần đầu, lần sau nhanh hơn |

---

📌 **Quan trọng**: Tất cả cấu trúc này được thiết kế để:
- ✅ Modular & reusable
- ✅ Configurable (via config.yaml)
- ✅ Maintainable & scalable
- ✅ Easy to test & debug
