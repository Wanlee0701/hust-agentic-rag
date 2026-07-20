# 11. Deployment Guide - Local Setup & Docker

## 📚 Mục Tiêu
Master **deployment strategies** - how to run chatbot locally in development, production Docker setup, and scaling options.

---

## 1. Local Development Setup

### 1.1 Prerequisites

**System Requirements:**
- OS: Windows 10+, macOS 10.14+, or Linux (Ubuntu 20.04+)
- CPU: 4-core minimum (8-core recommended)
- RAM: 8GB minimum (16GB recommended)
- Disk: 20GB free space
- GPU: Optional but recommended (NVIDIA with CUDA 11.8+)

**Software:**
- Python 3.10+
- Git
- Docker (optional, for containerization)

### 1.2 Step-by-Step Local Setup

#### Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd chatbot-project
```

#### Step 2: Install Ollama

**Option A: Official Installer**
```bash
# Windows/macOS/Linux
# Visit: https://ollama.ai/download
# Download and run installer
# Verify:
ollama --version
```

**Option B: Docker**
```bash
docker pull ollama/ollama:latest
```

#### Step 3: Pull Mistral Model

```bash
ollama pull mistral

# Verify:
ollama list
# Output:
# NAME      ID              SIZE    MODIFIED
# mistral   ef0ede8fcd57    4.1 GB  2 minutes ago
```

Try LLM:
```bash
ollama run mistral "Hello"
# Should respond!

# Leave running:
ollama serve
# Runs on localhost:11434
```

#### Step 4: Create Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

#### Step 5: Install Dependencies

```bash
# Install packages
pip install -r requirements.txt

# Verify key packages:
python -c "import langchain; print(langchain.__version__)"
python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

**requirements.txt:**
```
langchain==0.1.0
ollama==0.1.0
streamlit==1.28.0
chromadb==0.4.0
sentence-transformers==2.2.2
pypdf2==3.0.0
pdfplumber==0.10.0
python-dotenv==1.0.0
pytest==7.4.0
```

#### Step 6: Prepare Knowledge Base

```bash
# Create KB folder structure
mkdir -p knowledge_base/raw
mkdir -p data/chroma
mkdir -p logs

# Copy your PDF files to knowledge_base/raw/
cp /path/to/*.pdf knowledge_base/raw/

# Run data preparation
python data_preparation.py
# Output:
# Step 1: Extracting PDFs...
#   Found 170 pages
# Step 2: Chunking...
#   Created 312 chunks
# Step 3: Testing vector store...
#   ✓ Vector store ready
```

#### Step 7: Run Chatbot

```bash
streamlit run app.py

# Output:
# You can now view your Streamlit app in your browser.
# Local URL: http://localhost:8501
# Network URL: http://192.168.x.x:8501
```

**Browser:**
- Open http://localhost:8501
- Start asking questions!

---

## 2. Docker Deployment

### 2.1 Dockerfile for Application

```dockerfile
# Dockerfile

FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/chroma logs

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run streamlit app
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 2.2 Docker Compose (Complete Stack)

```yaml
# docker-compose.yml

version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama-service
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_MODELS_PATH=/root/.ollama/models
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 10s
      timeout: 5s
      retries: 5
    command: serve
    restart: unless-stopped

  chatbot:
    build: .
    container_name: chatbot-app
    ports:
      - "8501:8501"
    volumes:
      - ./knowledge_base:/app/knowledge_base
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - LLM_SERVICE_URL=http://ollama:11434
      - PYTHONUNBUFFERED=1
    depends_on:
      ollama:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 5
    restart: unless-stopped
    links:
      - ollama

volumes:
  ollama_data:
    driver: local
```

### 2.3 Running with Docker Compose

```bash
# Build and start
docker-compose up --build

# In separate terminal, pull model:
docker exec ollama-service ollama pull mistral

# Prepare KB (from host):
python data_preparation.py
# Writes to ./data/chroma (mounted folder)

# Access at:
# http://localhost:8501

# Stop:
docker-compose down

# View logs:
docker-compose logs -f chatbot
docker-compose logs -f ollama
```

---

## 3. Configuration Files

### 3.1 .env File (Secrets & Config)

```bash
# .env
LLM_MODEL=mistral
LLM_SERVICE_URL=http://localhost:11434
LLM_TEMPERATURE=0.3

EMBEDDING_MODEL=sentence-transformers/distiluse-base-multilingual-cased-v2
CHROMA_PATH=./data/chroma

STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

LOG_LEVEL=INFO
LOG_FILE=./logs/chatbot.log

# Optional: Redis for caching
REDIS_URL=redis://localhost:6379
ENABLE_CACHING=true
```

### 3.2 config.yaml Production Settings

```yaml
# config.yaml

system:
  name: "Student Chatbot"
  version: "1.0.0"
  environment: "production"

llm:
  provider: "ollama"
  model_name: "mistral"
  base_url: "${LLM_SERVICE_URL}"
  temperature: 0.3
  max_tokens: 1024
  timeout_seconds: 30
  
embedding:
  model_name: "${EMBEDDING_MODEL}"
  cache_folder: "./models"
  batch_size: 32

vectordb:
  provider: "chroma"
  persist_directory: "${CHROMA_PATH}"

retrieval:
  top_k: 5
  semantic_weight: 0.6
  keyword_weight: 0.4
  similarity_threshold: 0.5

agent:
  max_iterations: 5
  confidence_threshold: 0.75

logging:
  level: "${LOG_LEVEL}"
  file: "${LOG_FILE}"
  max_size_mb: 100
  backup_count: 5

caching:
  enabled: "${ENABLE_CACHING}"
  ttl_seconds: 3600
```

---

## 4. Monitoring & Maintenance

### 4.1 Health Checks

```python
# health_check.py

import requests
import sys

def check_ollama():
    """Check if Ollama service is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except:
        return False

def check_vectordb():
    """Check if Chroma DB is initialized"""
    from chromadb import Client
    try:
        client = Client()
        client.list_collections()
        return True
    except:
        return False

def check_embeddings():
    """Check if embedding model loads"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(
            "sentence-transformers/distiluse-base-multilingual-cased-v2"
        )
        emb = model.encode("test")
        return len(emb) == 768
    except:
        return False

if __name__ == "__main__":
    checks = {
        "Ollama": check_ollama(),
        "VectorDB": check_vectordb(),
        "Embeddings": check_embeddings()
    }
    
    print("System Health Check:")
    for service, status in checks.items():
        print(f"  {service}: {'✓' if status else '✗'}")
    
    if all(checks.values()):
        print("\n✓ All systems operational")
        sys.exit(0)
    else:
        print("\n✗ Some systems down")
        sys.exit(1)
```

### 4.2 Logging Setup

```python
# logging_config.py

import logging
import logging.handlers
from pathlib import Path

def setup_logging(log_file="logs/chatbot.log", level=logging.INFO):
    """Setup logging configuration"""
    
    # Create logs directory
    Path(log_file).parent.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("chatbot")
    logger.setLevel(level)
    
    # File handler with rotation
    fh = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=100*1024*1024,  # 100MB
        backupCount=5
    )
    fh.setLevel(logging.DEBUG)
    
    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s'
    )
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(fh)
    logger.addHandler(ch)
    
    return logger

# Usage:
logger = setup_logging()
logger.info("Application started")
```

---

## 5. Scaling Options

### 5.1 Single Server (Current)
```
┌─────────────────────────────────────┐
│   Single Server/Container           │
├─────────────────────────────────────┤
│ ┌──────────────────────────────────┐│
│ │ Ollama (LLM Service)             ││
│ │ Port: 11434                      ││
│ └──────────────────────────────────┘│
│ ┌──────────────────────────────────┐│
│ │ Streamlit App                    ││
│ │ Port: 8501                       ││
│ │ Chroma DB (local)                ││
│ └──────────────────────────────────┘│
│                                     │
│ Capacity: ~10-20 concurrent users   │
│ Latency: ~2-5s per query            │
└─────────────────────────────────────┘
```

### 5.2 Multi-Container (Recommended for Production)
```yaml
# Scale Chroma separately:
version: '3.8'
services:
  ollama:
    # LLM service
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8000:8000"
  chatbot:
    # Connect to external services
    environment:
      - CHROMA_URL=http://chroma:8000
      - LLM_URL=http://ollama:11434
```

### 5.3 Future: Kubernetes Deployment

```yaml
# k8s-deployment.yaml (for future scaling)

apiVersion: apps/v1
kind: Deployment
metadata:
  name: chatbot-app
spec:
  replicas: 3  # 3 app instances
  selector:
    matchLabels:
      app: chatbot
  template:
    metadata:
      labels:
        app: chatbot
    spec:
      containers:
      - name: chatbot
        image: your-registry/chatbot:latest
        ports:
        - containerPort: 8501
        env:
        - name: LLM_SERVICE_URL
          value: http://ollama-service:11434
---
apiVersion: v1
kind: Service
metadata:
  name: chatbot-service
spec:
  selector:
    app: chatbot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8501
  type: LoadBalancer
```

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Solution |
|-------|----------|
| **Ollama not responding** | `ollama serve` in new terminal |
| **Model not downloaded** | `ollama pull mistral` |
| **Port already in use** | Change port in config or kill process |
| **Out of memory** | Reduce batch size, use smaller model |
| **Slow responses** | Add GPU support, increase VRAM |
| **Import errors** | `pip install -r requirements.txt` |
| **KB not loading** | Check `/data/chroma` folder permissions |

### 6.2 Debug Mode

```bash
# Enable verbose logging
export LOG_LEVEL=DEBUG
export STREAMLIT_LOGGER_LEVEL=debug

streamlit run app.py --logger.level=debug
```

---

## 7. Deployment Checklist

Before Production:

- [ ] Ollama service stable (test 100+ queries)
- [ ] Knowledge base indexed and retrievable
- [ ] Model responses quality checked
- [ ] Latency acceptable (<5s)
- [ ] Error handling working
- [ ] Logs being written correctly
- [ ] Health checks passing
- [ ] Security: no credentials in code
- [ ] SSL/TLS configured (if internet-facing)
- [ ] Backup strategy for KB defined

---

## 8. Monitoring Dashboard (Optional)

```python
# monitoring.py - Simple metrics dashboard

import streamlit as st
import pandas as pd
from datetime import datetime

def show_metrics():
    st.write("## System Metrics")
    
    # Load logs
    with open("logs/chatbot.log") as f:
        logs = f.readlines()
    
    # Parse metrics
    total_queries = len([l for l in logs if "Query processed" in l])
    avg_latency = calculate_avg_latency(logs)
    success_rate = calculate_success_rate(logs)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Queries", total_queries)
    col2.metric("Avg Latency (ms)", f"{avg_latency:.0f}")
    col3.metric("Success Rate", f"{success_rate:.1%}")
    
    # Time series
    query_timeline = extract_timeline(logs)
    st.line_chart(query_timeline)

if __name__ == "__main__":
    show_metrics()
```

---

## Summary 📝

| Deployment Type | Setup Time | Maintenance | Cost | Capacity |
|-----------------|-----------|-------------|------|----------|
| **Local Dev** | 30 min | Low | Free | 1-10 users |
| **Docker** | 45 min | Medium | Free | 10-50 users |
| **Docker Compose** | 1 hour | Medium | Free/Low | 50-100 users |
| **Kubernetes** | 3-5 hours | High | Medium | 100+ users |

**For DỰ ÁN START:** Docker Compose (easy, scalable)

---

## Next Steps

🔗 **Related Files:**
- `04-System-Architecture.md` - What to deploy
- `06-Data-Preparation-Guide.md` - Prepare KB before deploy
