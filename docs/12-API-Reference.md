# 12. API Reference - Endpoints, Usage Examples, Integration

## 📚 Mục Tiêu
Complete **API documentation** - endpoints, request/response formats, examples, and how to integrate chatbot into other systems.

---

## 1. API Overview

### 1.1 Architecture
```
┌─────────────────┐
│  External App   │  (Student portal, mobile app, etc.)
│  or Frontend    │
└────────┬────────┘
         │ HTTP requests
         ▼
┌─────────────────────────────────────┐
│    API Server (FastAPI)             │
│    Port: 8000                       │
├─────────────────────────────────────┤
│ Routes:                             │
│ - POST /api/v1/chat                 │
│ - POST /api/v1/history              │
│ - GET /api/v1/health                │
│ - GET /api/v1/metrics               │
└────────────┬────────────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  Chatbot Logic  │
    │  (From main)    │
    └─────────────────┘
```

### 1.2 Environment Setup
```bash
# Install FastAPI
pip install fastapi uvicorn

# Create API wrapper
touch src/api/main.py
touch src/api/models.py
```

---

## 2. FastAPI Wrapper

### 2.1 Data Models

```python
# src/api/models.py

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ChatRequest(BaseModel):
    """Chat request model"""
    query: str
    session_id: Optional[str] = None
    language: Optional[str] = "auto"  # auto, vi, en
    include_sources: bool = True
    
    class Config:
        example = {
            "query": "Học phí năm nhất bao nhiêu?",
            "session_id": "session_abc123",
            "language": "vi",
            "include_sources": True
        }

class SourceReference(BaseModel):
    """Reference to source document"""
    document: str
    page: Optional[int] = None
    relevance_score: float
    excerpt: str

class ChatResponse(BaseModel):
    """Chat response model"""
    success: bool
    answer: str
    confidence: float
    query_language: str
    sources: List[SourceReference] = []
    iteration_count: int
    latency_ms: float
    timestamp: datetime
    
    class Config:
        example = {
            "success": True,
            "answer": "Học phí năm nhất là 8 triệu VND...",
            "confidence": 0.92,
            "query_language": "vi",
            "sources": [
                {
                    "document": "regulations.pdf",
                    "page": 12,
                    "relevance_score": 0.95,
                    "excerpt": "Học phí năm nhất: 8.000.000 VND"
                }
            ],
            "iteration_count": 2,
            "latency_ms": 2340.5,
            "timestamp": "2025-04-09T10:30:45Z"
        }

class ErrorResponse(BaseModel):
    """Error response"""
    success: bool = False
    error_code: str
    message: str
    details: Optional[dict] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str  # "healthy", "degraded", "unhealthy"
    timestamp: datetime
    services: dict  # {"ollama": True, "chroma": True, ...}
```

### 2.2 FastAPI Application

```python
# src/api/main.py

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import time
from datetime import datetime

from src.api.models import ChatRequest, ChatResponse, SourceReference, ErrorResponse, HealthResponse
from src.agent.orchestrator import StudentChatbotAgent
from src.retrieval.retriever import HybridRetriever

# Global instances (initialize once)
chatbot_agent = None
retriever = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management"""
    # Startup
    global chatbot_agent, retriever
    print("Initializing chatbot...")
    chatbot_agent = StudentChatbotAgent()
    retriever = HybridRetriever()
    print("✓ Chatbot ready")
    
    yield
    
    # Shutdown (cleanup if needed)
    print("Shutting down...")

app = FastAPI(
    title="Student Chatbot API",
    description="API for university regulation Q&A",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure based on security needs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# ENDPOINTS
# ================================================================

@app.get("/healthz", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint
    
    Returns: System status and component health
    """
    services_status = {
        "ollama": check_ollama(),
        "chroma": check_chroma(),
        "embeddings": check_embeddings()
    }
    
    overall_status = "healthy" if all(services_status.values()) else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(),
        services=services_status
    )

@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint - Process student query
    
    Args:
        request: ChatRequest with query and metadata
    
    Returns:
        ChatResponse with answer and sources
    
    Example:
        POST /api/v1/chat
        {
            "query": "Học phí năm nhất?",
            "session_id": "sess_123",
            "language": "vi"
        }
    """
    try:
        # Time the request
        start_time = time.time()
        
        # Process query
        result = chatbot_agent.answer_question(request.query)
        
        # Get sources if requested
        sources = []
        if request.include_sources:
            docs = retriever.retrieve(request.query)
            sources = [
                SourceReference(
                    document=doc.metadata.get('source', 'Unknown'),
                    page=doc.metadata.get('page'),
                    relevance_score=doc.metadata.get('score', 0.0),
                    excerpt=doc.page_content[:200]
                )
                for doc in docs[:3]  # Top 3 sources
            ]
        
        # Detect language
        from langdetect import detect
        try:
            query_lang = detect(request.query)
        except:
            query_lang = request.language or "unknown"
        
        latency_ms = (time.time() - start_time) * 1000
        
        return ChatResponse(
            success=result.get('success', True),
            answer=result.get('answer', 'Unable to process query'),
            confidence=result.get('confidence', 0.5),
            query_language=query_lang,
            sources=sources,
            iteration_count=result.get('iterations', 1),
            latency_ms=latency_ms,
            timestamp=datetime.now()
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}"
        )

@app.get("/api/v1/metrics")
async def get_metrics():
    """
    Get system metrics
    
    Returns: Performance and usage metrics
    """
    # Load from logs or database
    metrics = {
        "total_queries": 0,
        "success_rate": 0.0,
        "avg_latency_ms": 0.0,
        "uptime_hours": 0.0
    }
    # Populate metrics...
    return metrics

@app.post("/api/v1/feedback")
async def submit_feedback(feedback: dict):
    """
    Submit user feedback on answer quality
    
    Args:
        feedback: {
            "query": "...",
            "answer": "...",
            "rating": 1-5,
            "helpful": true/false,
            "notes": "..."
        }
    
    Returns: Acknowledgment
    """
    # Store feedback in database for iteration
    return {
        "success": True,
        "message": "Feedback recorded, thank you!"
    }

# ================================================================
# ERROR HANDLING
# ================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return ErrorResponse(
        error_code="INTERNAL_ERROR",
        message=str(exc),
        details={"type": exc.__class__.__name__}
    )

# ================================================================
# HELPER FUNCTIONS
# ================================================================

def check_ollama():
    """Check if Ollama service responsive"""
    import requests
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False

def check_chroma():
    """Check if Chroma DB accessible"""
    try:
        # Try to query one document
        retriever.retrieve("test")
        return True
    except:
        return False

def check_embeddings():
    """Check if embeddings model working"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(
            "sentence-transformers/distiluse-base-multilingual-cased-v2"
        )
        emb = model.encode("test")
        return len(emb) == 768
    except:
        return False
```

### 2.3 Running API Server

```bash
# Run FastAPI server
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Output:
# Uvicorn running on http://0.0.0.0:8000
# API docs: http://localhost:8000/docs
```

---

## 3. API Usage Examples

### 3.1 Python Client

```python
# examples/python_client.py

import requests
import json
from typing import Dict

class ChatbotClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def chat(self, query: str, language: str = "auto") -> Dict:
        """Send query to chatbot"""
        
        payload = {
            "query": query,
            "language": language,
            "include_sources": True
        }
        
        response = self.session.post(
            f"{self.base_url}/api/v1/chat",
            json=payload
        )
        
        response.raise_for_status()
        return response.json()
    
    def get_health(self) -> Dict:
        """Check system health"""
        response = self.session.get(f"{self.base_url}/healthz")
        response.raise_for_status()
        return response.json()

# Usage:
if __name__ == "__main__":
    client = ChatbotClient()
    
    # Check health
    health = client.get_health()
    print(f"System status: {health['status']}")
    
    # Ask question
    response = client.chat("Học phí bao nhiêu?", language="vi")
    
    print(f"Answer: {response['answer']}")
    print(f"Confidence: {response['confidence']}")
    print(f"Latency: {response['latency_ms']}ms")
    print(f"Sources:")
    for source in response['sources']:
        print(f"  - {source['document']} (page {source['page']})")
```

### 3.2 JavaScript/curl Examples

```bash
# Using curl

# Health check
curl http://localhost:8000/healthz

# Chat endpoint
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Học phí năm nhất bao nhiêu?",
    "language": "vi",
    "include_sources": true
  }'

# Response:
# {
#   "success": true,
#   "answer": "Học phí năm nhất là 8 triệu VND...",
#   "confidence": 0.92,
#   "sources": [...]
# }
```

```javascript
// Using JavaScript (fetch)

const query = "Học phí bao nhiêu?";

fetch("http://localhost:8000/api/v1/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json"
  },
  body: JSON.stringify({
    query: query,
    language: "vi",
    include_sources: true
  })
})
.then(response => response.json())
.then(data => {
  console.log("Answer:", data.answer);
  console.log("Confidence:", data.confidence);
  console.log("Latency:", data.latency_ms, "ms");
  console.log("Sources:", data.sources);
})
.catch(error => console.error("Error:", error));
```

### 3.3 Integration with Student Portal

```python
# examples/integration_student_portal.py

from fastapi import FastAPI, APIRouter
from chatbot_client import ChatbotClient

app = FastAPI()
chatbot_client = ChatbotClient(base_url="http://localhost:8000")

@app.get("/student/ask")
async def ask_question(q: str):
    """Endpoint in student portal that calls chatbot"""
    
    try:
        response = chatbot_client.chat(q, language="vi")
        return {
            "question": q,
            "answer": response['answer'],
            "sources": response['sources'],
            "confidence": response['confidence']
        }
    except Exception as e:
        return {
            "error": str(e),
            "answer": "I couldn't process your question. Please try again."
        }
```

---

## 4. Advanced Features

### 4.1 Session Management

```python
# Session tracking (optional for future)

@app.post("/api/v1/session/start")
async def start_session():
    """Create new conversation session"""
    import uuid
    session_id = str(uuid.uuid4())
    # Store session metadata
    return {"session_id": session_id}

@app.get("/api/v1/session/{session_id}/history")
async def get_session_history(session_id: str):
    """Get conversation history for session"""
    # Retrieve from database
    return {
        "session_id": session_id,
        "messages": [...]
    }
```

### 4.2 Rate Limiting

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/v1/chat")
@limiter.limit("10/minute")  # 10 requests per minute
async def chat(request: ChatRequest):
    # ... chat logic
```

### 4.3 Authentication (if needed)

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer

security = HTTPBearer()

async def verify_token(credentials = Depends(security)):
    """Verify API token"""
    token = credentials.credentials
    # Validate token...
    if not is_valid_token(token):
        raise HTTPException(status_code=401, detail="Invalid token")
    return token

@app.post("/api/v1/chat")
async def chat(request: ChatRequest, token = Depends(verify_token)):
    # Protected endpoint
    pass
```

---

## 5. API Documentation

### 5.1 Interactive Docs

```bash
# FastAPI auto-generates Swagger UI
# Open in browser after starting server:
http://localhost:8000/docs

# ReDoc alternative:
http://localhost:8000/redoc
```

### 5.2 OpenAPI Schema

```bash
# Get OpenAPI JSON schema
curl http://localhost:8000/openapi.json

# Output: Full API specification in JSON format
```

---

## 6. Deployment Configuration

### 6.1 Dockerfile for API

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements-api.txt .
RUN pip install -r requirements-api.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 6.2 Docker Compose with API

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    ports:
      - "8000:8000"
    depends_on:
      - ollama
    environment:
      - LLM_SERVICE_URL=http://ollama:11434
```

---

## 7. Error Codes & Responses

| Code | Message | Solution |
|------|---------|----------|
| 400 | `INVALID_REQUEST` | Check request format |
| 401 | `UNAUTHORIZED` | Provide valid token |
| 404 | `NOT_FOUND` | Check endpoint URL |
| 429 | `RATE_LIMITED` | Wait before retry |
| 500 | `INTERNAL_ERROR` | Check server logs |
| 503 | `SERVICE_UNAVAILABLE` | Ollama/Chroma not running |

---

## 8. API Versioning

```python
# Current: /api/v1/
# Future versions: /api/v2/, /api/v3/, etc.

@app.post("/api/v1/chat")  # Current
async def chat_v1(request: ChatRequest):
    pass

@app.post("/api/v2/chat")  # Future enhancement
async def chat_v2(request: ChatRequest):
    # Enhanced features
    pass
```

---

## Summary 📝

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/healthz` | GET | Health check |
| `/api/v1/chat` | POST | Main chat endpoint |
| `/api/v1/metrics` | GET | System metrics |
| `/api/v1/feedback` | POST | User feedback |

---

## Next Steps

🔗 **Related Documentation:**
- `04-System-Architecture.md` - How API fits in system
- `09-Prompt-Engineering.md` - How prompts work in API
- Full code: `src/api/` folder
