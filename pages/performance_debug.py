"""
Performance Debug Page - Streamlit page để xem performance metrics chi tiết
Sử dụng multipage Streamlit để tạo tab Performance Analyzer
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import json
from pathlib import Path


def render_performance_debug():
    """Render performance debug page"""
    st.set_page_config(page_title="⏱️ Performance Analyzer", layout="wide")
    
    st.title("⏱️ Performance Analyzer - Bottleneck Detector")
    st.markdown("---")
    
    # ---- Thông tin cơ bản ----
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Log File", "logs/chatbot.log")
    with col2:
        st.metric("🔍 Last Updated", datetime.now().strftime("%H:%M:%S"))
    with col3:
        st.metric("📈 Status", "Monitor Active")
    
    st.markdown("---")
    
    # ---- Tabs ----
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📋 How to Debug", "📊 Sample Report", "🔍 Live Logs", "⚙️ Config"]
    )
    
    with tab1:
        st.markdown("""
## 🎯 Cách Sử Dụng Performance Logger
        
### 1️⃣ Trong Streamlit App
Mỗi câu hỏi bạn nhập, hệ thống sẽ **tự động track** thời gian:

```python
# Trong orchestrator.py
perf_tracker = PerformanceTracker(question)
with perf_tracker.track("Step Name", {"detail": value}):
    # Code ở đây được track
    result = some_operation()
perf_tracker.log_summary()  # In report chi tiết
```

### 2️⃣ Xem Logs
Tất cả performance metrics được ghi vào:
- **logs/chatbot.log** - Log chính
- **logs/pipeline_run.log** - Pipeline logs

### 3️⃣ Hiểu Performance Report

Một report điển hình trông như thế này:

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
```

### 4️⃣ Identify Bottleneck

📌 **Rule of Thumb:**
- **LLM Generation > 50%** → Ollama/Mistral chậm, cần optimize LLM config
- **Vector Search > 30%** → Embedding/Chroma slow, check embedding model or DB size
- **Context Building > 20%** → Quá nhiều documents, reduce top_k
- **Total > 60 seconds** → Timeout issue, check LLM server status

### 5️⃣ Các Metrics Chính

| Metric | Yêu cầu | Hiện tại |
|--------|---------|---------|
| **Total Time** | < 5s | 3.2s ✅ |
| **LLM Time** | < 3s | 2.1s |
| **Vector Search** | < 1s | 0.78s ✅ |
| **Memory Usage** | - | Monitor |

### 6️⃣ Optimization Tips

**Nếu LLM chậm:**
- ⬇️ Reduce `llm.top_k` trong config
- 🧠 Use faster model (Phi thay vì Mistral)
- 💾 Increase Ollama context window

**Nếu Vector Search chậm:**
- ⬇️ Reduce `retrieval.top_k`
- 📦 Rebuild Chroma DB
- 🔍 Check Chroma collection size

**Nếu Context Building chậm:**
- ⬇️ Reduce `top_k` returned
- 📝 Reduce `chunk_size` để chunks nhỏ hơn

        """)
    
    with tab2:
        st.markdown("### 📊 Sample Performance Report")
        
        sample_report = """
```
================================================================================
📊 PERFORMANCE REPORT - Query: 'Sinh viên được phép học lại môn học không?'
================================================================================
⏱️  TOTAL TIME: 3421ms (3.4s)

Step Name                                    Duration          %
------------------------------------------------------------
LLM Answer Generation                        2314ms        67.6%
Vector Similarity Search                     845ms         24.7%
Build Context                                178ms          5.2%
Confidence Calculation                       84ms           2.5%
------------------------------------------------------------
TOTAL                                        3421ms       100.0%
================================================================================

🔄 REACT ITERATIONS SUMMARY
================================================================================

Iteration 1: 845ms
  • Retrieve — {'docs_found': 3}

Iteration 2: 2484ms
  • GenerateAnswer — {'answer_len': 487}

================================================================================
Total ReACT time: 3329ms (3.3s)
Number of iterations: 2
Avg time per iteration: 1664ms
================================================================================
```

### 🔍 Phân Tích:
- **LLM dominates** (67.6%) → Mistral 7B inference mất nhiều thời gian nhất
- **Vector search fast** (24.7%) → Chroma DB performance tốt
- **Total 3.4s acceptable** nhưng có thể optimize LLM
        """
        st.code(sample_report, language="markdown")
    
    with tab3:
        st.markdown("### 🔍 Real-time Log Viewer")
        
        log_file = Path("logs/chatbot.log")
        if log_file.exists():
            # Read last N lines
            with open(log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Filter performance-related lines
            perf_lines = [l for l in lines if any(x in l for x in ["TOTAL TIME", "ms", "PERFORMANCE", "Slowest"])]
            
            if perf_lines:
                st.success(f"Found {len(perf_lines)} performance entries")
                
                # Show last 50 lines
                st.code("\n".join(perf_lines[-50:]), language="log")
            else:
                st.info("No performance logs yet. Ask a question to generate logs.")
        else:
            st.warning("Log file not found. Check logs/chatbot.log path.")
    
    with tab4:
        st.markdown("### ⚙️ Current Configuration")
        
        config_file = Path("config.yaml")
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                import yaml
                config = yaml.safe_load(f)
            
            st.json({
                "Agent Config": {
                    "max_iterations": config.get("agent", {}).get("max_iterations"),
                    "confidence_threshold": config.get("agent", {}).get("confidence_threshold"),
                },
                "LLM Config": {
                    "model": config.get("llm", {}).get("model_name"),
                    "temperature": config.get("llm", {}).get("temperature"),
                    "timeout": config.get("llm", {}).get("timeout_seconds"),
                },
                "Retrieval Config": {
                    "top_k": config.get("retrieval", {}).get("top_k"),
                    "similarity_threshold": config.get("retrieval", {}).get("similarity_threshold"),
                },
                "Embedding Config": {
                    "model": config.get("embedding", {}).get("model_name"),
                    "dimension": config.get("embedding", {}).get("dimension"),
                },
                "Chunking Config": {
                    "chunk_size": config.get("chunking", {}).get("chunk_size"),
                    "chunk_overlap": config.get("chunking", {}).get("chunk_overlap"),
                }
            })
    
    # ---- Footer ----
    st.markdown("---")
    st.markdown("""
### 📚 Key Files for Performance:
- `src/utils/performance.py` - Performance tracker implementation
- `src/agent/orchestrator.py` - Main agent with performance tracking
- `logs/chatbot.log` - Detailed logs with timings
    """)


if __name__ == "__main__":
    render_performance_debug()
