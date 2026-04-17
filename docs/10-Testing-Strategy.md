# 10. Testing Strategy - How to Test Everything

## 📚 Mục Tiêu
Master **testing strategy** for each component - unit tests, integration tests, manual QA, and evaluation metrics.

---

## 1. Testing Pyramid

### 1.1 Test Hierarchy (What to Test)

```
                    ▲
                   / \
                  /   \
                 / E2E  \
                /Tests  \       System-level
               /─────────\     (Few tests, slow)
              /  /   \    \
             /__/     \    \
            / Integration  \   Component-level
           /___Tests________\  (Medium tests)
          /         \        \
         /           \        \
        /    Unit     \        \
       /    Tests     \        \
      /___/__/__/__/__\\  (Many tests, fast)
```

**For DỰ ÁN:**
- **Unit Tests:** Each component independently
- **Integration Tests:** Components working together
- **E2E Tests:** Full query → answer pipeline
- **Manual QA:** Real-world queries

---

## 2. Unit Tests by Component

### 2.1 Embedding Component Tests

```python
# test_embeddings.py
import pytest
from sentence_transformers import SentenceTransformer

class TestEmbeddings:
    @pytest.fixture
    def model(self):
        return SentenceTransformer(
            "sentence-transformers/distiluse-base-multilingual-cased-v2"
        )
    
    def test_embedding_dimension(self, model):
        """Embeddings have correct dimension"""
        text = "Học phí bao nhiêu?"
        embedding = model.encode(text)
        assert len(embedding) == 768
    
    def test_multilingual_similarity(self, model):
        """Vietnamese and English similar text have high similarity"""
        vi_text = "Học phí năm nhất"
        en_text = "First year tuition"
        
        vi_emb = model.encode(vi_text)
        en_emb = model.encode(en_text)
        
        # Cosine similarity
        similarity = cosine_sim(vi_emb, en_emb)
        assert similarity > 0.85  # Should be similar
    
    def test_different_meaning_dissimilar(self, model):
        """Different meanings have low similarity"""
        text1 = "Học phí"
        text2 = "Thời tiết hôm nay"
        
        emb1 = model.encode(text1)
        emb2 = model.encode(text2)
        
        similarity = cosine_sim(emb1, emb2)
        assert similarity < 0.5  # Should be different
    
    def test_same_text_high_similarity(self, model):
        """Same text has very high similarity"""
        text = "Học phí năm nhất là bao nhiêu?"
        
        emb1 = model.encode(text)
        emb2 = model.encode(text)
        
        similarity = cosine_sim(emb1, emb2)
        assert similarity > 0.99  # Should be almost identical
```

### 2.2 Retriever Component Tests

```python
# test_retriever.py
import pytest
from src.retrieval.retriever import HybridRetriever

class TestRetriever:
    @pytest.fixture
    def retriever(self):
        return HybridRetriever(kb_path="./data/chroma")
    
    def test_retrieve_returns_documents(self, retriever):
        """Retriever returns documents"""
        query = "Học phí năm nhất bao nhiêu?"
        docs = retriever.retrieve(query)
        
        assert len(docs) > 0
        assert all(hasattr(doc, 'page_content') for doc in docs)
    
    def test_retrieve_top_k(self, retriever):
        """Retriever returns exactly top_k results"""
        query = "Quy chế"
        docs = retriever.retrieve(query)
        
        assert len(docs) <= 5  # Default top_k
    
    def test_retrieve_relevant_documents(self, retriever):
        """Retrieved documents are relevant to query"""
        query = "Tuition fee first year"
        docs = retriever.retrieve(query)
        
        # Check if docs contain relevant keywords
        keywords = ["tuition", "fee", "year", "student"]
        doc_text = "\n".join(d.page_content for d in docs)
        
        matches = sum(1 for kw in keywords if kw.lower() in doc_text.lower())
        assert matches >= 1  # At least one keyword present
    
    def test_retrieve_vietnamese_query(self, retriever):
        """Retriever handles Vietnamese queries"""
        query = "Học phí"
        docs = retriever.retrieve(query)
        
        assert len(docs) > 0  # Should find results
    
    def test_retrieve_english_query(self, retriever):
        """Retriever handles English queries"""
        query = "Tuition"
        docs = retriever.retrieve(query)
        
        assert len(docs) > 0  # Should find results
    
    def test_retrieve_mixed_language(self, retriever):
        """Retriever handles mixed language queries"""
        query = "Tuition fee học phí"
        docs = retriever.retrieve(query)
        
        assert len(docs) > 0  # Should find results (CLIR works)
```

### 2.3 Agent Component Tests

```python
# test_agent.py
import pytest
from src.agent.orchestrator import StudentChatbotAgent

class TestAgent:
    @pytest.fixture
    def agent(self):
        return StudentChatbotAgent()
    
    def test_agent_answers_question(self, agent):
        """Agent can answer a question"""
        query = "Học phí bao nhiêu?"
        result = agent.answer_question(query)
        
        assert result['success'] == True
        assert len(result['answer']) > 0
    
    def test_agent_provides_sources(self, agent):
        """Agent cites sources in answer"""
        query = "Quy chế gì?"
        result = agent.answer_question(query)
        
        # Check if sources mentioned
        # (Would depend on your format, example)
        assert "regulations" in result.get('sources', []) or \
               result['answer'] != ""  # At least answered
    
    def test_agent_handles_no_results(self, agent):
        """Agent gracefully handles when no docs found"""
        query = "Tôi có thể đi du lịch đến sao Hỏa không?"
        result = agent.answer_question(query)
        
        # Should indicate lack of info (not hallucinate)
        assert "don't know" in result['answer'].lower() or \
               "not found" in result['answer'].lower() or \
               result['success'] == False
    
    def test_agent_respects_max_iterations(self, agent):
        """Agent respects max iteration limit"""
        # This test would track agent state
        query = "Complex multi-part question..."
        result = agent.answer_question(query)
        
        # Agent state info (if logged)
        # assert result['iterations'] <= 5
```

---

## 3. Integration Tests

### 3.1 End-to-End Pipeline Test

```python
# test_e2e.py
import pytest
from src.main import ChatbotService

class TestE2E:
    @pytest.fixture
    def chatbot(self):
        return ChatbotService()
    
    def test_full_pipeline_simple_question(self, chatbot):
        """Full pipeline: query → retrieval → answer"""
        query = "Học phí năm nhất bao nhiêu?"
        
        response = chatbot.process_query(query)
        
        assert response['success'] == True
        assert 'answer' in response
        assert len(response['answer']) > 10  # Reasonable answer length
        assert 'confidence' in response
        assert response['confidence'] > 0.5
    
    def test_full_pipeline_complex_question(self, chatbot):
        """Full pipeline: complex reasoning"""
        query = "Nếu tôi không đạt GPA 2.0, có thể hoãn học không?"
        
        response = chatbot.process_query(query)
        
        assert response['success'] == True
        assert len(response['answer']) > 20  # Longer answer for complex
    
    def test_multilingual_support(self, chatbot):
        """Vietnamese → answer in Vietnamese"""
        vi_query = "Còn được học lại được không?"
        vi_response = chatbot.process_query(vi_query, language="vi")
        
        # Check Vietnamese in response
        vietnamese_chars = any(
            '\u0100' <= char <= '\u01EF' 
            for char in vi_response['answer']  # Vietnamese Unicode range
        )
        assert vietnamese_chars
    
    def test_english_support(self, chatbot):
        """English query → answer in English"""
        en_query = "Can I retake a course?"
        en_response = chatbot.process_query(en_query, language="en")
        
        assert len(en_response['answer']) > 0
    
    def test_latency_acceptable(self, chatbot):
        """Response time within acceptable range"""
        import time
        
        query = "Học phí?"
        start = time.time()
        response = chatbot.process_query(query)
        latency = time.time() - start
        
        assert latency < 5.0  # 5 seconds max
        assert latency > 0.1  # At least 100ms (sanity check)
    
    def test_consistency(self, chatbot):
        """Same query returns consistent answers"""
        query = "Học phí bao nhiêu?"
        
        response1 = chatbot.process_query(query)
        response2 = chatbot.process_query(query)
        
        # Should be similar (not byte-identical due to LLM variability)
        assert response1['confidence'] > 0.5
        assert response2['confidence'] > 0.5
        # Both should mention similar facts (tuition amount, etc.)
```

---

## 4. Manual QA Test Cases

### 4.1 Test Cases Template

```python
qa_test_cases = [
    # Category: Tuition
    {
        "id": "T001",
        "category": "Tuition",
        "query": "Học phí năm nhất bao nhiêu?",
        "expected_keywords": ["8 triệu", "tuition", "million"],
        "expected_source": "regulations.pdf",
        "difficulty": "easy",
        "priority": "high"
    },
    {
        "id": "T002",
        "category": "Tuition",
        "query": "Khi nào phải thanh toán học phí?",
        "expected_keywords": ["September", "15", "deadline"],
        "expected_source": "tuition_policy.txt",
        "difficulty": "easy",
        "priority": "high"
    },
    
    # Category: Academic
    {
        "id": "A001",
        "category": "Academic",
        "query": "Còn được học lại được không nếu fail?",
        "expected_keywords": ["retake", "fail", "repeat"],
        "expected_source": "academic_regulation.pdf",
        "difficulty": "medium",
        "priority": "high"
    },
    
    # Category: Multi-step
    {
        "id": "M001",
        "category": "Multi-step",
        "query": "Nếu GPA dưới 2.0, có thể hoãn học và sau đó học lại không?",
        "expected_keywords": ["deferment", "retake", "GPA"],
        "difficulty": "hard",
        "priority": "medium"
    }
]

def run_manual_qa(chatbot, test_cases):
    """Run manual QA and collect results"""
    results = []
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"Test ID: {test['id']}")
        print(f"Category: {test['category']}")
        print(f"Query: {test['query']}")
        print(f"Difficulty: {test['difficulty']}")
        print(f"'─'*60}")
        
        response = chatbot.process_query(test['query'])
        
        print(f"Answer: {response['answer']}")
        print(f"Confidence: {response['confidence']}")
        print(f"Sources: {response.get('sources', [])}")
        
        # Manual evaluation
        passed = input("Did answer satisfy requirements? (y/n): ").lower() == 'y'
        
        results.append({
            "test_id": test['id'],
            "query": test['query'],
            "passed": passed,
            "answer": response['answer'],
            "confidence": response['confidence']
        })
    
    return results
```

---

## 5. Evaluation Metrics

### 5.1 Retrieval Metrics

```python
from sklearn.metrics import precision_score, recall_score, f1_score

class RetrievalEvaluator:
    def evaluate(self, retrieved_docs, relevant_docs):
        """Evaluate retrieval quality"""
        
        # Convert to binary vectors
        retrieved_set = set(d.metadata['id'] for d in retrieved_docs)
        relevant_set = set(d.metadata['id'] for d in relevant_docs)
        
        true_positives = len(retrieved_set & relevant_set)
        false_positives = len(retrieved_set - relevant_set)
        false_negatives = len(relevant_set - retrieved_set)
        
        metrics = {
            "precision": true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0,
            "recall": true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0,
            "f1": 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0
        }
        
        return metrics
```

### 5.2 Answer Quality Metrics

```python
class AnswerEvaluator:
    def evaluate_answer(self, answer, reference_answer):
        """Evaluate answer quality using multiple metrics"""
        
        from nltk.translate.bleu_score import sentence_bleu
        from rouge_score import rouge_scorer
        
        # BLEU Score (matches n-grams)
        bleu = sentence_bleu(
            [reference_answer.split()],
            answer.split()
        )
        
        # ROUGE Score (recall-oriented)
        scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'])
        rouge = scorer.score(reference_answer, answer)
        
        return {
            "bleu": bleu,
            "rouge1": rouge['rouge1'].fmeasure,
            "rougeL": rouge['rougeL'].fmeasure,
            "length_match": len(answer.split()) / len(reference_answer.split())
        }
```

### 5.3 Overall System Metrics

```python
class SystemMetricsTracker:
    def __init__(self):
        self.queries = []
        self.latencies = []
        self.confidences = []
        self.successes = 0
        self.total = 0
    
    def log_query(self, query, latency_ms, confidence, success):
        self.queries.append(query)
        self.latencies.append(latency_ms)
        self.confidences.append(confidence)
        self.total += 1
        if success:
            self.successes += 1
    
    def get_stats(self):
        import statistics
        
        return {
            "total_queries": self.total,
            "success_rate": self.successes / self.total if self.total > 0 else 0,
            "avg_latency_ms": statistics.mean(self.latencies),
            "median_latency_ms": statistics.median(self.latencies),
            "avg_confidence": statistics.mean(self.confidences),
            "p95_latency_ms": sorted(self.latencies)[int(0.95 * len(self.latencies))]
        }
```

---

## 6. Continuous Testing

### 6.1 Regression Testing

```python
def run_regression_tests():
    """Ensure no regression with updates"""
    
    baseline_metrics = {
        "retrieval_f1": 0.82,
        "answer_quality": 0.85,
        "latency_p95": 4500,  # ms
        "success_rate": 0.95
    }
    
    current_metrics = run_full_test_suite()
    
    for metric_name, baseline_value in baseline_metrics.items():
        current_value = current_metrics[metric_name]
        
        # Allow 2% regression
        if current_value < baseline_value * 0.98:
            print(f"⚠️ REGRESSION: {metric_name}")
            print(f"   Baseline: {baseline_value}")
            print(f"   Current: {current_value}")
            return False
    
    print("✓ No regression detected")
    return True
```

---

## 7. Testing Checklist

Before Release:

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] 50+ manual QA test cases with >80% pass rate
- [ ] Retrieval metrics: F1 > 0.75
- [ ] Answer quality metrics: BLEU > 0.6
- [ ] Latency: Average < 3s, P95 < 5s
- [ ] No regression from baseline
- [ ] Vietnamese queries tested
- [ ] English queries tested
- [ ] Error handling tested
- [ ] Edge cases tested (no results, conflicting info, etc.)
- [ ] Multilingual support tested

---

## Summary 📝

| Test Level | What | When | Pass Rate Target |
|-----------|------|------|------------------|
| **Unit** | Components | Always | 100% |
| **Integration** | System end-to-end | Before release | 100% |
| **Manual QA** | Real-world cases | Release + periodically | >80% |
| **Metrics** | Performance | Continuous | Track trends |

---

## Next Steps

🔗 **Related Files:**
- `04-System-Architecture.md` - Components to test
- `11-Deployment-Guide.md` - Testing in production
