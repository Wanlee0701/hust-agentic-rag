# Student Regulation Chatbot - AgenticRAG Implementation

A comprehensive AI-powered chatbot for answering student regulation and policy questions using AgenticRAG with local models for privacy.

## 🎯 Project Overview

This project implements an intelligent chatbot that uses:
- **AgenticRAG Architecture:** AI Agent with reasoning loop for complex queries
- **Local LLM:** Ollama + Mistral 7B (no cloud, full privacy)
- **Hybrid Retrieval:** Semantic + BM25 keyword search
- **Multilingual Support:** Vietnamese + English (CLIR)
- **Privacy-First:** All data stays local

## 📚 Documentation

Complete documentation available in `docs/` folder:

- **01-RAG-Fundamentals.md** ⭐ START HERE
- **02-AgenticRAG-Architecture.md** - Agent concepts
- **03-CLIR-Multilingual.md** - Language support
- **04-System-Architecture.md** - Full system design
- **05-Tech-Stack-Explanation.md** - Technology choices
- **06-Data-Preparation-Guide.md** - Build knowledge base
- **07-Retrieval-Component.md** - Search implementation
- **08-Agent-Design.md** - Agent development
- **09-Prompt-Engineering.md** - LLM optimization
- **10-Testing-Strategy.md** - Testing approach
- **11-Deployment-Guide.md** - Deployment setup
- **12-API-Reference.md** - API documentation

👉 **Read `docs/README.md` first for learning guide!**

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- 8GB RAM (16GB recommended)
- 10GB disk space
- Optional: NVIDIA GPU with CUDA

### 1. Setup Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Ollama

Download from: https://ollama.ai/download

```bash
# Pull Mistral model
ollama pull mistral

# Verify
ollama list
```

### 3. Prepare Knowledge Base

```bash
# Place your PDF files in:
knowledge_base/raw/

# Run data preparation
python data_preparation.py
```

### 4. Run Chatbot

```bash
streamlit run app.py
# Opens at http://localhost:8501
```

## 📁 Project Structure

```
ĐATN/
├── docs/                          # 📚 All documentation (12 files)
│   ├── 01-RAG-Fundamentals.md
│   ├── 02-AgenticRAG-Architecture.md
│   ├── ... (9 more files)
│   └── README.md
│
├── src/
│   ├── agent/                     # 🤖 Agent logic
│   ├── retrieval/                 # 🔍 Search component
│   ├── embeddings/                # 🧠 Vector generation
│   ├── api/                       # 🔌 REST API (optional)
│   └── main.py                    # Entry point
│
├── knowledge_base/
│   └── raw/                       # 📄 Your PDF files here
│
├── data/
│   ├── chroma/                    # Vector store
│   └── embeddings.pkl             # Cached embeddings
│
├── logs/                          # 📊 Application logs
├── tests/                         # 🧪 Test files
├── models/                        # 🤖 Downloaded models
│
├── requirements.txt               # Dependencies
├── config.yaml                    # Configuration
├── docker-compose.yml             # Docker setup
├── Dockerfile                     # Container config
├── .env.example                   # Environment template
└── README.md                      # This file
```

## 🐳 Docker Deployment

```bash
# Build and start
docker-compose up --build

# In another terminal, pull model:
docker exec ollama-service ollama pull mistral

# Prepare knowledge base
python data_preparation.py

# Access at http://localhost:8501
```

## 🧪 Testing

```bash
# Run unit tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## 📊 Configuration

Edit `config.yaml` to customize:
- LLM model and parameters
- Embedding settings
- Vector DB configuration
- Agent behavior
- Logging levels

## 🔑 Key Features

✅ **AgenticRAG:** Multi-step reasoning with agent orchestration
✅ **Hybrid Retrieval:** Semantic + keyword-based search
✅ **Multilingual:** Vietnamese + English with CLIR
✅ **Privacy:** All local, no cloud APIs
✅ **Fast:** ~2-5s per query on CPU
✅ **Scalable:** Easy Docker deployment

## 📈 Performance Targets

- **Accuracy:** >80% for test questions
- **Latency:** <3s average, <5s P95
- **Precision:** >0.80
- **Recall:** >0.70
- **F1 Score:** >0.75

## 🛠️ Development

### Add New Components

1. Create module in `src/`
2. Add tests in `tests/`
3. Update documentation
4. Reference in main

### Modify Prompts

Edit prompt templates in:
- `src/agent/prompts.py`
- `src/api/models.py`

### Customize Retrieval

Adjust in `config.yaml`:
```yaml
retrieval:
  semantic_weight: 0.6
  keyword_weight: 0.4
  top_k: 5
```

## 📝 Logging

Logs stored in `logs/chatbot.log`

Verbosity levels in `config.yaml`:
```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama not responding | Run `ollama serve` in new terminal |
| Model not downloaded | `ollama pull mistral` |
| Port already in use | Change port in `config.yaml` |
| Out of memory | Reduce batch_size, use smaller model |

See `docs/11-Deployment-Guide.md` for more troubleshooting.

## 📞 Support

- 📚 **Theory questions:** See `docs/01-05` (foundation docs)
- 💻 **Code questions:** See `docs/06-12` (implementation docs)
- 🚀 **Deployment help:** See `docs/11-Deployment-Guide.md`
- 🔌 **API help:** See `docs/12-API-Reference.md`

## 📄 License

This project is for educational purposes.

## 🙏 Acknowledgments

- Built with [LangChain](https://langchain.com/)
- LLM: [Ollama](https://ollama.ai/) + [Mistral](https://mistral.ai/)
- Embeddings: [Sentence-Transformers](https://www.sbert.net/)
- Vector DB: [Chroma](https://www.trychroma.com/)

---

**Ready to start?** Read `docs/README.md` and follow the learning guide! 🚀
