# 🎓 HUST Agentic RAG — Chatbot Hỏi Đáp Quy Chế Sinh Viên

> Hệ thống Chatbot tra cứu quy chế đào tạo Đại học Bách Khoa Hà Nội dựa trên kiến trúc **Agentic RAG** với đồ thị trạng thái **LangGraph**.

---

## 📋 Mục lục

- [Giới thiệu](#-giới-thiệu)
- [Kiến trúc hệ thống](#-kiến-trúc-hệ-thống)
- [Yêu cầu cài đặt](#-yêu-cầu-cài-đặt)
- [Hướng dẫn cài đặt](#-hướng-dẫn-cài-đặt)
- [Cấu hình hệ thống](#-cấu-hình-hệ-thống)
- [Xây dựng cơ sở tri thức](#-xây-dựng-cơ-sở-tri-thức)
- [Khởi chạy ứng dụng](#-khởi-chạy-ứng-dụng)
- [Cấu trúc dự án](#-cấu-trúc-dự-án)
- [Xử lý sự cố](#-xử-lý-sự-cố)

---

## 🚀 Giới thiệu

Chatbot sử dụng kiến trúc **Agentic RAG** — Agent thông minh được điều phối bởi **LangGraph StateGraph** có khả năng:

- 🧠 **Phân loại ý định** câu hỏi và phát hiện thông tin còn thiếu (Intent Gate)
- 🔍 **Truy xuất đa vòng** — tự động viết lại truy vấn nếu kết quả chưa đủ tốt (Multi-hop Retrieval)
- ✅ **Kiểm soát chất lượng đầu ra** — tính điểm tin cậy và từ chối trả lời khi không có đủ căn cứ (Confidence Gate)
- 💬 **Duy trì ngữ cảnh** hội thoại đa lượt (Sliding Window Memory)

---

## 🏗 Kiến trúc hệ thống

```
Câu hỏi của người dùng
        │
        ▼
┌─────────────────┐
│   Intent Gate   │ ← Phân loại ý định, phát hiện thực thể thiếu
└────────┬────────┘
         │ (nếu đủ thông tin)
         ▼
┌─────────────────┐
│    Retrieve     │ ← Tìm kiếm ChromaDB (BAAI/bge-m3)
└────────┬────────┘
         ▼
┌─────────────────┐        ┌──────────────┐
│    Evaluate     │──────▶ │    Rewrite   │ ← Viết lại truy vấn (nếu cần)
└────────┬────────┘        └──────┬───────┘
         │ (relevant)             │ (quay lại Retrieve)
         ▼
┌─────────────────┐
│    Generate     │ ← Tổng hợp câu trả lời (Gemini / Ollama)
└────────┬────────┘
         ▼
┌─────────────────┐
│ Confidence Gate │ ← Pass / Warn / Reject
└────────┬────────┘
         ▼
   Câu trả lời + Nguồn trích dẫn
```

---

## 💻 Yêu cầu cài đặt

| Thành phần | Phiên bản tối thiểu | Ghi chú |
|---|---|---|
| **Python** | 3.10+ | Khuyến nghị 3.11 |
| **RAM** | 8 GB | 16 GB nếu dùng Ollama local |
| **Ổ cứng** | 3 GB trống | Dành cho model embedding + ChromaDB |
| **GPU** | Không bắt buộc | Cần nếu chạy LLM local qua Ollama |

### LLM Backend (chọn một trong hai)

| Backend | Ưu điểm | Nhược điểm |
|---|---|---|
| **Gemini API** *(mặc định)* | Nhanh, không cần GPU | Cần API Key, gửi dữ liệu ra ngoài |
| **Ollama (Local)** | Bảo mật tuyệt đối | Cần GPU ≥ 8GB VRAM, tốc độ chậm hơn |

---

## 📦 Hướng dẫn cài đặt

### Bước 1: Clone dự án

```bash
git clone https://github.com/Wanlee0701/hust-agentic-rag.git
cd hust-agentic-rag
```

### Bước 2: Tạo môi trường ảo Python

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt (Windows)
venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source venv/bin/activate
```

### Bước 3: Cài đặt thư viện

```bash
pip install -r requirements.txt
```

> ⏳ Lần đầu chạy, model embedding `BAAI/bge-m3` (~1.1 GB) sẽ được tải tự động từ HuggingFace. Đảm bảo bạn có kết nối Internet ổn định.

### Bước 4: Cấu hình biến môi trường

```bash
# Sao chép file mẫu
cp .env.example .env
```

Mở file `.env` vừa tạo và điền thông tin:

```env
# ── Google Gemini (bắt buộc khi dùng provider='gemini') ──
# Lấy API Key miễn phí tại: https://aistudio.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# ── LangSmith Observability (tuỳ chọn — để theo dõi trace) ──
# Đăng ký tại: https://smith.langchain.com
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_api_key_here
LANGCHAIN_PROJECT=hust-agentic-rag

# ── Ollama (chỉ cần nếu dùng provider='ollama') ──
# LLM_SERVICE_URL=http://localhost:11434
```

> ⚠️ **Lưu ý bảo mật:** File `.env` đã được thêm vào `.gitignore`. **Không bao giờ commit file này lên GitHub.**

---

## ⚙️ Cấu hình hệ thống

Toàn bộ tham số của hệ thống được quản lý tập trung tại file [`config.yaml`](./config.yaml). Dưới đây là các mục quan trọng bạn có thể tùy chỉnh:

### 🤖 Chọn LLM Backend (`llm`)

```yaml
llm:
  # --- Chế độ 1: Dùng Google Gemini API (mặc định, khuyến nghị) ---
  provider: "gemini"
  model_name: "gemini-2.5-flash"   # Hoặc: gemini-1.5-flash, gemini-1.5-pro

  # --- Chế độ 2: Dùng Ollama Local (cần GPU, bảo mật hơn) ---
  # provider: "ollama"
  # model_name: "llama3"           # Tên model đã pull về qua: ollama pull llama3
  # base_url: "http://localhost:11434"

  temperature: 0.3      # Độ sáng tạo (0.0 = chính xác, 1.0 = sáng tạo)
  max_tokens: 2048      # Độ dài tối đa của câu trả lời
  timeout_seconds: 120  # Thời gian chờ tối đa mỗi lần gọi LLM
```

### 🔍 Cấu hình Retrieval (`retrieval`)

```yaml
retrieval:
  top_k: 3                    # Số đoạn tài liệu lấy về mỗi lần tìm kiếm
                              # Tăng lên 5-7 nếu muốn context phong phú hơn
  similarity_threshold: 0.35  # Ngưỡng điểm tương đồng (0.0 - 1.0)
                              # Tăng lên để lấy ít nhưng chính xác hơn
                              # Giảm xuống nếu hệ thống trả về "không tìm thấy" quá nhiều
```

### 🧠 Cấu hình Agent (`agent`)

```yaml
agent:
  max_iterations: 5             # Số vòng lặp Retrieve-Evaluate-Rewrite tối đa
  high_confidence_threshold: 0.65  # ≥ 65%: trả lời bình thường (Pass)
  low_confidence_threshold: 0.35   # < 35%: từ chối trả lời (Reject)
                                   # 35-65%: trả lời kèm cảnh báo (Warn)
  min_avg_similarity: 0.65      # Ngưỡng avg similarity để kết luận tài liệu đủ tốt
```

### 💬 Cấu hình Bộ nhớ Hội thoại (`memory`)

```yaml
memory:
  enabled: true
  window_size: 5            # Số cặp Q&A gần nhất được ghi nhớ
                            # Tăng lên để bot nhớ ngữ cảnh dài hơn
  max_context_chars: 1500   # Giới hạn ký tự context đưa vào prompt
```

### ✂️ Cấu hình Phân đoạn Văn bản (`chunking`)

```yaml
chunking:
  chunk_size: 1000    # Kích thước mỗi đoạn (tính bằng ký tự)
  chunk_overlap: 200  # Số ký tự chồng lấp giữa 2 đoạn liền kề
                      # Tăng overlap nếu câu trả lời hay bị thiếu ngữ cảnh
```

---

## 📚 Xây dựng cơ sở tri thức

### Bước 1: Thêm tài liệu PDF

Đặt tất cả các file PDF quy chế vào thư mục:

```
knowledge_base/raw/
├── Quy_che_25.pdf
├── Hoc_bong_KKHT_2023.pdf
├── QD_NN_K68.pdf
└── ... (các file PDF khác)
```

### Bước 2: Đăng ký metadata cho tài liệu mới (nếu có)

Mở file `config.yaml`, tìm section `pdf_processing.metadata_mapping` và thêm entry cho file PDF mới:

```yaml
pdf_processing:
  metadata_mapping:
    "Ten_file_moi.pdf":
      doc_type: "Loại văn bản"           # Mô tả loại tài liệu
      effective_date: "2025-01-01"       # Ngày hiệu lực
      applicable_students: "All"         # Đối tượng: "All" hoặc ">=K68"
      status: "active"
```

### Bước 3: Chạy script xây dựng Knowledge Base

```bash
python scripts/build_knowledge_base.py
```

Script sẽ tự động:
1. Đọc tất cả PDF trong `knowledge_base/raw/`
2. Làm sạch và phân đoạn văn bản (Hierarchical Chunking)
3. Tạo vector embedding bằng `BAAI/bge-m3`
4. Lưu vào ChromaDB tại `data/chroma/`

> ⏳ Quá trình này mất khoảng **5-15 phút** tùy số lượng tài liệu và cấu hình máy.

### (Tuỳ chọn) Reset và xây dựng lại từ đầu

```bash
python scripts/reset_vector_db.py
python scripts/build_knowledge_base.py
```

---

## ▶️ Khởi chạy ứng dụng

```bash
streamlit run app.py
```

Ứng dụng sẽ khởi động tại: **http://localhost:8501**

> 💡 **Mẹo:** Bật tính năng **"🔍 Hiển thị quá trình suy luận"** trên giao diện để quan sát Agent đang thực hiện các bước nào (Intent Gate → Retrieve → Evaluate → Rewrite → ...).

---

## 📁 Cấu trúc dự án

```
hust-agentic-rag/
├── app.py                          # Điểm khởi chạy Streamlit
├── config.yaml                     # ⚙️  Cấu hình toàn bộ hệ thống
├── requirements.txt                # Danh sách thư viện Python
├── .env.example                    # Mẫu biến môi trường
├── .env                            # Biến môi trường thực tế (KHÔNG commit)
│
├── src/
│   ├── agent/
│   │   ├── graph.py                # LangGraph StateGraph (6 nodes)
│   │   ├── orchestrator.py         # Agent orchestrator chính
│   │   ├── prompts.py              # Prompt templates
│   │   ├── state.py                # GraphState definition
│   │   └── tools/
│   │       ├── retrieve_tool.py    # Tool tìm kiếm ChromaDB
│   │       ├── evaluate_tool.py    # Tool đánh giá tài liệu
│   │       ├── rewrite_tool.py     # Tool viết lại truy vấn
│   │       └── generate_tool.py    # Tool tổng hợp câu trả lời
│   ├── pipeline/
│   │   ├── confidence_gate.py      # Tính điểm tin cậy và phân loại đầu ra
│   │   └── intent_classifier.py    # Phân loại ý định và trích xuất thực thể
│   ├── memory/
│   │   └── memory_manager.py       # Sliding Window Memory
│   ├── vectordb/
│   │   └── vector_db_manager.py    # Giao tiếp với ChromaDB
│   └── utils/
│       ├── config.py               # Nạp config.yaml và .env
│       └── performance.py          # Tracker hiệu năng
│
├── scripts/
│   ├── build_knowledge_base.py     # Script xây dựng KB (chạy offline)
│   └── reset_vector_db.py          # Script reset ChromaDB
│
├── knowledge_base/
│   └── raw/                        # 📂 Đặt file PDF tại đây
│
├── data/
│   └── chroma/                     # ChromaDB (tự động tạo sau khi build KB)
│
├── logs/                           # Log files
└── docs/                           # Tài liệu kỹ thuật
```

---

## 🔧 Xử lý sự cố

### ❌ Lỗi: `GEMINI_API_KEY not found`
- Kiểm tra file `.env` đã được tạo từ `.env.example` chưa
- Đảm bảo dòng `GEMINI_API_KEY=...` không có khoảng trắng thừa

### ❌ Lỗi: `Collection not found` hoặc `ChromaDB empty`
- Chưa xây dựng Knowledge Base. Chạy lại:
  ```bash
  python scripts/build_knowledge_base.py
  ```

### ❌ Lỗi khi dùng Ollama: `Connection refused`
- Đảm bảo Ollama đang chạy: `ollama serve`
- Kiểm tra model đã được pull: `ollama list`
- Kiểm tra `base_url` trong `config.yaml` khớp với cổng Ollama đang lắng nghe

### ❌ Hệ thống trả lời "Không tìm thấy thông tin" quá nhiều
- Thử giảm `similarity_threshold` trong `config.yaml` xuống `0.25`
- Thử giảm `min_avg_similarity` trong `agent` xuống `0.55`
- Kiểm tra PDF đã được đặt đúng vào `knowledge_base/raw/` và đã chạy build script

### ❌ Câu trả lời bị cắt ngắn hoặc thiếu thông tin
- Tăng `max_tokens` trong section `llm` của `config.yaml`
- Tăng `top_k` trong section `retrieval` để lấy nhiều tài liệu hơn
- Tăng `chunk_overlap` trong section `chunking` và build lại KB

---

## 📄 Giấy phép

Dự án được phát triển phục vụ mục đích học thuật — Đồ án Tốt nghiệp, Khoa Toán - Tin, Đại học Bách Khoa Hà Nội.

**Tác giả:** Lê Quang Đức — `duclq227221@sis.hust.edu.vn`

**Giảng viên hướng dẫn:** TS. Ngô Thị Hiền
