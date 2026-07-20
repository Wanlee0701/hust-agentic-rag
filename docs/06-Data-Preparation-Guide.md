# 06. Data Preparation Guide - PDF → Knowledge Base

## 📚 Mục Tiêu
Hiểu **quy trình chuẩn bị dữ liệu** - từ PDF tài liệu quy chế → chunks → embeddings → vector store sẵn sàng retrieve.

---

## 1. Overview: Data Pipeline

### 1.1 End-to-End Flow

```
┌────────────────────────────────────────────────────────────────┐
│              DATA PREPARATION PIPELINE                         │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  [SOURCE]                 [PROCESS]           [STORAGE]        │
│  ┌──────────┐             ┌──────────┐        ┌─────────┐     │
│  │          │             │          │        │         │     │
│  │ PDF Files│─────────→   │ Extract  │───────→│ Vector  │     │
│  │ (Quy chế)│  (1)        │ Text     │ (3)    │ Store   │     │
│  │          │             │          │        │ (Chroma)│     │
│  └──────────┘             │ Split    │        └─────────┘     │
│                           │ Chunks   │                         │
│  ┌──────────┐             │          │        ┌─────────┐     │
│  │ PDF Files│─────┐       └──────────┘──────→│ Metadata│     │
│  │ (English)│  (2)├──────→│ Add Meta │        │ Store   │     │
│  │ (if any) │     │       │ (lang,   │        │ (SQLite)│     │
│  └──────────┘     │       │  source, │        └─────────┘     │
│                   │       │  page)   │                         │
│  ┌──────────┐     │       │          │        ┌─────────┐     │
│  │ Already  │─────┤       └──────────┘───────→│ Embed   │     │
│  │ Processed│  (4)│           ↓         (5)   │ Models  │     │
│  │ Chunks   │     │       [Tokenize]          │ Cache   │     │
│  └──────────┘     └──────→│ & Embed  │        └─────────┘     │
│                           │ (Multi-  │                         │
│                           │  lingual)│                         │
│                           └──────────┘                         │
│                                                                │
│  Outputs:                                                      │
│  1. Cleaned text chunks                                        │
│  2. Embeddings (768-dim vectors)                              │
│  3. Metadata (source, language, chunk_index)                  │
│  4. Vector search index (Chroma DB)                           │
│  → Ready for retrieval! ✓                                     │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 2. Phase 1: Document Extraction

### 2.1 PDF Extraction

**Input:** `knowledge_base/raw/` contains PDF files
```
knowledge_base/
└── raw/
    ├── regulations_2024.pdf         (100 pages)
    ├── student_handbook.pdf         (50 pages)
    ├── scholarship_policy.pdf       (20 pages)
    └── ...
```

**Tool Options:**

#### Option A: PyPDF2 (Simple, Basic)
```python
import PyPDF2

def extract_pdf_pypdf(pdf_path):
    documents = []
    with open(pdf_path, 'rb') as pdf_file:
        reader = PyPDF2.PdfReader(pdf_file)
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            documents.append({
                "content": text,
                "page": page_num,
                "source": pdf_path
            })
    return documents

# Usage:
docs = extract_pdf_pypdf("regulations_2024.pdf")
```

**Pros:** Simple, minimal dependencies
**Cons:** Sometimes garbled text with complex PDFs

#### Option B: pdfplumber (Better, Recommended ⭐)
```python
import pdfplumber

def extract_pdf_pdfplumber(pdf_path):
    documents = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            text = page.extract_text()
            tables = page.extract_tables()  # Extract tables too!
            
            doc = {
                "content": text,
                "page": page_num,
                "source": pdf_path,
                "has_tables": bool(tables)
            }
            
            if tables:
                doc["tables"] = [str(t) for t in tables]
            
            documents.append(doc)
    return documents

# Usage:
docs = extract_pdf_pdfplumber("regulations_2024.pdf")
```

**Pros:** Better text extraction, handles tables
**Cons:** Slightly slower

#### Option C: Marker (AI-powered, Best but Slower)
```python
from marker.convert import convert_single_pdf

def extract_pdf_marker(pdf_path):
    full_text, metadata, images = convert_single_pdf(pdf_path)
    # Handles complex layouts, OCR if needed
```

**Pros:** Best accuracy for complex PDFs
**Cons:** Slower, needs GPU for OCR

**For DỰ ÁN:** Use **pdfplumber** (good balance)

### 2.2 Text Cleaning

```python
import re
import unicodedata

def clean_text(text):
    """Clean extracted text"""
    
    # 1. Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # 2. Remove special characters (but keep Vietnamese diacritics)
    text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', text)
    
    # 3. Normalize Unicode (NFC normalization)
    text = unicodedata.normalize('NFC', text)
    
    # 4. Strip leading/trailing whitespace
    text = text.strip()
    
    return text

# Usage:
cleaned_docs = []
for doc in docs:
    doc["content"] = clean_text(doc["content"])
    cleaned_docs.append(doc)
```

---

## 3. Phase 2: Text Chunking

### 3.1 Why Chunking?

**Problem:**
- LLM context window = 4096 tokens (~16KB text)
- Full PDF (100 pages) = too large to pass to LLM
- Need to split into manageable pieces

**Solution:** Chunk documents intelligently

### 3.2 Chunking Strategy

#### Option A: Simple Fixed-Size Chunking
```python
def chunk_fixed_size(text, chunk_size=1000, overlap=100):
    """Split text into fixed-size chunks with overlap"""
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)
    return chunks

chunks = chunk_fixed_size("Quy chế sinh viên...", chunk_size=1000)
# Result: ~10 chunks of ~1000 chars each
```

**Pros:** Simple, predictable
**Cons:** May break mid-sentence, lose context

#### Option B: Recursive Character-Level Chunking (Recommended ⭐)
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,           # Target chunk size (tokens)
    chunk_overlap=100,         # Overlap between chunks
    separators=[               # Try to split at these, in order
        "\n\n",               # Try paragraph break first
        "\n",                 # Then line break
        ". ",                 # Then sentence
        " ",                  # Then word
        ""                    # Finally character
    ]
)

documents = [
    {"page_content": "Text from page 1...", "metadata": {...}},
    {"page_content": "Text from page 2...", "metadata": {...}},
    ...
]

chunks = splitter.split_documents(documents)
# Result: Chunks split at sentence boundaries (better!)
```

**Pros:** Preserves meaning, splits at natural boundaries
**Cons:** Slightly slower, less predictable sizes

#### Option C: Semantic Chunking (Advanced)
```python
# Using sentence_transformers
# Split at sentences, merge semantically similar ones

from sentence_transformers import SentenceTransformer

model = SentenceTransformer("distiluse-base-multilingual-cased-v2")

sentences = text.split(". ")  # Split into sentences
embeddings = model.encode(sentences)

# Cluster semantically similar sentences into chunks
# More advanced, skip for now
```

**For DỰ ÁN:** Use **Recursive Character-Level** (good balance)

### 3.3 Recommended Chunking Config

```python
chunk_config = {
    "chunk_size": 1000,      # ~200-300 words
    "chunk_overlap": 100,    # Preserve context
    "separators": [
        "\n\n",              # Paragraph
        "\n",                # Line
        ". ",                # Sentence
        " ",                 # Word
        ""                   # Character
    ]
}

# This produces:
# - Chunks usually 800-1200 chars
# - Split at sentence/paragraph boundaries
# - 10% overlap for context preservation
# - Suitable for embedding & retrieval
```

---

## 4. Phase 3: Add Metadata

### 4.1 Metadata Structure

```python
def add_metadata(chunks, pdf_path, language="vi"):
    """Add useful metadata to chunks"""
    
    for idx, chunk in enumerate(chunks):
        chunk.metadata = {
            "source": pdf_path,              # Which PDF
            "chunk_index": idx,              # Position
            "page": chunk.metadata.get("page", 0),
            "language": language,            # vi / en
            "version": "1.0",                # KB version
            "indexed_date": "2025-04-09",
            "total_chunks": len(chunks)
        }
    
    return chunks

# Usage:
docs_with_meta = add_metadata(chunks, "regulations_2024.pdf", "vi")
```

### 4.2 Language Detection (Automatic)

```python
from langdetect import detect

def auto_detect_language(text):
    """Detect language of text"""
    try:
        lang = detect(text[:500])  # Check first 500 chars
        return lang if lang in ["vi", "en"] else "unknown"
    except:
        return "unknown"

# Update metadata:
for chunk in chunks:
    chunk.metadata["language"] = auto_detect_language(chunk.page_content)
```

---

## 5. Phase 4: Embedding Generation

### 5.1 Embedding Process

```python
from sentence_transformers import SentenceTransformer

# 1. Load multilingual embedding model
model = SentenceTransformer(
    "sentence-transformers/distiluse-base-multilingual-cased-v2",
    cache_folder="./models"
)

# 2. Generate embeddings for all chunks
def generate_embeddings(chunks, model=model, batch_size=32):
    """Generate embeddings for chunks"""
    
    texts = [chunk.page_content for chunk in chunks]
    
    # Batch process for efficiency
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True  # Return numpy arrays
    )
    
    # Attach embeddings to chunks
    for chunk, embedding in zip(chunks, embeddings):
        chunk.metadata["embedding_vector"] = embedding
        print(f"Generated embedding for chunk {chunk.metadata['chunk_index']}")
    
    return chunks

# 3. Process
chunks_with_embeddings = generate_embeddings(chunks)
print(f"Generated {len(chunks_with_embeddings)} embeddings")
# Result: Each chunk has 768-dim vector
```

### 5.2 Embedding Dimensions Explained

```
Embedding Output:
  "Học phí năm nhất" → [0.234, -0.567, 0.123, ..., 0.445]
                         ^ 768 dimensions ^
                       
  Each dimension captures different semantic meaning:
  - Dim1: Academic concept (0.234 = moderate)
  - Dim2: Financial concept (-0.567 = strong negative)
  - Dim3: Time concept (0.123 = weak)
  - ...
  - Dim768: (learned from training)
```

### 5.3 Caching Embeddings

```python
import pickle

# Save embeddings to disk (don't recompute)
def save_embeddings(chunks, output_path="./data/embeddings.pkl"):
    """Cache embeddings"""
    data = {
        "chunks": chunks,
        "metadata": {
            "model": "distiluse-base-multilingual-cased-v2",
            "generated_at": datetime.now().isoformat(),
            "total_chunks": len(chunks)
        }
    }
    with open(output_path, 'wb') as f:
        pickle.dump(data, f)
    print(f"Saved {len(chunks)} chunks with embeddings")

# Load from cache (next time)
def load_embeddings(input_path="./data/embeddings.pkl"):
    """Load cached embeddings"""
    with open(input_path, 'rb') as f:
        data = pickle.load(f)
    print(f"Loaded {len(data['chunks'])} chunks from cache")
    return data

# Usage:
if os.path.exists("./data/embeddings.pkl"):
    data = load_embeddings()  # Fast: 1s
    chunks = data["chunks"]
else:
    chunks = generate_embeddings(chunks)  # Slow: 30s
    save_embeddings(chunks)  # Save for next time
```

---

## 6. Phase 5: Store in Vector Database

### 6.1 Vector Store Ingestion

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# 1. Initialize embeddings (same model as before)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/distiluse-base-multilingual-cased-v2",
    cache_folder="./models"
)

# 2. Create Chroma vector store
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="./data/chroma",
    collection_name="regulations",
    client_type="persistent"  # Persist to disk
)

# 3. Add chunks to vector store
vectorstore.add_documents(chunks)
print(f"Added {len(chunks)} documents to vector store")

# 4. Persist to disk (Chroma does this automatically)
vectorstore.persist()

# Verify:
print(f"Total documents in store: {vectorstore._collection.count()}")
```

### 6.2 Test Retrieval

```python
# Test if retrieval works
from langchain.vectorstores import Chroma

vectorstore = Chroma(
    persist_directory="./data/chroma",
    embedding_function=embeddings,
    collection_name="regulations"
)

# Test query
query = "Học phí bao nhiêu?"
results = vectorstore.similarity_search(query, k=5)

print(f"\nQuery: {query}")
print(f"Top 5 results:")
for i, result in enumerate(results, 1):
    print(f"{i}. Page {result.metadata['page']}: {result.page_content[:100]}...")
```

---

## 7. Complete Data Preparation Script

### 7.1 End-to-End Pipeline

```python
# data_preparation.py

import os
import pickle
from pathlib import Path
from datetime import datetime

import pdfplumber
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings
from langdetect import detect

class DataPreparationPipeline:
    def __init__(self, kb_path="./knowledge_base", output_path="./data"):
        self.kb_path = kb_path
        self.output_path = output_path
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/distiluse-base-multilingual-cased-v2"
        )
    
    def extract_pdfs(self):
        """Extract text from all PDFs"""
        documents = []
        for pdf_file in Path(self.kb_path).glob("*.pdf"):
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    documents.append({
                        "page_content": text,
                        "metadata": {
                            "source": str(pdf_file),
                            "page": page_num
                        }
                    })
        return documents
    
    def chunk_documents(self, documents):
        """Split documents into chunks"""
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        return splitter.split_documents(documents)
    
    def add_metadata(self, chunks):
        """Add language info"""
        for chunk in chunks:
            try:
                lang = detect(chunk.page_content[:500])
                chunk.metadata["language"] = lang
            except:
                chunk.metadata["language"] = "unknown"
        return chunks
    
    def store_in_vectordb(self, chunks):
        """Store in Chroma"""
        vectorstore = Chroma(
            embedding_function=self.embeddings,
            persist_directory=os.path.join(self.output_path, "chroma"),
            collection_name="regulations",
            client_type="persistent"
        )
        vectorstore.add_documents(chunks)
        vectorstore.persist()
        print(f"Stored {len(chunks)} chunks in vector DB")
    
    def run(self):
        """Run full pipeline"""
        print("Step 1: Extracting PDFs...")
        docs = self.extract_pdfs()
        print(f"  Found {len(docs)} pages")
        
        print("Step 2: Chunking documents...")
        chunks = self.chunk_documents(docs)
        print(f"  Created {len(chunks)} chunks")
        
        print("Step 3: Adding metadata...")
        chunks = self.add_metadata(chunks)
        print(f"  Added language info")
        
        print("Step 4: Creating vector store...")
        self.store_in_vectordb(chunks)
        
        print("\n✓ Data preparation complete!")
        print(f"Knowledge base ready with {len(chunks)} chunks")

# Usage:
if __name__ == "__main__":
    pipeline = DataPreparationPipeline()
    pipeline.run()
```

### 7.2 Running the Pipeline

```bash
# Prepare data once
python data_preparation.py

# Output:
# Step 1: Extracting PDFs...
#   Found 170 pages
# Step 2: Chunking documents...
#   Created 312 chunks
# Step 3: Adding metadata...
#   Added language info
# Step 4: Creating vector store...
#   Stored 312 chunks in vector DB
# 
# ✓ Data preparation complete!
# Knowledge base ready with 312 chunks
```

---

## 8. Folder Structure After Preparation

```
project/
├── knowledge_base/
│   └── raw/
│       ├── regulations_2024.pdf
│       ├── student_handbook.pdf
│       ├── scholarship.pdf
│       └── ...
│
├── data/
│   ├── chroma/                    # Vector store
│   │   ├── chroma.sqlite3
│   │   ├── index/
│   │   ├── embeddings/
│   │   └── ...
│   │
│   └── embeddings.pkl             # Cached embeddings
│
└── models/                         # Downloaded models
    └── distiluse-multilingual/    # Cached model file
```

---

## 9. Data Quality Checklist

Before going to retrieval phase:

- [ ] All PDFs extracted without corruption
- [ ] Text properly cleaned (no garbled characters)
- [ ] Chunks split at meaningful boundaries
- [ ] Metadata complete (source, page, language)
- [ ] Embeddings generated (768-dim vectors)
- [ ] Vector store initialized and persisted
- [ ] Sample retrieval test passes
- [ ] Vietnamese & English docs both indexed
- [ ] Multilingual search works (test)

---

## Summary 📝

| Phase | Input | Process | Output |
|-------|-------|---------|--------|
| 1. Extract | PDFs | pdfplumber | Raw text |
| 2. Clean | Raw text | Normalize, remove junk | Clean text |
| 3. Chunk | Clean text | Recursive splitting | 1000-char chunks |
| 4. Metadata | Chunks | Add source, language | Enhanced chunks |
| 5. Embed | Chunks | SentenceTransformer | 768-dim vectors |
| 6. Store | Embeddings + vectors | Chroma ingestion | Ready-to-query KB |

---

## Next Steps

🔗 **Related Files:**
- `04-System-Architecture.md` - Where KB fits in system
- `07-Retrieval-Component.md` - How retriever uses prepared KB
