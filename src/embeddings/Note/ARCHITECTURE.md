# 📚 Hướng dẫn Module Embedding - Kiến trúc và Luồng Hoạt động

## 🏗️ Cấu trúc Module

```
src/embeddings/
├── __init__.py           # Export tất cả modules
├── model.py              # Load embeddings model từ config
├── processor.py          # Xử lý PDF, chunking
└── vector_db.py          # Quản lý Chroma vector database
```

---

## 🔄 Luồng Hoạt động Chi tiết

### **1. KHỞI TẠO MODEL (model.py)**

```python
from src.embeddings import EmbeddingModelManager

# Bước 1: Load config.yaml
model_manager = EmbeddingModelManager(config_path="./config.yaml")

# Bước 2: Tự động load HuggingFace embeddings model
# - Đọc config.embedding.model_name
# - Đọc config.embedding.cache_folder
# - Tải model từ HuggingFace

# Bước 3: Lấy model đã khởi tạo
embeddings_model = model_manager.get_model()
```

**Cấu hình từ config.yaml:**
```yaml
embedding:
  model_name: "BAAI/bge-m3"        # Model HuggingFace
  cache_folder: "./models"         # Nơi cache model
  batch_size: 32                   # Batch size embedding
  dimension: 768                   # Vector dimension
```

---

### **2. XỬ LÝ PDF (processor.py)**

#### **Bước 2A: Trích xuất từ PDF**

```python
from src.embeddings import PDFProcessor

# Trích xuất text từ file PDF
content = PDFProcessor.process_pdf_file("path/to/file.pdf")

# Nội dung:
# ✓ Xóa header/footer, số trang
# ✓ Format lại cấu trúc Markdown (# Chương, ## Điều)
# ✓ Trích bảng thành Markdown format
# ✓ Làm sạch dữ liệu
```

**Quy trình chi tiết:**
```
PDF File
  ↓
pdfplumber.open()
  ├─→ Trích xuất text từ mỗi trang
  ├─→ Trích bảng (table.extract_tables())
  ├─→ Convert bảng → Markdown format
  └─→ Làm sạch text (remove patterns)
  ↓
Document JSON (lưu vào data/)
```

---

#### **Bước 2B: Tách thành Chunks**

```python
from src.embeddings import TextChunker

# Tách một JSON file thành chunks
chunks = TextChunker.chunk_json_document(
    json_path=Path("data/file.json"),
    chunk_size=1000,      # Kích thước chunk
    chunk_overlap=200     # Overlap giữa chunks
)

# Tách tất cả documents
all_chunks = TextChunker.chunk_all_documents(
    data_path=Path("data/"),
    chunk_size=1000,
    chunk_overlap=200
)
```

**Quy trình chi tiết:**
```
JSON Document (metadata + content)
  ↓
Markdown Header Split (chia theo # Chương, ## Điều)
  ↓
Text Chunk Split (kích thước 1000 ký tự, overlap 200)
  ├─→ Giữ nguyên bảng (không bị tách)
  └─→ Tách text bình thường
  ↓
Document[] (mỗi doc có page_content + metadata)
  ↓
Gắn metadata gốc (doc_type, effective_date, v.v.)
```

**Ví dụ metadata của mỗi chunk:**
```python
{
    "doc_type": "Quy chế đào tạo",
    "effective_date": "2025-05-28",
    "applicable_students": "ALL",
    "status": "active",
    "source_file": "Quy_che_25.pdf",
    "processed_date": "2025-04-20T10:30:00",
    "chapter_title": "CHƯƠNG I",
    "article_title": "Điều 1.",
    "is_table": False
}
```

---

### **3. LƯU VÀO VECTOR DATABASE (vector_db.py)**

```python
from src.embeddings import VectorDatabaseManager

# Khởi tạo vector database manager
vector_db = VectorDatabaseManager(
    embeddings=embeddings_model,
    persist_directory="./data/chroma",
    collection_name="student_regulations"
)

# Thêm documents vào vector database
vector_db.add_documents(chunks)
# Chroma tự động embedding mỗi chunk
# và lưu vào vector database

# Tìm kiếm tương tự
results = vector_db.search_similar(
    query="Học sinh cấp 3 có được học bổng không?",
    k=5  # Top 5 results
)

for doc, score in results:
    print(f"Score: {score:.4f}")
    print(f"Content: {doc.page_content[:200]}")
```

**Quy trình chi tiết:**
```
Document[] (với metadata)
  ↓
HuggingFace Embeddings
  (Convert text → vector 768-dim)
  ↓
Chroma Vector Database
  ├─→ Lưu vector
  ├─→ Lưu metadata
  └─→ Persist tới disk
  ↓
Vector Search (khi cần lấy dữ liệu)
```

---

## 📊 Quy trình Toàn bộ Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    DATA PREPARATION PIPELINE                │
└─────────────────────────────────────────────────────────────┘

1️⃣  LOAD CONFIG & MODEL
    ├─ EmbeddingModelManager.load_config("config.yaml")
    └─ EmbeddingModelManager.get_model() → HuggingFaceEmbeddings

2️⃣  PDF PROCESSING
    ├─ PDFProcessor.process_pdf_file()
    ├─ Extract text + tables
    ├─ Clean & format
    └─ Save as JSON → data/

3️⃣  CHUNKING
    ├─ TextChunker.chunk_all_documents()
    ├─ Split by Markdown headers
    ├─ Split by chunk size (keep tables)
    ├─ Attach metadata
    └─ Save chunks → data/chunks/

4️⃣  VECTOR DATABASE
    ├─ VectorDatabaseManager()
    ├─ load chunks
    ├─ HuggingFace embedding
    └─ Store in Chroma DB → data/chroma/
```

---

## 💡 Ví dụ Sử Dụng Hoàn Chỉnh

```python
import logging
from pathlib import Path
from src.embeddings import (
    EmbeddingModelManager,
    PDFProcessor,
    TextChunker,
    VectorDatabaseManager
)

logging.basicConfig(level=logging.INFO)

# 1️⃣ KHỞI TẠO MODEL
print("1️⃣ Initializing embeddings model...")
model_manager = EmbeddingModelManager(config_path="./config.yaml")
embeddings = model_manager.get_model()

# 2️⃣ XỬ LÝ PDF (nếu chưa có JSON)
print("\n2️⃣ Processing PDFs...")
kb_path = Path("./knowledge_base/raw")
output_path = Path("./data")

for pdf_file in kb_path.glob("*.pdf"):
    content = PDFProcessor.process_pdf_file(str(pdf_file))
    # Lưu content thành JSON file (tùy bạn implement)

# 3️⃣ TÁCH CHUNKS
print("\n3️⃣ Chunking documents...")
chunks = TextChunker.chunk_all_documents(
    data_path=output_path,
    chunk_size=1000,
    chunk_overlap=200
)

# 4️⃣ LƯU VÀO VECTOR DATABASE
print("\n4️⃣ Storing in vector database...")
vector_db = VectorDatabaseManager(
    embeddings=embeddings,
    persist_directory="./data/chroma",
    collection_name="student_regulations"
)
vector_db.add_documents(chunks)

# 5️⃣ TÌM KIẾM
print("\n5️⃣ Searching...")
query = "Tiêu chí xét duyệt học bổng là gì?"
results = vector_db.search_similar(query, k=3)

for doc, score in results:
    print(f"\n📌 Score: {score:.4f}")
    print(f"Document type: {doc.metadata.get('doc_type')}")
    print(f"Content preview: {doc.page_content[:300]}...")
```

---

## 🔑 Lợi ích của Kiến trúc Này

| Khía cạnh | Lợi ích |
|----------|---------|
| **Modular** | Mỗi module có trách nhiệm cụ thể, dễ test |
| **Configurable** | Tất cả settings trong config.yaml |
| **Scalable** | Dễ thêm PDF mới, tăng chunk_size, đổi model |
| **Maintainable** | Code rõ ràng, comments đầy đủ |
| **Reusable** | Import modules vào app.py hoặc agent |
| **Debuggable** | Logging chi tiết ở mỗi bước |

---

## 📝 Các File Cần Có

```
✓ config.yaml                      (cấu hình embedding, vectordb)
✓ src/embeddings/model.py          (load model)
✓ src/embeddings/processor.py      (xử lý PDF + chunking)
✓ src/embeddings/vector_db.py      (quản lý Chroma DB)
✓ src/embeddings/__init__.py       (export modules)
```

---

## 🚀 Cách Tích Hợp với app.py

```python
# app.py
from src.embeddings import VectorDatabaseManager, EmbeddingModelManager

# Khởi tạo
model_manager = EmbeddingModelManager()
embeddings = model_manager.get_model()

vector_db = VectorDatabaseManager(
    embeddings=embeddings,
    persist_directory="./data/chroma"
)

# Sử dụng trong agent
def retrieve_documents(query: str):
    results = vector_db.search_similar(query, k=5)
    return results
```

---

## ⚙️ Hướng Dẫn Chạy Lần Đầu

```bash
# 1. Đảm bảo requirements.txt có:
# langchain-huggingface
# langchain-chroma
# pdfplumber
# chromadb
# pyyaml

pip install -r requirements.txt

# 2. Đặt PDF vào knowledge_base/raw/

# 3. Chạy data preparation (ETL)
python -c "
from src.embeddings import EmbeddingModelManager, PDFProcessor, TextChunker, VectorDatabaseManager
from pathlib import Path

model_mgr = EmbeddingModelManager()
embeddings = model_mgr.get_model()

chunks = TextChunker.chunk_all_documents(Path('./data'))
vector_db = VectorDatabaseManager(embeddings)
vector_db.add_documents(chunks)

print('✅ Pipeline complete!')
"
```

---

📌 **Ghi chú:** Kiến trúc này cho phép bạn dễ dàng:
- Thay đổi embedding model trong config
- Thêm PDF mới mà không cần thay đổi code
- Thử nghiệm chunk_size khác nhau
- Tái sử dụng modules trong các project khác
