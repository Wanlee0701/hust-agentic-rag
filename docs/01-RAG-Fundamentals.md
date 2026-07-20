# 01. RAG Fundamentals - Nền Tảng Retrieval-Augmented Generation

## 📚 Mục Tiêu
Hiểu rõ **Retrieval-Augmented Generation (RAG)** là gì, tại sao nó quan trọng, và nó giải quyết vấn đề gì của Large Language Models (LLMs).

---

## 1. Vấn Đề: LLM Bị Giới Hạn Khi Nào?

### 1.1 Knowledege Cutoff
- **LLM được huấn luyện** vào một thời điểm nhất định (ví dụ: Llama 2 cutoff tháng 4/2023)
- **Không biết về sự kiện** xảy ra sau thời điểm đó
- Ví dụ: Nếu bạn hỏi về quy chế sinh viên năm 2024, model không biết vì nó được train trên dữ liệu đến 2023

### 1.2 Hallucination (Ảo Tưởng)
- **LLM đôi khi "bịa chuyện"** - generate answer nghe có vẻ hợp lý nhưng hoàn toàn sai
- **Không có mechanism** để verify với dữ liệu thực tế
- Ví dụ: Hỏi "Tuition fee bao nhiêu?", model có thể nói "8 triệu/năm" (không đúng)

### 1.3 Domain-Specific Knowledge
- **Kiến thức chuyên biệt** (quy chế sinh viên, policy nội bộ) không nằm trong training data
- Model không thể biết mà chỉ đoán

### 1.4 Privacy & Security
- Nếu gửi query lên cloud API (ChatGPT, GPT-4), **dữ liệu người dùng bị lộ**
- Không phù hợp với thông tin nhạy cảm (sinh viên info)

---

## 2. Giải Pháp: Retrieval-Augmented Generation (RAG)

### 2.1 Khái Niệm
**RAG = Semantic Search + LLM Generation**

```
┌─────────────────────────────────────────────────────┐
│                  RAG Pipeline                       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  User Query                                         │
│      │                                              │
│      ▼                                              │
│  [STEP 1: RETRIEVAL]                               │
│  └─ Search Knowledge Base (Vector DB)              │
│     └─ Find top-K most relevant documents          │
│        └─ Returns: [Doc1, Doc2, Doc3, ...]        │
│                                                     │
│      │                                              │
│      ▼                                              │
│  [STEP 2: AUGMENTATION]                            │
│  └─ Combine: Query + Retrieved Documents           │
│     └─ Create: Enhanced Prompt                     │
│        └─ Format: "Given [Doc1, Doc2], answer Q"  │
│                                                     │
│      │                                              │
│      ▼                                              │
│  [STEP 3: GENERATION]                              │
│  └─ Feed to LLM                                     │
│     └─ LLM generates answer based on docs          │
│        └─ Answer grounded in actual data           │
│                                                     │
│      │                                              │
│      ▼                                              │
│  Answer with Sources ✓                             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 2.2 Ý Tưởng Chính
1. **Don't ask LLM to remember** → Hãy cung cấp dữ liệu cho nó
2. **LLM là expert lý luận** → Cho nó documents, nó tổng hợp & generate answer tốt
3. **Grounded Answers** → Answer dựa vào thực tế, không ảo tưởng

---

## 3. Thành Phần Chính của RAG

### 3.1 Knowledge Base (Cơ Sở Tri Thức)
**Là gì:** Tập hợp các documents, từ khóa, thông tin được tổ chức
**Ví dụ trong dự án:**
- Tài liệu PDF quy chế sinh viên
- Formatted thành text chunks
- Stored in vector store

**Đặc điểm:**
- Có thể cập nhật mà không cần retrain model
- Độc lập với LLM

### 3.2 Retriever (Công Cụ Tìm Kiếm)
**Là gì:** Module tìm documents liên quan từ Knowledge Base
**2 Phương Pháp Chính:**

#### a) Vector/Semantic Search
```
Process:
  Document → Embedding Vector (768 dimensions)
  Query    → Embedding Vector (768 dimensions)
  
  Compare: Cosine Similarity
  Result: Top-K documents most similar to query
```

**Ưu điểm:** Hiểu meaning, semantics
**Nhược điểm:** Không tốt khi query có keyword cụ thể

#### b) Keyword/BM25 Search
```
Process:
  Query keywords: ["quy chế", "học phí", "nhập học"]
  Search: Find docs containing ALL/ANY keywords
  Result: Exact match, ranking by frequency
```

**Ưu điểm:** Tốt với keyword cụ thể, nhanh
**Nhược điểm:** Không hiểu meaning nếu dùng synonym

#### c) Hybrid Search (Best of Both)
```
Vector Score + BM25 Score → Combined Ranking
(= Semantic + Keyword = More accurate retrieval)
```

### 3.3 Language Model (LLM)
**Là gì:** Model generate answer từ retrieved documents
**Role trong RAG:**
- Input: Query + Retrieved docs
- Output: Answer grounded in those docs
- Không cần generate từ memory riêng

**Ưu điểm:**
- Tập trung vào lý luận & tổng hợp
- Ít hallucination hơn (vì có documents)
- Có thể add citations/sources

---

## 4. So Sánh: LLM Truyền Thống vs RAG

| Aspect | Traditional LLM | RAG |
|--------|-----------------|-----|
| **Knowledge Source** | Training weights | External Knowledge Base |
| **Hallucination Risk** | ⚠️ High | ✅ Low |
| **Update Knowledge** | 🚫 Retrain model | ✅ Update docs only |
| **Latency** | ⚡ Fast | ~1-2s (retrieval overhead) |
| **Accuracy** | 📊 Depends on training | 📊 Better for specific domains |
| **Privacy** | Local only | Can be local + KB |
| **Control** | 🚫 Limited | ✅ Can control KB content |

---

## 5. Ứng Dụng trong Dự Án: Chatbot Quy Chế Sinh Viên

### 5.1 Tại Sao RAG Phù Hợp?
✅ **Knowledge Base cứ mê:** Quy chế sinh viên = tài liệu PDF cố định, có thể cực specific  
✅ **Domain-specific:** Cần chính xác 100%, không được ảo tưởng  
✅ **Privacy:** Dữ liệu sinh viên local, không gửi cloud  
✅ **Updatable:** Khi quy chế thay đổi, chỉ cần update PDF → reindex  

### 5.2 Workflow
```
Student: "Học phí năm nhất bao nhiêu?"
   ↓
[RETRIEVER] Search KB: 
   → Find docs about "học phí", "nhập học", "năm nhất"
   → Return: [QD-Section3.pdf, TuitionPolicy.txt, ...]
   ↓
[AUGMENT] Create Prompt:
   "Based on these documents: [QD-Section3...], 
    answer: Học phí năm nhất bao nhiêu?"
   ↓
[LLM] Answer:
   "Theo quy chế sinh viên (Section 3), 
    học phí năm nhất là 8 triệu VND. 
    (Source: QD-Section3.pdf:parag5)"
   ↓
Student: Gets accurate, sourced answer ✓
```

---

## 6. Hạn Chế của RAG Cơ Bản

| Hạn Chế | Ảnh Hưởng | Cách Giải Quyết |
|--------|----------|-----------------|
| **Poor Retrieval** | Lấy doc sai → answer sai | Hybrid search, re-ranking |
| **Complex Questions** | "What if I do X then Y?" → Cần reasoning | **→ Agentic RAG** |
| **Multi-language** | "Hỏi Tiếng Việt, doc tiếng Anh?" | **→ CLIR (Cross-Lingual IR)** |
| **Large KB** | 1000+ docs → slow search | Chunking, indexing, caching |

---

## 7. Khám Phá Tiếp Theo

🔗 **Các file liên quan:**
- `02-AgenticRAG-Architecture.md` - Giải quyết vấn đề "phức tạp" với Agent + Reasoning
- `03-CLIR-Multilingual.md` - Giải quyết vấn đề "đa ngôn ngữ"
- `06-Data-Preparation-Guide.md` - Cách xây dựng Knowledge Base
- `07-Retrieval-Component.md` - Chi tiết cách implement retriever

---

## Summary 📝

| Concept | Giải Thích |
|---------|-----------|
| **RAG** | = Gửi relevant docs → LLM generate answer based on those |
| **Why** | LLM memory hạn chế, RAG dùng external KB → grounded answers |
| **3 Steps** | Retrieve docs → Augment prompt → LLM generate |
| **Benefit** | Accurate, updatable, privacy-preserving, no hallucination |
| **For Project** | Perfect cho chatbot quy chế (specific domain, need accuracy) |

---

## Key Takeaways 🎯

1. **RAG = LLM + Vector DB + Retrieval**
2. **Solve:** Hallucination, knowledge cutoff, privacy issues
3. **3 Components:** Knowledge Base, Retriever, LLM
4. **2 Retrieval Methods:** Vector search + Keyword search (hybrid best)
5. **Next:** AgenticRAG adds reasoning loop to handle complex queries
