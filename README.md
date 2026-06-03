# 🎓 HUST AgenticRAG Chatbot

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)

An intelligent AI Chatbot system specifically designed to answer questions regarding **Student Regulations and Policies at Hanoi University of Science and Technology (HUST)**. This project leverages an advanced **AgenticRAG** architecture combined with a fully local Large Language Model (Ollama + Mistral/Qwen), ensuring 100% data privacy and easy, cost-free deployment.

---

## 🎯 The Problem

Students often struggle to find specific information within lengthy and complex regulation documents (e.g., Training Regulations, Scholarship Policies, Foreign Language Standards). Traditional search tools only return keyword matches without understanding the context.

**HUST AgenticRAG Chatbot** solves this by:
1. **Agent Reasoning:** The AI autonomously reasons, plans its search strategy, and synthesizes information from multiple sources to provide the most accurate answer.
2. **Local & Private:** No third-party APIs (like OpenAI) are used. All data processing and generation happen directly on your server or local machine.
3. **Transparent Citations:** Every answer includes clear references to its sources (File Name, Article Number, Chapter), making it easy to verify.

## ✨ Key Features

- 🐳 **Docker-Ready Server Deployment:** Packaged with `Dockerfile` and `docker-compose.yml`. Just one command to deploy the entire system (App + LLM) and host it securely on any server.
- 🤖 **AgenticRAG Architecture:** The Agent can self-evaluate search results, retry if information is missing (Fallback Retrieval), and score its own confidence.
- 🔍 **Hybrid Retrieval:** Combines semantic search (`bge-m3` embedding model) with keyword-based search for maximum accuracy.
- 💻 **Intuitive UI:** Modern Streamlit interface featuring chat history, expandable reasoning steps, and confidence indicators.

---

## 🚀 Installation & Deployment (Docker Method - Recommended)

The easiest and most reliable way to deploy this application—whether on your local machine or a remote server—is using Docker. This ensures that all environments, Python versions, and dependencies are perfectly isolated.

### 📋 Prerequisites
- **Docker** and **Docker Compose** installed on your system.
- Minimum 8GB RAM (16GB recommended for the LLM).

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/your-username/hust-agentic-rag.git
cd hust-agentic-rag
```

### 2️⃣ Deploy the Entire System
Run the following command to build the chatbot container and start the Ollama service:
```bash
docker-compose up -d --build
```
*(This will run both the chatbot application and the Ollama server in the background).*

### 3️⃣ Pull the LLM Model (First time only)
Since Ollama is now running in a container, you need to tell it to download the `mistral` model:
```bash
docker exec -it ollama-service ollama pull mistral
```

### 4️⃣ Build the Knowledge Base (Vector DB)
The system includes PDF regulation files in `knowledge_base/raw/`. To process them into the Vector Database:
```bash
docker exec -it chatbot-app python scripts/build_knowledge_base.py
```

### 5️⃣ Access the Application
- **Local Machine:** Open your browser and go to `http://localhost:8501`
- **Remote Server:** If you deployed this on a VPS or cloud server with IP `X.X.X.X`, anyone can access it via `http://X.X.X.X:8501`. The container automatically binds to `0.0.0.0`, making it accessible over the network.

---

## 🐍 Manual Installation (Python Method)

If you prefer running it directly without Docker:

1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   ```
2. Install [Ollama](https://ollama.com/), run `ollama serve`, and pull the model: `ollama pull mistral`.
3. Build the knowledge base: `python scripts/build_knowledge_base.py`.
4. Run the app: `streamlit run app.py`.

---

## 📁 Directory Structure

```text
ĐATN/
├── app.py                 # UI entry point (Streamlit)
├── config.yaml            # Central configuration (LLM, Retrieval, vector DB)
├── docker-compose.yml     # Docker Compose orchestration
├── Dockerfile             # Chatbot container build file
├── src/                   # Main source code
│   ├── agent/             # Agent Logic (Orchestrator, Tools, Prompts, State)
│   ├── embeddings/        # PDF processing and Vector Database
│   ├── pipeline/          # Data pipeline
│   └── utils/             # Utilities (Logger, Config)
├── scripts/               # Utility scripts (build DB, reset DB)
├── docs/                  # Architectural documentation
├── data/                  # Derived data (JSON, chunks, chroma DB)
└── knowledge_base/raw/    # Original regulation PDF files
```

---

## ⚙️ Configuration

You can customize the system behavior via the `config.yaml` file:
- Change the LLM (e.g., switch from `mistral` to `qwen`)
- Adjust `top_k` and `similarity_threshold` for the retrieval mechanism
- Modify `chunk_size` and `chunk_overlap` for PDF processing
*Note: If deploying via Docker, the LLM URL is automatically overridden by the `LLM_SERVICE_URL` environment variable defined in `docker-compose.yml`.*

## 📚 Detailed Documentation

Please refer to the `docs/` folder for an in-depth understanding of the architecture:
- `docs/02-AgenticRAG-Architecture.md`: Core AgenticRAG Architecture
- `docs/04-System-Architecture.md`: Overall System Design
- `docs/09-Prompt-Engineering.md`: Prompt Design Techniques for the Agent

---

## 🤝 Contributing

We welcome all contributions (Pull Requests) to improve the system, optimize LLM prompts, or expand the dataset! Please create an Issue to discuss major changes before submitting a PR.

## 📄 License
This project is developed for educational and research purposes.
