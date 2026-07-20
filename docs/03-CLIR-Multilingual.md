# 03. CLIR & Multilingual Support - Xử Lý Tiếng Việt & Tiếng Anh

## 📚 Mục Tiêu
Hiểu **Cross-Lingual Information Retrieval (CLIR)** - làm sao để chatbot xử lý được cả tiếng Việt và tiếng Anh một cách seamless.

---

## 1. Thách Thức Đa Ngôn Ngữ

### 1.1 Ví Dụ: Language Mismatch

**Scenario:**
- Student hỏi tiếng Việt: "Hình thức học tập của trường là gì?"
- KB chứa: English docs từ international partnership
- Expected: Tìm và hiểu docs tiếng Anh, trả lời tiếng Việt

**Vấn Đề Traditional Retrieval:**
```
Query: "Hình thức học tập"      (Vietnamese)
Search in KB: 
  ❌ Won't match "Learning Modality" (English)
  ❌ Wrong results or no results
```

### 1.2 Language Challenges

| Challenge | Impact | Example |
|-----------|--------|---------|
| **Language Mismatch** | Query & docs different language | Vi query + En docs |
| **Synonym Across Lang** | Same meaning, different words | "học lại" = "retake" |
| **Context Lost** | Translating loses nuance | "Điểm dưới C" |
| **Writing Variants** | Vi without diacritics: "hoc" vs "học" | Typo tolerance |
| **Code-switching** | "Học tiếng Anh hay Learning English" | Mixed language |

---

## 2. CLIR: Giải Pháp

### 2.1 Khái Niệm
**CLIR = Cross-Lingual IR**
- Tìm documents relevant regardless of language
- Support retrieving từ KB tiếng Anh khi query tiếng Việt (& vice versa)

### 2.2 Phương Pháp CLIR

#### **Method 1: Multilingual Embeddings (Recommended ⭐)**
```
Concept:
  Sentence-Transformers multilingual model
  → Maps ALL languages to SAME embedding space
  
Process:
  "Học tiếng Anh" (Vietnamese)
        ↓
    Embeddings Model
        ↓
    [0.23, -0.15, 0.67, ..., 0.42]  (768-dim vector)
    
  "Learning English" (English)
        ↓
    Embeddings Model (SAME model)
        ↓
    [0.24, -0.14, 0.68, ..., 0.43]  (768-dim vector)
    
  ✓ Vectors very similar!
  ✓ Cosine similarity high → Good retrieval
```

**Pros:**
- ✅ No translation needed
- ✅ Fast (single embedding once)
- ✅ Preserves meaning across languages
- ✅ Handle code-switching

**Cons:**
- ⚠️ Multilingual model slightly less accurate than monolingual
- ⚠️ Must use same model for query & documents

**Models to Use:**
- `sentence-transformers/distiluse-base-multilingual-cased-v2` (223 languages, 768-dim)
- `sentence-transformers/multilingual-e5-base` (100+ languages)
- Both: local, free, support Vietnamese

#### **Method 2: Query Translation**
```
Process:
  Vietnamese Query: "Học tiếng Anh"
         ↓
    Translator (e.g., Huggingface/Google Translate)
         ↓
    English Query: "Learn English"
         ↓
    Standard Retrieval (search with English query)
         ↓
    Retrieve from KB (mostly English docs)
         ↓
    Translate Answer back to Vietnamese
         ↓
    Vietnamese Answer: "Học tiếng Anh là..."
```

**Pros:**
- ✅ Works with any retrieval method
- ✅ Can use monolingual embeddings

**Cons:**
- ❌ 2x API calls (slow)
- ❌ Translation errors compound
- ❌ Meaning can be lost in translation
- ❌ Hard to maintain privacy (need external translator unless local)

**Local Translation Options:**
- `MarianMT` (HuggingFace, small models, EN ↔ VI, VI ↔ EN)
- Open source, but slower

#### **Method 3: Language-Specific Retriever (Not recommended for multi-lang)**
```
If Vietnamese query:
  Use Vietnamese-only embedder
Else if English query:
  Use English-only embedder
```

**Cons:** Doesn't solve cross-lingual retrieval

---

## 3. Best Approach for Dự Án: Multilingual Embeddings

### 3.1 Why?
✅ Simple to implement
✅ Private (no external translation API)
✅ Handles Vietnamese naturally
✅ Good performance

### 3.2 Architecture

```
┌─────────────────────────────────────────────────────────┐
│       Multilingual CLIR Architecture                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  [INITIALIZATION]                                       │
│  └─ Load: sentence-transformers/distiluse-multilingual  │
│  └─ Load KB docs (Vi + En) into vector store            │
│  └─ Generate embeddings for ALL docs (once)            │
│                                                         │
│  [RUNTIME]                                              │
│  Hỏi tiếng Việt: "Học phí bao nhiêu?"                  │
│        ↓                                                │
│  [AUTO DETECT] Language = Vietnamese                   │
│  (optional, but good for logging)                      │
│        ↓                                                │
│  [EMBED] Use SAME multilingual model                    │
│  Query embedding: [0.12, -0.34, 0.89, ...]            │
│        ↓                                                │
│  [SEARCH] Cosine similarity in vector DB               │
│  Compare with ALL doc embeddings (Vi + En)            │
│        ↓                                                │
│  [RETRIEVE] Top-K docs (might be Vi doc or En doc)     │
│  Result: Both Vietnamese & English docs ranked         │
│        ↓                                                │
│  [GENERATION] LLM generates answer                      │
│  Input language: Vietnamese                            │
│  Answer language: Automatically Vietnamese             │
│  (LLM infers from query language)                       │
│        ↓                                                │
│  "Học phí năm nhất: 8 triệu VND..."                    │
│  (Source: Doc1.pdf, Doc2.txt)                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 3.3 Generation Layer: Output Language

**Problem:**
If retrieved docs are English but user asked Vietnamese:
- Generate answer in English? ❌ Bad UX
- Translate back to Vietnamese? ⚠️ Extra step

**Solution: Language-Aware Prompting**
```python
# Detect input language
input_language = detect_language(user_query)  # → "vi"

# Create prompt that instructs LLM
prompt = f"""
You are answering a student query.
The student asked in {input_language}.
Please answer ONLY in {input_language}.

Query: {user_query}
Relevant information:
{retrieved_docs}

Answer:
"""

# LLM generates answer in Vietnamese automatically
answer = llm.generate(prompt)
# Output: Vietnamese ✓
```

**Why this works:**
- LLM is smart enough to follow instructions
- No extra translation needed
- Preserves meaning & nuance

---

## 4. Implementation Details

### 4.1 Data Preparation

**When Ingesting KB:**
```python
documents = [
  {"title": "Học phí", "content": "Học phí năm nhất...", "lang": "vi"},
  {"title": "Tuition Fee", "content": "First year tuition...", "lang": "en"},
  ...
]

# Generate embeddings for ALL (regardless of language)
for doc in documents:
    doc_embedding = multilingual_model.encode(doc["content"])
    store_in_vectordb(doc_embedding, doc["title"], doc["lang"])
```

### 4.2 Retrieval

```python
def retrieve_multilingual(query, top_k=5):
    # 1. Embed query (same model as docs)
    query_embedding = multilingual_model.encode(query)
    
    # 2. Search in vector DB
    results = vectordb.search(query_embedding, top_k=top_k)
    # Returns: docs in ANY language that match semantically
    
    # 3. Optional: Re-rank by language preference
    # If prefer Vietnamese docs, boost scores for lang="vi"
    
    return results  # Mixed language results OK!
```

### 4.3 Language Detection (Optional but Good)

```python
from langdetect import detect

def detect_query_language(query):
    try:
        lang = detect(query)  # Returns: "vi", "en", etc.
        return lang
    except:
        return "unknown"

# Use for: logging, conditional processing, output language
```

---

## 5. Edge Cases & Handling

### 5.1 Code-Switching (Mixed Language)
**Query:** "Tuition fee là học phí bao nhiêu?"

**Handling:**
```python
# Multilingual embeddings naturally handle this
# Model trained on code-switched data
query_embedding = multilingual_model.encode(query)
# Embeddings capture mixed-language meaning ✓
```

### 5.2 Typos & Diacritics Variation
**Query:** "hoc phi" (without diacritics) vs "học phí" (with)

**Handling Options:**

**Option A:** Normalize input (remove diacritics)
```python
import unicodedata

def remove_diacritics(text):
    nfd = unicodedata.normalize('NFD', text)
    return ''.join(char for char in nfd 
                   if unicodedata.category(char) != 'Mn')

query = "học phí" → "hoc phi"
```

**Option B:** Let model handle (embeddings are robust)
- Sentence-transformers trained on varied text
- Usually works without explicit normalization

### 5.3 Language Not in Model Support
**What if query in Chinese but KB supports only Vi/En?**
- Most multilingual models support 100+ languages
- If unsupported: graceful fallback
- Or: translate to English first, then retrieve

---

## 6. Evaluation: Is Retrieval Working Cross-Lingually?

### 6.1 Manual Testing

```
Test Cases:

Case 1:
  Input: "What is the tuition?" (English)
  Expected Output: Relevant Vietnamese or English docs about học phí
  ✓ Pass if retrieved correctly

Case 2:
  Input: "Học phí là gì?" (Vietnamese)
  Expected Output: Relevant docs (both Vi & En ok)
  ✓ Pass if retrieved correctly

Case 3:
  Input: "Learning methods are?" (English)
  Expected Output: Docs about hình thức học tập
  ✓ Pass if retrieved correctly
```

### 6.2 Metrics

- **Retrieval Recall:** Does it find relevant docs in other languages?
- **Language Distribution:** % of Vi docs vs En docs retrieved
- **User Satisfaction:** Do answers make sense?

---

## 7. For Your Project: Specific Setup

### 7.1 Recommended Configuration

```python
# config.yaml
embedding:
  model_name: "sentence-transformers/distiluse-base-multilingual-cased-v2"
  dimension: 768
  batch_size: 32
  
language_detection:
  enabled: true
  model: "langdetect"  # Simple, lightweight
  
supported_languages:
  - vi  # Vietnamese
  - en  # English
  
output_language: "auto"  # Match input language
```

### 7.2 Knowledge Base Structure

```
knowledge_base/
├── vietnamese/
│   ├── quy_che_2024.pdf
│   ├── tuition.txt
│   └── ...
│
├── english/
│   ├── regulations_2024.pdf
│   ├── intl_student_guide.txt
│   └── ...
│
└── multilingual/  (same content in both languages)
    ├── scholarship_info.md  (Vi + En in same file)
    └── ...
```

---

## 8. Summary 📝

| Aspect | Solution |
|--------|----------|
| **Challenge** | KB in multiple languages, users query in any language |
| **Solution** | Multilingual embeddings (CLIR) |
| **How** | Use same multilingual model for all embedding |
| **Benefit** | Seamless cross-language retrieval, no translation needed |
| **Implementation** | Use `sentence-transformers/distiluse-multilingual` |
| **Trade-off** | Slightly less accurate than monolingual, but good enough |
| **For Output** | Instruct LLM to answer in input language |

---

## Key Takeaways 🎯

1. **CLIR = Retrieve across languages without translation**
2. **Multilingual embeddings best approach for privacy**
3. **Sentence-Transformers supports 223 languages** ✓
4. **Different language queries can retrieve mixed-language results** ✓
5. **LLM output language can follow input language** ✓

---

## Next Steps

🔗 **Related Files:**
- `04-System-Architecture.md` - Full architecture with CLIR
- `06-Data-Preparation-Guide.md` - How to prepare multilingual KB
- `07-Retrieval-Component.md` - Retrieval implementation
