# 💼 Config.yaml - Use Cases Thực Tế

## Tóm tắt

Document này cho thấy **cách sử dụng config.yaml** trong các **tình huống thực tế** mà bạn sẽ gặp phải.

---

## 📌 Use Case 1: Thêm PDF Mới

### Tình Huống
Bạn có một PDF mới: `Quy_che_he_PTNK_2025.pdf` muốn thêm vào hệ thống.

### Cách Làm (Hiện Tại - Cũ)
```python
# Phải sửa code trong example_pipeline.py
class DataPreparationPipelineRefactored:
    @staticmethod
    def _init_metadata_mapping():
        return {
            # ... existing mappings
            "Quy_che_he_PTNK_2025.pdf": {    # ← Thêm dòng này
                "doc_type": "Quy chế hệ PTNK",
                "effective_date": "2025-04-20",
                "applicable_students": "PTNK",
                "status": "active"
            }
        }

# Rồi chạy pipeline
pipeline = DataPreparationPipelineRefactored()
pipeline.run_full_pipeline()
```

**Vấn đề**: Phải edit code, risk bugs

### Cách Làm (Mới - Config)
```yaml
# Chỉ cần edit config.yaml!
pdf_processing:
  metadata_mapping:
    # ... existing PDFs
    "Quy_che_he_PTNK_2025.pdf":          # ← Thêm dòng này
      doc_type: "Quy chế hệ PTNK"
      effective_date: "2025-04-20"
      applicable_students: "PTNK"
      status: "active"
```

```python
# Code không cần thay đổi!
pipeline = DataPreparationPipelineRefactored(config_path="./config.yaml")
pipeline.run_full_pipeline()
```

**Lợi ích**: Không edit code, DevOps có thể thêm PDF 🎉

---

## 📌 Use Case 2: Tuning Chunk Size

### Tình Huống
Bạn thấy chunks quá nhỏ (1000 chars), muốn thử 2000 chars để xem hiệu quả.

### Cách Làm (Hiện Tại)
```python
# Sửa code trong TextChunker
class TextChunker:
    @staticmethod
    def chunk_all_documents(data_path: Path):
        # chunk_size = 1000  # ← Sửa giá trị này
        chunk_size = 2000   # ← Thay đổi
        
        # ...
```

**Vấn đề**: Phải sửa code, khó rollback

### Cách Làm (Mới - Config)
```yaml
# config_test.yaml
chunking:
  chunk_size: 2000        # ← Đơn giản thay đổi giá trị
  chunk_overlap: 200
```

```python
# Code hoàn toàn không thay đổi
from src.embeddings import TextChunker
from pathlib import Path

# Test 1
chunks1 = TextChunker.chunk_all_documents(
    Path("./data"),
    chunk_size=1000
)
print(f"Config 1: {len(chunks1)} chunks")

# Test 2
chunks2 = TextChunker.chunk_all_documents(
    Path("./data"),
    chunk_size=2000
)
print(f"Config 2: {len(chunks2)} chunks")

# So sánh kết quả - dễ dàng A/B test!
```

**Lợi ích**: Dễ A/B testing, no code change, easy rollback 📊

---

## 📌 Use Case 3: Đổi Embedding Model

### Tình Huống
Model `BAAI/bge-m3` tải chậm. Bạn muốn thử model nhẹ hơn: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`

### Cách Làm (Hiện Tại)
```python
# Sửa trong model.py
class EmbeddingModelManager:
    def _initialize_model(self):
        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # ← Sửa
        
        self.model = HuggingFaceEmbeddings(model_name=model_name)
```

**Vấn đề**: Phải sửa code, không thể dễ dàng switch back

### Cách Làm (Mới - Config)
```yaml
# config_fast.yaml (Model nhẹ)
embedding:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  cache_folder: "./models"
  batch_size: 64
  dimension: 384
```

```yaml
# config_accurate.yaml (Model nặng)
embedding:
  model_name: "BAAI/bge-m3"
  cache_folder: "./models"
  batch_size: 32
  dimension: 768
```

```python
# Code không cần thay đổi - chỉ cần chọn config!

# Test 1: Model nhẹ
from src.embeddings import EmbeddingModelManager
model_mgr_fast = EmbeddingModelManager(config_path="./config_fast.yaml")
embeddings_fast = model_mgr_fast.get_model()
print("✅ Fast model loaded")

# Test 2: Model nặng
model_mgr_accurate = EmbeddingModelManager(config_path="./config_accurate.yaml")
embeddings_accurate = model_mgr_accurate.get_model()
print("✅ Accurate model loaded")
```

**Lợi ích**: Dễ test nhiều models, no code change 🚀

---

## 📌 Use Case 4: Environment-Specific Config (Dev vs Prod)

### Tình Huống
Development dùng model nhỏ, production dùng model lớn. Cần 2 config khác nhau.

### Cách Làm (Mới - Config)

**config_dev.yaml**
```yaml
embedding:
  model_name: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
  batch_size: 16              # Nhỏ hơn cho dev

chunking:
  chunk_size: 500             # Nhỏ hơn để test nhanh
  chunk_overlap: 100

vectordb:
  persist_directory: "./data_dev/chroma"  # DB riêng cho dev
  collection_name: "regulations_dev"
```

**config_prod.yaml**
```yaml
embedding:
  model_name: "BAAI/bge-m3"
  batch_size: 64              # Lớn hơn cho prod (better performance)

chunking:
  chunk_size: 1000            # Optimal
  chunk_overlap: 200

vectordb:
  persist_directory: "/var/data/chroma"  # Production path
  collection_name: "student_regulations"
```

```python
# app.py - Tự động chọn config theo environment
import os
from src.embeddings import DataPreparationPipelineRefactored

# Chọn config dựa trên environment variable
env = os.getenv("ENVIRONMENT", "development")
config_path = f"./config_{env}.yaml"

# Khởi tạo pipeline
pipeline = DataPreparationPipelineRefactored(config_path=config_path)
pipeline.run_full_pipeline()

print(f"✅ Pipeline running in {env} mode with {config_path}")
```

**Sử dụng:**
```bash
# Development
ENVIRONMENT=dev python app.py

# Production
ENVIRONMENT=prod python app.py
```

**Lợi ích**: Single code, multiple configs, no conditionals 🎯

---

## 📌 Use Case 5: Tính Toán Top-K Động

### Tình Huống
Bạn muốn lấy số documents khác nhau tùy theo query:
- Query ngắn → top 3
- Query dài → top 10

### Cách Làm (Mới - Config)

**config.yaml**
```yaml
retrieval:
  top_k: 5                    # Default
  similarity_threshold: 0.5
```

```python
from src.embeddings import VectorDatabaseManager

vector_db = VectorDatabaseManager(embeddings)

# Query ngắn
short_results = vector_db.search_similar(
    query="Học bổng?",
    k=3  # Override default
)

# Query dài
long_query = "Tiêu chí xét duyệt học bổng Trần Đại Nghĩa cho sinh viên K70"
long_results = vector_db.search_similar(
    query=long_query,
    k=10  # Override default
)

# Dùng default từ config
medium_query = "Quy chế học tập"
medium_results = vector_db.search_similar(query=medium_query)  # k=5 từ config
```

**Lợi ích**: Flexible top-k, config acts as default 📚

---

## 📌 Use Case 6: Path Management - Multi-Project

### Tình Huống
Có nhiều projects khác nhau, mỗi cái có dữ liệu ở folder riêng.

### Cách Làm (Mới - Config)

**project1_config.yaml**
```yaml
data_paths:
  knowledge_base_raw: "/data/project1/knowledge_base/raw"
  output_base: "/data/project1/output"
  chroma_db: "/data/project1/vector_store/chroma"
```

**project2_config.yaml**
```yaml
data_paths:
  knowledge_base_raw: "/data/project2/knowledge_base/raw"
  output_base: "/data/project2/output"
  chroma_db: "/data/project2/vector_store/chroma"
```

```python
from src.embeddings import DataPreparationPipelineRefactored

# Project 1
pipeline1 = DataPreparationPipelineRefactored(config_path="./project1_config.yaml")
pipeline1.run_full_pipeline()

# Project 2
pipeline2 = DataPreparationPipelineRefactored(config_path="./project2_config.yaml")
pipeline2.run_full_pipeline()
```

**Lợi ích**: Một codebase, nhiều projects 🎪

---

## 📌 Use Case 7: Logging Configuration

### Tình Huống
Dev muốn DEBUG logs, Prod chỉ cần INFO.

### Cách Làm (Mới - Config)

**config_dev.yaml**
```yaml
logging:
  level: "DEBUG"              # Verbose
  file: "./logs/dev.log"
```

**config_prod.yaml**
```yaml
logging:
  level: "INFO"               # Less verbose
  file: "/var/logs/prod.log"
```

```python
import logging
import yaml

def setup_logging(config_path: str):
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    log_config = config.get("logging", {})
    
    logging.basicConfig(
        level=log_config.get("level", "INFO"),
        filename=log_config.get("file"),
        format=log_config.get("format")
    )

# Setup logging
setup_logging("./config.yaml")

logger = logging.getLogger(__name__)
logger.debug("Debug message")  # Chỉ hiện ở dev, không ở prod
```

**Lợi ích**: Centralized logging config 📋

---

## 📌 Use Case 8: Performance Tuning

### Tình Huống
Bạn muốn thử 3 configurations khác nhau để tìm optimal performance.

### Cách Làm

**config_small.yaml**
```yaml
chunking:
  chunk_size: 500
  chunk_overlap: 50
embedding:
  batch_size: 16
```

**config_medium.yaml**
```yaml
chunking:
  chunk_size: 1000
  chunk_overlap: 200
embedding:
  batch_size: 32
```

**config_large.yaml**
```yaml
chunking:
  chunk_size: 2000
  chunk_overlap: 400
embedding:
  batch_size: 64
```

```python
import time
from src.embeddings import DataPreparationPipelineRefactored

configs = ["config_small.yaml", "config_medium.yaml", "config_large.yaml"]
results = {}

for config_path in configs:
    start_time = time.time()
    
    pipeline = DataPreparationPipelineRefactored(config_path=config_path)
    pipeline.run_full_pipeline()
    
    elapsed = time.time() - start_time
    results[config_path] = elapsed
    
    print(f"{config_path}: {elapsed:.2f}s")

# Find best config
best_config = min(results.items(), key=lambda x: x[1])
print(f"\n✅ Best config: {best_config[0]} ({best_config[1]:.2f}s)")
```

**Lợi ích**: Easy performance comparison 📊

---

## 🎯 Quick Reference - Mỗi Use Case Cần Sửa Gì

| Use Case | File Cần Sửa | Cách Sửa |
|----------|-------------|---------|
| Thêm PDF mới | config.yaml | Thêm entry trong metadata_mapping |
| Đổi chunk_size | config.yaml | Đổi chunking.chunk_size |
| Đổi embedding model | config.yaml | Đổi embedding.model_name |
| Dev vs Prod | config_dev.yaml, config_prod.yaml | Tạo 2 file config |
| Top-K dynamic | Code (search_similar) | Pass `k` parameter |
| Paths khác nhau | config.yaml | Edit data_paths section |
| Logging khác | config.yaml | Edit logging section |
| Performance tuning | config.yaml | Thay đổi chunk_size, batch_size |

---

## 💡 Best Practice Summary

✅ **Do This:**
- Tất cả settings đặt trong config.yaml
- Có config_dev.yaml, config_prod.yaml riêng
- Override config qua environment variables (nếu cần)
- Version control config files
- Comment config để giải thích từng setting

❌ **Don't Do This:**
- Hardcode values trong code
- Quên commit config changes
- Để sensitive data (passwords) trong config
- Mix code + config changes trong same commit

---

## 📝 Template Config Checklist

Khi tạo config mới, đảm bảo có:

```yaml
☐ data_paths
  ☐ knowledge_base_raw
  ☐ output_base
  ☐ chroma_db

☐ embedding
  ☐ model_name
  ☐ cache_folder
  ☐ batch_size

☐ chunking
  ☐ chunk_size
  ☐ chunk_overlap

☐ vectordb
  ☐ persist_directory
  ☐ collection_name

☐ retrieval
  ☐ top_k
  ☐ similarity_threshold

☐ pdf_processing
  ☐ metadata_mapping

☐ logging
  ☐ level
  ☐ file
```

---

Với cách này, **config là single source of truth** cho tất cả settings. Code nhỏ gọn, maintainable, và dễ mở rộng! 🚀
