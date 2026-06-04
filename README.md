# 🤖 AgenticRAG Chatbot Framework

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

An open-source, highly customizable **AgenticRAG (Retrieval-Augmented Generation)** framework designed to help you quickly build an intelligent document-answering chatbot. This system uses fully local Large Language Models (via Ollama) ensuring **100% data privacy**, combined with an advanced reasoning agent that synthesizes information, evaluates its own searches, and provides transparent citations.

---

## ✨ Why AgenticRAG?

Traditional RAG systems simply search for keywords and pass them to an LLM. This **AgenticRAG** framework goes a step further:
- 🧠 **Self-Reasoning:** The Agent plans its search, evaluates the retrieved context, and decides if it needs to search again with different queries (Fallback Retrieval) before answering.
- 🎯 **Hybrid Retrieval:** Automatically combines Semantic Search (`BAAI/bge-m3`) with Keyword Search for pinpoint accuracy.
- 🔒 **100% Local & Private:** No API keys required. Everything runs on your own hardware or server.
- 🚀 **Plug & Play:** Just drop your PDF files into a folder, run a command, and your custom AI is ready.
---

## 📋 Prerequisites & System Requirements

Before you clone and run this repository, ensure your system meets the following requirements:

- **Operating System:** Windows 10/11, macOS, or Linux
- **Hardware:** Minimum 8GB RAM (16GB+ highly recommended for running local LLMs smoothly).
- **Git:** Installed on your system to clone the repository.
- **Docker & Docker Compose** *(Recommended)*: If using the Docker deployment method, ensure Docker Desktop (or Docker Engine) is installed and running.
- **Python 3.10+** *(Alternative)*: Only required if you choose the Manual Installation method.
- **Ollama:** Installed locally or via Docker. Used to serve the open-source LLMs (e.g., Mistral, Llama 3, Gemma).
---

## 🛠️ Quick Start (Docker Deployment)

Docker is the recommended way to deploy this framework, ensuring perfectly isolated environments.

### 1. Clone the Repository
```bash
git clone https://github.com/Wanlee0701/hust-agentic-rag
cd agentic-rag-framework
```

### 2. Add Your Documents
Drop any PDF documents you want the chatbot to read into the `knowledge_base/raw/` directory.

### 3. Start the System
Run the following command to start both the Chatbot UI and the Ollama LLM server:
```bash
docker-compose up -d --build
```

### 4. Pull the LLM Model (First time only)
By default, the system uses the `gemma-4-E4B` model (or `mistral`). Tell the Ollama container to download it:
```bash
docker exec -it ollama-service ollama pull gemma-4-E4B
```

### 5. Build Your Knowledge Base
Convert your PDFs into the Vector Database (ChromaDB):
```bash
docker exec -it chatbot-app python scripts/build_knowledge_base.py
```

### 6. Access the App
Open your browser and navigate to `http://localhost:8501`. (If hosted on a server, use `http://<server-ip>:8501`).

---

## 🐍 Manual Installation (Without Docker)

1. **Setup Python Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Setup Ollama:** Install [Ollama](https://ollama.com/), run `ollama serve`, and pull your preferred model (`ollama pull gemma-4-E4B`).
3. **Add PDFs:** Place your files in `knowledge_base/raw/`.
4. **Build Vector DB:** `python scripts/build_knowledge_base.py`
5. **Run the App:** `streamlit run app.py`

---

## ⚙️ Configuration (`config.yaml`)

The entire framework is controlled by `config.yaml`. You don't need to touch the code to customize the chatbot for your specific use case.

### 1. Changing the LLM Model
Want to use a different model (e.g., `llama3`, `qwen`, `mistral`)? Just change the `model_name` and ensure you have pulled it via Ollama.
```yaml
llm:
  provider: "ollama"
  model_name: "llama3"       # <-- Change this!
  base_url: "http://localhost:11434"
```

### 2. PDF Processing & Metadata
If you have multiple documents targeting different user groups, you can define metadata in the config. The agent can use this metadata to filter searches.
```yaml
pdf_processing:
  metadata_mapping:
    "HR_Policy_2024.pdf":
      doc_type: "Human Resources"
      status: "active"
```
You can also define custom regex patterns to strip unwanted headers/footers from your PDFs during processing under `text_cleanup_patterns`.

### 3. Tuning the Vector Database & Retrieval
Adjust how documents are chunked and how strictly the search engine matches queries:
```yaml
chunking:
  chunk_size: 1000
  chunk_overlap: 200

retrieval:
  top_k: 3
  similarity_threshold: 0.35   # Lower = broader search, Higher = stricter match
```

---

## 📁 Core Directory Structure

This repository strictly contains the core engine. Example documents, thesis materials, and development notebooks are excluded.

```text
.
├── app.py                 # Streamlit User Interface
├── config.yaml            # Main Configuration File
├── docker-compose.yml     # Docker Setup
├── Dockerfile             # App Container Image
├── src/                   # Core Engine
│   ├── agent/             # Logic (Orchestrator, Tools, Prompts, State)
│   ├── pipeline/          # Data Pipeline (PDF -> Vector)
│   ├── embeddings/        # Embedding Models & Vector DB Connectors
│   └── utils/             # Config & Logging utilities
├── scripts/               # Utility scripts (build/reset Knowledge Base)
└── knowledge_base/raw/    # -> DROP YOUR PDFs HERE <-
```

## 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request if you add new Agent capabilities, improve the Hybrid Retrieval, or add support for new Vector Databases.

## 📄 License
MIT License. Free to use and modify for any purpose.
