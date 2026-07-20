FROM python:3.11-slim

WORKDIR /app

# ── System dependencies ──────────────────────────────────────────────
# pdfplumber needs libpoppler for PDF text extraction
# sentence-transformers may need gcc for compiling tokenizers
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpoppler-cpp-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies (cache layer ─ before copying source) ─────
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application source ──────────────────────────────────────────────
COPY . .

# ── Runtime directories ─────────────────────────────────────────────
RUN mkdir -p data/chroma logs

# HuggingFace model cache (maps to volume for persistence across restarts)
ENV HF_HOME=/app/models

# Streamlit
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]
