# ⏱️ Performance Tracking & Debugging Guide

## 📊 Tổng Quan

Hệ thống AgenticRAG bây giờ có **performance tracking tự động** để giúp bạn:
- ✅ Identify bottleneck trong inference pipeline
- ✅ Track từng step của ReACT reasoning
- ✅ Measure LLM latency, vector search time, etc.
- ✅ Optimize configuration dựa trên metrics

---

## 🎯 Quick Start

### 1️⃣ Automatic Logging

**Mỗi lần bạn nhập câu hỏi**, performance tracker tự động:

```
1. Track thời gian vector similarity search
2. Track thời gian LLM generation
3. Track confidence calculation
4. Log chi tiết breakdown
```

Không cần cấu hình gì cả - nó chạy tự động!

### 2️⃣ Xem Performance Report

Tất cả logs được lưu vào: **`logs/chatbot.log`**

```bash
# On Windows PowerShell
Get-Content -Path logs/chatbot.log -Wait -Tail 100

# On Linux/Mac
tail -f logs/chatbot.log
```

### 3️⃣ CLI Performance Test

Run test từ command line:

```bash
# Test with default questions
python scripts/test_performance.py

# Test with custom question
python scripts/test_performance.py "Có được học lại không?" "Quy chế tính điểm?"

# Results saved to logs/perf_test_YYYYMMDD_HHMMSS.json
```

---

## 📋 Understanding Performance Report

### Sample Report

```
================================================================================
📊 PERFORMANCE REPORT - Query: 'Có được học lại môn học không?'
================================================================================
⏱️  TOTAL TIME: 3234ms (3.2s)

Step Name                                    Duration          %
------------------------------------------------------------
LLM Answer Generation                        2150ms        66.4%
Vector Similarity Search                     780ms         24.1%
Build Context                                204ms          6.3%
Confidence Calculation                       100ms          3.1%
------------------------------------------------------------
TOTAL                                        3234ms       100.0%
================================================================================

🔄 REACT ITERATIONS SUMMARY
================================================================================

Iteration 1: 780ms
  • Retrieve — {'docs_found': 3}

Iteration 2: 2154ms
  • GenerateAnswer — {'answer_len': 487}

================================================================================
Total ReACT time: 2934ms (2.9s)
Number of iterations: 2
Avg time per iteration: 1467ms
================================================================================
```

### Key Metrics

| Metric | Meaning | Typical Range |
|--------|---------|---------------|
| **TOTAL TIME** | Total inference time | 2-5 seconds |
| **LLM Answer Generation** | LLM call latency (Ollama Mistral) | 1-3 seconds |
| **Vector Similarity Search** | Chroma DB search time | 0.5-1 second |
| **Build Context** | Creating context from documents | 100-500ms |
| **Confidence Calculation** | Scoring algorithm | 50-200ms |

---

## 🔍 Identify Bottlenecks

### Rule of Thumb

```
📌 LLM > 70% of total → Mistral inference is the bottleneck
📌 Vector Search > 40% → Embedding or Chroma is slow
📌 Context Building > 15% → Too many documents, reduce top_k
📌 Total > 60 seconds → Critical issue, check LLM server
```

### Case Analysis

#### Case 1: LLM is Slow (70%+ of total)
```
✅ Normal: LLM + embeddings on CPU = slow
✅ Solution options:
  1. Use faster model (Phi-2 instead of Mistral 7B)
  2. Reduce context length (less documents)
  3. Use GPU if available
  4. Increase Ollama memory allocation
```

#### Case 2: Vector Search is Slow (40%+ of total)
```
⚠️  Problem: Chroma search taking too long
✅ Solution options:
  1. Reduce retrieval.top_k (3 → 1 or 2)
  2. Increase similarity_threshold to filter faster
  3. Rebuild Chroma DB (might be corrupted)
  4. Check collection size: select count(*) from documents
```

#### Case 3: Context Building is Slow (15%+ of total)
```
⚠️  Problem: Too many documents or large chunks
✅ Solution options:
  1. Reduce retrieval.top_k
  2. Reduce chunk_size (1000 → 500 tokens)
  3. Reduce chunk_overlap
```

---

## ⚙️ Configuration Optimization

### config.yaml Performance-Related Settings

```yaml
agent:
  max_iterations: 5           # Max ReACT loops (more = slower)
  confidence_threshold: 0.75  # Higher = fewer iterations

retrieval:
  top_k: 3                    # Number of docs to retrieve
  similarity_threshold: 0.5   # Filter threshold (higher = fewer docs)

llm:
  model_name: mistral         # LLM model
  temperature: 0.3            # Lower = more deterministic (slight speedup)
  timeout_seconds: 60         # Max LLM call time

chunking:
  chunk_size: 1000            # Token size per chunk
  chunk_overlap: 200          # Overlap between chunks
```

### Performance Tuning Tips

#### ⚡ For Speed (Fastest)
```yaml
agent:
  max_iterations: 2
  confidence_threshold: 0.8

retrieval:
  top_k: 1
  similarity_threshold: 0.6

llm:
  temperature: 0.2

chunking:
  chunk_size: 500
  chunk_overlap: 50
```

#### 🎯 Balanced (Current)
```yaml
agent:
  max_iterations: 5
  confidence_threshold: 0.75

retrieval:
  top_k: 3
  similarity_threshold: 0.5

llm:
  temperature: 0.3

chunking:
  chunk_size: 1000
  chunk_overlap: 200
```

#### 🎓 For Accuracy (Slower)
```yaml
agent:
  max_iterations: 5
  confidence_threshold: 0.6

retrieval:
  top_k: 5
  similarity_threshold: 0.3

llm:
  temperature: 0.5

chunking:
  chunk_size: 1500
  chunk_overlap: 300
```

---

## 🖥️ Performance Debugging Page

Access the performance debug page in Streamlit:

```bash
streamlit run app.py
# Then click "⏱️ Performance Analyzer" in sidebar (if multipage setup)
# OR visit: pages/performance_debug.py
```

The page includes:
- ✅ How-to guide for debugging
- ✅ Sample performance reports
- ✅ Live log viewer
- ✅ Current configuration display

---

## 📊 Understanding Log Files

### Main Log File
Location: `logs/chatbot.log`

Contains:
- Startup messages
- Query processing logs
- **Performance metrics (with ⏱️ TOTAL TIME)**
- Error messages

### Finding Performance Data
```bash
# Show all performance reports
grep "TOTAL TIME" logs/chatbot.log

# Show 10 slowest queries
grep "⏱️  TOTAL TIME" logs/chatbot.log | sort -t: -k2 -rn | head -10

# Watch real-time
Get-Content -Path logs/chatbot.log -Wait -Tail 50
```

---

## 🚀 Performance Targets

### Goal Latency
- **Ideal**: 2-3 seconds per query
- **Acceptable**: 3-5 seconds
- **Warning**: 5-10 seconds (needs optimization)
- **Critical**: > 10 seconds (check LLM server)

### Benchmark Results

Current setup (Mistral 7B on CPU):
```
Question Type           Avg Time    Status
-------------------------------------------
Simple queries          2-3 sec     ✅ Good
Complex queries         3-5 sec     ✅ Acceptable
Edge cases             5-8 sec     ⚠️  Slow
```

---

## 🔧 Troubleshooting

### Problem: All queries taking 60+ seconds
**Likely cause**: Ollama LLM server not responding

**Solution**:
```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Restart Ollama
docker-compose restart ollama-service

# Or if not in Docker:
ollama serve
```

### Problem: Random slow queries
**Likely cause**: LLM model loading into memory

**Solution**:
```bash
# Preload model
ollama pull mistral

# Increase Ollama memory limit
# In docker-compose.yml: environment: OLLAMA_NUM_PARALLEL=2
```

### Problem: Vector search very slow (>2s)
**Likely cause**: Chroma DB corruption or too many embeddings

**Solution**:
```bash
# Rebuild vector DB
python scripts/reset_vector_db.py
python scripts/build_knowledge_base.py
```

---

## 📈 Monitoring in Production

For production monitoring, save performance data:

```bash
# Run test suite daily
python scripts/test_performance.py "Test Q1" "Test Q2" "Test Q3"

# Results auto-saved to: logs/perf_test_YYYYMMDD_HHMMSS.json
```

Parse JSON results:
```python
import json

with open("logs/perf_test_20240604_120000.json") as f:
    results = json.load(f)

avg_time = sum(r["total_time_ms"] for r in results) / len(results)
print(f"Average response time: {avg_time:.0f}ms")
```

---

## 🎯 Implementation Details

### Files Involved

| File | Purpose |
|------|---------|
| `src/utils/performance.py` | PerformanceTracker implementation |
| `src/agent/orchestrator.py` | Main agent with tracking integration |
| `scripts/test_performance.py` | CLI performance test script |
| `pages/performance_debug.py` | Streamlit debug page |
| `logs/chatbot.log` | Main log file with metrics |

### How Performance Tracking Works

```python
# In orchestrator.py
def answer_question(self, question):
    perf_tracker = PerformanceTracker(question)
    
    # Each operation is tracked
    with perf_tracker.track("Vector Search", {"k": 3}):
        results = self.retrieve(question)
    
    with perf_tracker.track("LLM Generation", {"len": len(context)}):
        answer = self.llm.invoke(prompt)
    
    # Summary automatically logged
    perf_tracker.log_summary()
```

---

## ✅ Next Steps

1. **Run your first test**: `python scripts/test_performance.py "Your question"`
2. **Check logs**: `Get-Content logs/chatbot.log -Tail 100`
3. **Identify bottleneck**: Look at % breakdown
4. **Optimize**: Adjust config.yaml based on findings
5. **Re-test**: Verify improvements

---

## 📚 References

- [Performance Report Sample](#sample-report)
- [Config Optimization Guide](#configuration-optimization)
- [Troubleshooting](#troubleshooting)
- [Implementation Details](#implementation-details)

---

**Happy Optimizing! 🚀**
