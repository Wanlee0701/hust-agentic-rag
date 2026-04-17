# 07. Retrieval Component - Semantic Search + BM25 Hybrid

## 📚 Mục Tiêu  
Hiểu **chi tiết cách retriever hoạt động** - semantic search, BM25, hybrid ranking, re-ranking để lấy documents phù hợp nhất từ vector store.

---

## 1. Retrieval Overview

### 1.1 Role in System

```
Agent Query: "Học phí năm nhất bao nhiêu?"
      │
      ▼
┌─────────────────────────────────────────┐
│    RETRIEVAL COMPONENT (This file!)     │
│                                         │
│  Job: Find TOP-K most relevant docs    │
│        from Knowledge Base              │
├─────────────────────────────────────────┤
│                                         │
│  Input:  Query string                   │
│  Output: [Doc1, Doc2, Doc3, Doc4, Doc5] │
│          (sorted by relevance)          │
│                                         │
└─────────────────────────────────────────┘
      │
      ▼
LLM uses these docs to generate answer ✓
```

### 1.2 Two Retrieval Methods

#### Method 1: Semantic/Vector Search
- Query → embedding → cosine similarity with stored embeddings
- **What:** Meaning-based matching
- **How good:** 90-95% accuracy for similar meanings

#### Method 2: BM25 Keyword Search
- Query keywords → exact keyword matching in docs
- **What:** Keyword-based matching
- **How good:** 85-90% for exact phrases

**Best:** Combine both → Hybrid search (95-98% accuracy!)

---

## 2. Semantic Search (Vector-Based)

### 2.1 How It Works

```
INFERENCE TIME (at query):

User Query: "Học phí năm nhất?"
      │
      ▼
[EMBED] SentenceTransformer.encode()
  └─ [0.123, -0.456, 0.789, ..., 0.234]  (768-dim)
      │
      ▼
[SEARCH] Chroma.similarity_search()
  ├─ Compare query embedding with all doc embeddings
  ├─ Cosine similarity:
  │  Doc1: 0.92 ⭐
  │  Doc2: 0.87 ⭐
  │  Doc3: 0.75 ⭐
  │  Doc4: 0.68 ⭐
  │  Doc5: 0.45 (not relevant)
  │  ...
  │
  ▼
[RANK] Sort by score descending
  └─ Return top-5 docs with highest similarity ✓
```

### 2.2 Implementation

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# Initialize
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/distiluse-base-multilingual-cased-v2"
)

vectorstore = Chroma(
    persist_directory="./data/chroma",
    embedding_function=embeddings,
    collection_name="regulations"
)

# Semantic search
query = "Học phí năm nhất bao nhiêu?"
docs = vectorstore.similarity_search(query, k=5)

# Results
for doc in docs:
    print(f"Score: {doc.metadata.get('score')}")
    print(f"Source: {doc.metadata['source']}")
    print(f"Content: {doc.page_content[:100]}...")
    print()
```

### 2.3 Cosine Similarity Math (Deep Dive)

```
Query Vector:  Q = [q1, q2, q3, ..., q768]
Doc Vector:    D = [d1, d2, d3, ..., d768]

Cosine Similarity = (Q · D) / (||Q|| × ||D||)
                  = sum(q_i × d_i) / (sqrt(sum(q_i²)) × sqrt(sum(d_i²)))

Result: Score between 0 and 1
  1.0 = identical meaning
  0.9 = very similar
  0.7 = somewhat similar
  0.5 = weakly related
  0.0 = completely different
```

### 2.4 Semantic Search Strengths & Weaknesses

**Strengths ✅:**
- Understands meaning/context
- Works even if words different ("học lại" = "retake")
- Handles Vietnamese + English
- Good for general understanding

**Weaknesses ❌:**
- Misses specific keywords
- Example: Query "GPA 2.0" might return docs about "academic standing" (related but not exact)
- If keyword exact then other meaning, still returns other meaning

---

## 3. BM25 Keyword Search

### 3.1 How BM25 Works

```
BM25 = TF-IDF based ranking

TF (Term Frequency):
  How often keyword appears in doc
  More appearances = higher relevance
  
IDF (Inverse Document Frequency):
  How rare the keyword is across all docs
  Rare keyword = higher weight
  Common keyword ("the") = lower weight

BM25 Score = TF × IDF × (k1 + 1) / (TF + k1(1 - b + b × doc_length/avg_doc_length))
           = (Somewhat complex formula, but idea is: rarity × frequency × length normalization)
```

### 3.2 Implementation with Chroma

```python
# Option A: Using LangChain's BM25 retriever

from langchain.retrievers import BM25Retriever
from langchain.schema import Document

# Convert Chroma docs to simple format
documents = [
    Document(page_content="Học phí năm nhất...", metadata={...}),
    Document(page_content="Tuition fee first year...", metadata={...}),
    ...
]

# Create BM25 retriever
bm25_retriever = BM25Retriever.from_documents(documents)

# Search
query = "Học phí năm nhất?"
bm25_docs = bm25_retriever.get_relevant_documents(query)
print(f"BM25 found {len(bm25_docs)} results")
```

### 3.3 BM25 Strengths & Weaknesses

**Strengths ✅:**
- Exact keyword matching
- Works for specific queries ("GPA 2.0", "deadline 15/9")
- Very fast (no embedding needed)
- Works for domain-specific terminology

**Weaknesses ❌:**
- Doesn't understand meaning
- Query "học lại" won't match doc with "retake" (different words)
- Bad for Vietnamese without diacritics ("hoc lai")
- No semantic understanding

---

## 4. Hybrid Retrieval (Best of Both Worlds!)

### 4.1 Hybrid Strategy

```
┌────────────────────────────────────────────────────────┐
│ HYBRID RETRIEVAL PIPELINE                              │
├────────────────────────────────────────────────────────┤
│                                                        │
│ Query: "Học phí năm nhất bao nhiêu?"                  │
│        │                                               │
│        ├─→ [Semantic Search]      (Chroma)            │
│        │   Results: [Doc1:0.92, Doc3:0.75,...]       │
│        │                                               │
│        └─→ [BM25 Search]          (LangChain)         │
│            Results: [Doc2:0.88, Doc1:0.82,...]       │
│                                                        │
│        ▼                                               │
│ ┌─ MERGE & RANK ─────────────────────────────────────┐│
│ │ Combine scores:                                    ││
│ │ weighted_score = 0.6 × semantic_score + 0.4 × bm25││
│ │                                                    ││
│ │ Doc1: 0.6×0.92 + 0.4×0.82 = 0.880 ⭐              ││
│ │ Doc2: 0.6×0.70 + 0.4×0.88 = 0.772                 ││
│ │ Doc3: 0.6×0.75 + 0.4×0.60 = 0.690                 ││
│ │ ...                                                  ││
│ │                                                    ││
│ │ Final ranking: [Doc1, Doc2, Doc3, ...]            ││
│ └────────────────────────────────────────────────────┘│
│        │                                               │
│        ▼                                               │
│ Return Top-K: [Doc1, Doc2, Doc3, Doc4, Doc5]         │
│                                                        │
└────────────────────────────────────────────────────────┘
```

### 4.2 Hybrid Implementation

```python
from langchain.retrievers import EnsembleRetriever
from langchain.retrievers import BM25Retriever
from langchain.vectorstores import Chroma

# 1. Create semantic retriever (Chroma)
vectorstore = Chroma(
    persist_directory="./data/chroma",
    embedding_function=embeddings,
    collection_name="regulations"
)
semantic_retriever = vectorstore.as_retriever(
    search_kwargs={"k": 5}
)

# 2. Create BM25 retriever
documents = [...]  # Load documents
bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 5

# 3. Combine them (Ensemble)
hybrid_retriever = EnsembleRetriever(
    retrievers=[semantic_retriever, bm25_retriever],
    weights=[0.6, 0.4]  # 60% semantic, 40% BM25
)

# 4. Search
query = "Học phí năm nhất?"
hybrid_docs = hybrid_retriever.get_relevant_documents(query)
print(f"Hybrid search found {len(hybrid_docs)} results")
```

### 4.3 Weight Tuning

```yaml
# Tuning based on query type:

query_type: "Keyword-heavy"
  # "GPA 2.0", "deadline 15/9", "section 3.2"
  weights: [0.4, 0.6]  # More BM25 weight

query_type: "Semantic"
  # "What are the requirements?"
  weights: [0.7, 0.3]  # More semantic weight

query_type: "Balanced"
  # Most common case
  weights: [0.6, 0.4]  # Balanced (RECOMMENDED)
```

---

## 5. Retrieval Ranking & Re-ranking

### 5.1 Simple Ranking

```python
# After retrieval, already sorted by score
docs = retriever.get_relevant_documents(query)

# Already ranked best-first:
# Doc1: score 0.92
# Doc2: score 0.87
# Doc3: score 0.75
# Doc4: score 0.68
# Doc5: score 0.45
```

### 5.2 Re-ranking (Advanced)

**Problem:** Top-K from similarity might still not be perfect
- Sometimes irrelevant doc has high score (false positive)
- Sometimes relevant doc ranked lower (false negative)

**Solution:** Re-rank using LLM

```python
def rerank_documents(query, docs, llm, top_k=3):
    """Use LLM to judge relevance and re-rank"""
    
    # Create scoring prompt
    prompt = f"""
    Given the query: "{query}"
    
    Rate each document's relevance (0-10):
    
    {''.join([
        f"Doc {i+1}: {doc.page_content[:200]}..."
        + "\nRelevance score: ___\n\n"
        for i, doc in enumerate(docs[:top_k])
    ])}
    
    Output format: "Doc1: 8, Doc2: 6, Doc3: 9"
    """
    
    # LLM scores each doc
    response = llm(prompt)
    
    # Parse scores and re-rank
    scores = parse_response(response)
    # ...
    
    return reranked_docs
```

❌ **Trade-off:** Extra LLM call = slower
✅ **Benefit:** More accurate ranking

**For DỰ ÁN:** Skip re-ranking initially, add if needed

---

## 6. Handling Edge Cases

### 6.1 No Relevant Documents Found

```python
def retrieve_with_fallback(query, retriever, threshold=0.5):
    """Retrieve with confidence threshold"""
    
    docs = retriever.get_relevant_documents(query)
    
    # Filter by relevance threshold
    relevant_docs = [
        doc for doc in docs 
        if doc.metadata.get("score", 0) > threshold
    ]
    
    if not relevant_docs:
        # Fallback 1: Lower threshold
        relevant_docs = docs[:3]
        
        if not relevant_docs:
            # Fallback 2: Return empty with info
            return {
                "docs": [],
                "message": "No relevant documents found",
                "suggestion": "Try different keywords"
            }
    
    return relevant_docs
```

### 6.2 Too Many Results (Redundancy)

```python
def deduplicate_docs(docs, threshold=0.9):
    """Remove duplicate/very similar docs"""
    
    unique_docs = []
    for doc in docs:
        is_duplicate = False
        for unique_doc in unique_docs:
            # Compare similarity
            sim = cosine_similarity(
                doc.metadata["embedding"],
                unique_doc.metadata["embedding"]
            )
            if sim > threshold:
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_docs.append(doc)
    
    return unique_docs
```

### 6.3 Cross-Language Retrieval

```python
def retrieve_multilingual(query, multilingual_retriever):
    """Retriever already handles multilingual via embeddings"""
    
    # Query in Vietnamese
    query_vi = "Học phí bao nhiêu?"
    docs = multilingual_retriever.get_relevant_documents(query_vi)
    
    # Results include both Vietnamese & English docs
    # LLM will generate answer in Vietnamese ✓
    
    return docs
```

---

## 7. Retrieval Metrics

### 7.1 Metrics to Track

```python
import numpy as np

class RetrievalMetrics:
    def __init__(self, retrieved_docs, relevant_docs):
        self.retrieved = set(d.metadata["id"] for d in retrieved_docs)
        self.relevant = set(d.metadata["id"] for d in relevant_docs)
    
    def precision(self):
        """What % of retrieved docs are relevant?"""
        if not self.retrieved:
            return 0
        true_positives = len(self.retrieved & self.relevant)
        return true_positives / len(self.retrieved)
    
    def recall(self):
        """What % of relevant docs did we retrieve?"""
        if not self.relevant:
            return 0
        true_positives = len(self.retrieved & self.relevant)
        return true_positives / len(self.relevant)
    
    def f1_score(self):
        """Harmonic mean of precision & recall"""
        p = self.precision()
        r = self.recall()
        if p + r == 0:
            return 0
        return 2 * (p * r) / (p + r)
    
    def mrr(self):
        """Mean Reciprocal Rank: position of first relevant doc"""
        for i, doc in enumerate(self.retrieved, 1):
            if doc in self.relevant:
                return 1.0 / i
        return 0
```

### 7.2 Target Metrics

```yaml
retrieval_performance:
  precision: "> 0.8"      # 80% of retrieved docs relevant
  recall: "> 0.7"         # Retrieve 70% of relevant docs
  f1_score: "> 0.75"      # Good balance
  mrr: "> 0.8"            # First result usually relevant
  latency: "< 500ms"      # Fast response
```

---

## 8. Testing Retrieval

### 8.1 Manual Test Cases

```python
# Test cases with expected relevant docs

test_cases = [
    {
        "query": "Học phí năm nhất?"
        "expected_sources": ["regulations_2024.pdf", "tuition.txt"],
        "expected_keywords": ["học phí", "năm nhất", "9 triệu"]
    },
    {
        "query": "GPA requirement là gì?",
        "expected_sources": ["academic_policy.pdf"],
        "expected_keywords": ["GPA", "2.0", "academic"]
    },
    {
        "query": "Deferment policy",
        "expected_sources": ["handbook.pdf"],
        "expected_keywords": ["defer", "study", "postpone"]
    }
]

# Run tests
def test_retrieval(retriever, test_cases):
    for test in test_cases:
        query = test["query"]
        docs = retriever.get_relevant_documents(query)
        
        # Check if expected sources found
        found_sources = set(
            doc.metadata["source"] for doc in docs
        )
        expected = set(test["expected_sources"])
        
        passed = expected.issubset(found_sources)
        print(f"Query: {query}")
        print(f"  ✓ PASS" if passed else f"  ✗ FAIL")
        print(f"  Found: {found_sources}")
        print(f"  Expected: {expected}\n")
```

---

## 9. Complete Retriever Class

```python
# src/retrieval/retriever.py

from langchain.retrievers import EnsembleRetriever, BM25Retriever
from langchain.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

class HybridRetriever:
    def __init__(self, kb_path="./data/chroma", top_k=5):
        self.top_k = top_k
        
        # Semantic retriever
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/distiluse-base-multilingual-cased-v2"
        )
        self.vectorstore = Chroma(
            persist_directory=kb_path,
            embedding_function=self.embeddings,
            collection_name="regulations"
        )
        self.semantic_retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": top_k}
        )
        
        # BM25 retriever
        documents = self.vectorstore.get()  # Load all docs
        self.bm25_retriever = BM25Retriever.from_documents(documents)
        self.bm25_retriever.k = top_k
        
        # Ensemble
        self.retriever = EnsembleRetriever(
            retrievers=[self.semantic_retriever, self.bm25_retriever],
            weights=[0.6, 0.4]
        )
    
    def retrieve(self, query):
        """Retrieve relevant documents"""
        docs = self.retriever.get_relevant_documents(query)
        return docs
    
    def retrieve_with_scores(self, query):
        """Retrieve with relevance scores"""
        docs_with_scores = self.vectorstore.similarity_search_with_score(
            query, k=self.top_k
        )
        return docs_with_scores
```

---

## Summary 📝

| Method | What | Speed | Accuracy | When |
|--------|------|-------|----------|------|
| **Semantic** | Meaning matching | ⚡ Medium | 🎯 High | General Q |
| **BM25** | Keyword matching | ⚡⚡ Fast | 🎯 High | Specific Q |
| **Hybrid** | Both combined | ⚡ Medium | 🎯 Highest | BEST ✓ |
| **Re-ranking** | LLM judges | Slow | Excellent | If needed |

---

## Next Steps

🔗 **Related Files:**
- `04-System-Architecture.md` - Where retriever fits in system
- `06-Data-Preparation-Guide.md` - How KB is prepared
- `08-Agent-Design.md` - How agent uses retriever
