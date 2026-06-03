# 🎓 HUST AgenticRAG Chatbot

![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-black.svg)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-orange.svg)

Hệ thống Chatbot AI thông minh dành riêng cho việc giải đáp **Quy chế và Chính sách sinh viên Đại học Bách khoa Hà Nội (HUST)**. Dự án ứng dụng kiến trúc **AgenticRAG** tiên tiến kết hợp với mô hình ngôn ngữ lớn (LLM) chạy hoàn toàn local (Ollama + Mistral/Qwen), đảm bảo 100% quyền riêng tư dữ liệu và có thể triển khai dễ dàng mà không tốn phí API.

---

## 🎯 Bài toán đặt ra

Sinh viên thường gặp khó khăn khi phải tra cứu thông tin từ hàng loạt văn bản quy chế dài dòng, phức tạp (Quy chế đào tạo, Quy chế học bổng, Chuẩn ngoại ngữ, v.v.). Các công cụ tìm kiếm truyền thống thường chỉ trả về từ khóa mà không hiểu được ngữ cảnh câu hỏi.

**HUST AgenticRAG Chatbot** giải quyết vấn đề này bằng cách:
1. **Agent Reasoning:** AI tự động suy luận, lập kế hoạch tìm kiếm và tổng hợp thông tin từ nhiều nguồn để đưa ra câu trả lời chính xác nhất.
2. **Local & Private:** Không sử dụng API của bên thứ ba (như OpenAI). Toàn bộ dữ liệu và quá trình xử lý diễn ra ngay trên máy của bạn.
3. **Trích dẫn minh bạch:** Mỗi câu trả lời đều đi kèm nguồn gốc rõ ràng (Tên file, Số Điều, Chương) giúp sinh viên dễ dàng đối chiếu.

## ✨ Tính năng nổi bật

- 🤖 **Kiến trúc AgenticRAG:** Thay vì RAG truyền thống (chỉ tìm kiếm và trả lời), Agent có khả năng tự đánh giá kết quả tìm kiếm, tra cứu lại nếu thiếu thông tin (Fallback Retrieval) và chấm điểm độ tin cậy (Confidence Score).
- 🔍 **Hybrid Retrieval:** Kết hợp tìm kiếm ngữ nghĩa (Semantic Search với `bge-m3`) và tìm kiếm từ khóa.
- 💻 **Giao diện trực quan:** Streamlit UI hiện đại với lịch sử trò chuyện, hiển thị tiến trình suy luận (Reasoning Steps) và thanh độ tin cậy.
- 🔒 **100% Local:** Triển khai qua Ollama, bảo mật tuyệt đối dữ liệu nội bộ.

---

## 🚀 Hướng dẫn Cài đặt & Deploy

### 📋 Yêu cầu hệ thống (Requirements)
- **Hệ điều hành:** Windows / Linux / macOS
- **Python:** Phiên bản 3.10 trở lên
- **RAM:** Tối thiểu 8GB (Khuyến nghị 16GB để chạy mượt LLM local)
- **Ollama:** Cài đặt sẵn trên máy

### 1️⃣ Cài đặt môi trường

Clone repository về máy:
```bash
git clone https://github.com/your-username/hust-agentic-rag.git
cd hust-agentic-rag
```

Tạo môi trường ảo (Virtual Environment) và cài đặt thư viện:
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Cài đặt dependencies
pip install -r requirements.txt
```

### 2️⃣ Cài đặt Ollama & Mô hình LLM

1. Tải và cài đặt Ollama tại [ollama.com](https://ollama.com/)
2. Mở terminal và tải mô hình `mistral` (hoặc `qwen3.5:4b` nếu máy yếu hơn):
```bash
ollama pull mistral
```
3. Đảm bảo Ollama đang chạy ngầm (`ollama serve`).

### 3️⃣ Xây dựng Cơ sở tri thức (Vector DB)

Hệ thống đã có sẵn thư mục `knowledge_base/raw/` chứa các file PDF quy chế. Để xây dựng Vector Database:

```bash
python scripts/build_knowledge_base.py
```
*Quá trình này sẽ parse PDF, chia nhỏ (chunking), nhúng (embedding với bge-m3) và lưu vào ChromaDB tại thư mục `data/chroma/`.*

### 4️⃣ Khởi chạy Ứng dụng

Khởi động giao diện Streamlit:
```bash
streamlit run app.py
```
Trình duyệt sẽ tự động mở tại địa chỉ `http://localhost:8501`.

---

## 📁 Cấu trúc Thư mục

Dự án được tổ chức theo chuẩn Modular Architecture:

```text
ĐATN/
├── app.py                 # UI entry point (Streamlit)
├── config.yaml            # Cấu hình trung tâm (LLM, Retrieval, vector DB)
├── src/                   # Source code chính
│   ├── agent/             # Logic Agent (Orchestrator, Tools, Prompts, State)
│   ├── embeddings/        # Xử lý PDF và Vector Database
│   ├── pipeline/          # Data pipeline
│   └── utils/             # Tiện ích (Logger, Config)
├── scripts/               # Scripts tiện ích (build DB, reset DB)
├── docs/                  # Tài liệu kiến trúc và hướng dẫn chi tiết
├── data/                  # Dữ liệu phái sinh (JSON, chunks, chroma DB)
└── knowledge_base/raw/    # PDF văn bản quy chế gốc
```

---

## ⚙️ Cấu hình (Configuration)

Bạn có thể tùy chỉnh toàn bộ hệ thống tại file `config.yaml`:
- Thay đổi LLM (ví dụ: chuyển từ `mistral` sang `qwen`)
- Thay đổi top_k, similarity_threshold cho tìm kiếm
- Thay đổi chunk_size, chunk_overlap khi xử lý PDF

## 📚 Tài liệu chi tiết

Vui lòng tham khảo thư mục `docs/` để tìm hiểu sâu hơn về kiến trúc:
- `docs/02-AgenticRAG-Architecture.md`: Kiến trúc AgenticRAG
- `docs/04-System-Architecture.md`: Thiết kế hệ thống tổng thể
- `docs/09-Prompt-Engineering.md`: Kỹ thuật thiết kế Prompt cho Agent

---

## 🤝 Đóng góp (Contributing)

Mọi đóng góp (Pull Requests) để cải thiện hệ thống, tối ưu hóa LLM prompts hoặc mở rộng bộ dữ liệu đều được hoan nghênh! Vui lòng tạo Issue trước khi submit PR lớn.

## 📄 Giấy phép (License)
Dự án được phát triển phục vụ mục đích giáo dục và nghiên cứu.
