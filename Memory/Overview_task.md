# PROJECT CONTEXT: HUST Student Regulation Chatbot (Agentic RAG)

## 1. Tổng quan dự án (Project Overview)
- **Tên dự án:** HUST Student Regulation Chatbot.
- **Mục tiêu chính:** Xây dựng một AI Chatbot giúp sinh viên Đại học Bách khoa Hà Nội (HUST) giải đáp các thắc mắc về quy chế đào tạo, công tác sinh viên, học phí, học bổng, và chuẩn ngoại ngữ dựa trên bộ tài liệu PDF chính thức của nhà trường.
- **Tính năng cốt lõi (Core features):**
  - **Agentic RAG (Multi-hop Reasoning):** Bot không chỉ tìm kiếm một lần. Nó có khả năng tự đánh giá xem tài liệu tìm được có đủ để trả lời không. Nếu thiếu, nó sẽ tự động viết lại từ khóa (Query Rewrite) và tìm kiếm lại (tối đa 3 vòng lặp).
  - **Hiển thị minh bạch (Explainability):** Giao diện hiển thị rõ ràng quá trình suy luận (Reasoning steps), điểm tin cậy (Confidence score), và nguyên văn các đoạn tài liệu gốc (Raw Chunks) kèm theo tên file, số Chương, số Điều.
  - **Linh hoạt LLM Engine:** Cho phép chuyển đổi dễ dàng giữa Local LLM (Ollama) và Cloud LLM (Google Gemini) chỉ bằng một thao tác đổi cấu hình.

## 2. Công nghệ sử dụng (Tech Stack & Architecture)
- **Ngôn ngữ:** Python 3.x
- **Giao diện (UI):** Streamlit
- **Agent Framework:** LangChain (`langchain-core`, `langchain-ollama`, `langchain-google-genai`).
- **Vector Database:** ChromaDB (Local SQLite).
- **Embedding Model:** `BAAI/bge-m3` (chạy qua thư viện `sentence-transformers` và `PyTorch`).
- **LLM Providers:**
  - Ollama (Local): Dùng cho các mô hình nhỏ như `mistral` (GPU RTX 4050 6GB VRAM giới hạn các mô hình < 5GB để tránh bottleneck CPU offloading).
  - Google Gemini API: `gemini-1.5-flash` (dùng để test logic suy luận phức tạp khi Local LLM quá kém).
- **Kiến trúc:** Agentic RAG với vòng lặp ReACT (Retrieve → Evaluate → QueryRewrite → Retrieve → Generate).

## 3. Cấu trúc thư mục (Folder Structure)
```text
ĐATN/
├── app.py                      # File giao diện chính Streamlit (Session, UI, chat history, nút Reset).
├── config.yaml                 # File cấu hình trung tâm: LLM, chunk, top_k, threshold, intents, memory.
├── .env                        # Chứa GEMINI_API_KEY.
├── requirements.txt            # Danh sách thư viện.
├── src/
│   ├── agent/
│   │   ├── orchestrator.py     # Trái tim dự án: StudentRegulationAgent, ReACT loop, Intent+Memory.
│   │   ├── intent_classifier.py # [MỚI v3] Hybrid Intent: LLM extraction + YAML validation.
│   │   ├── memory_manager.py   # [MỚI v3] ConversationMemory: Sliding Window K=5 + entity carry-over.
│   │   ├── prompts.py          # Prompt templates (hệ thống, đánh giá, viết lại câu hỏi).
│   │   └── state.py            # Quản lý AgentState (Track actions, thoughts, confidence, sources).
│   ├── embeddings/
│   │   ├── model.py            # Khởi tạo SentenceTransformer embedding model.
│   │   └── vector_db.py        # Wrapper kết nối ChromaDB, lưu và query vector.
├── data/
│   ├── chroma/                 # Nơi lưu database ChromaDB thực tế (sqlite3).
│   └── chunks/                 # Các file JSON chứa raw text đã băm từ PDF.
├── Memory/                     # [MỚI] Thư mục lưu Sprint Log và Project Context.
└── logs/
    └── chatbot.log             # Nơi ghi log chi tiết của hệ thống để debug.
```

## 4. Quy tắc Code & Important Logic
- **Đóng gói config:** Mọi tham số model, DB, RAG params (top_k, threshold), intent definitions, memory config đều phải đọc từ `config.yaml`.
- **Luồng xử lý chính (`orchestrator.py`) — v3:**
  1. **BƯỚC 0 — Intent Routing:** `IntentClassifier.classify()` gọi LLM bóc tách intent + entities, merge với entity từ memory, kiểm tra `required_fields` trong YAML.
     - Nếu thiếu entity bắt buộc → trả `clarification_question` và dừng luồng.
     - Nếu đủ → tiếp tục RAG.
  2. **RAG Loop (max 2 hops):** `_retrieve()` → Hop 1 có ≥2 kết quả thì generate luôn. Hop 2 mới `_evaluate_context()` (kiểm tra *liên quan*, không kiểm tra *hoàn chỉnh*).
  3. **GenerateAnswer:** Tổng hợp câu trả lời từ context.
  4. **Lưu Memory:** `ConversationMemory.add_turn(session_id, q, a[:500], entities)` sau khi generate xong.
- **Fix lỗi Asyncio Deadlock (CỰC KỲ QUAN TRỌỌNG):**
  - Streamlit chạy mỗi session trên một luồng (thread) độc lập, không có vòng lặp sự kiện bất đồng bộ (`asyncio event loop`).
  - Gói `langchain-google-genai` (v2.x) gọi API Gemini bằng httpx bất đồng bộ bên dưới. Nếu gọi `.invoke()` thẳng trong Streamlit, hệ thống sẽ bị **deadlock (treo vĩnh viễn)**.
  - **Cách fix (Đã làm):** Trong `_invoke_llm` của `orchestrator.py`, hệ thống được code thêm một đoạn `try-except RuntimeError` để ép tạo ra một `asyncio.new_event_loop()` và set nó cho luồng hiện tại trước khi gọi Gemini. Tuyệt đối không xóa đoạn code này nếu dùng Gemini.

## 5. Trạng thái dự án (Current Progress)
- [x] **Data Pipeline:** Đọc PDF, chia nhỏ (chunking), đánh index vào ChromaDB hoàn tất.
- [x] **Vector Search:** Chạy mượt mà, đã map được metadata (`source`, `chapter`, `article`).
- [x] **UI Streamlit:** Xong. Hiển thị mượt mà tiến trình suy luận, sources, và raw chunks.
- [x] **Agent Logic:** Đã implement thành công Multi-hop Reasoning. Hoạt động trơn tru.
- [x] **LLM Integration:** Hỗ trợ tốt cả Ollama (Mistral) và Google Gemini.
- [x] **Evaluate Fix:** Tiêu chí đánh giá đổi sang "liên quan" thay vì "hoàn hảo", skip Evaluate ở Hop 1.
- [x] **Hybrid Intent Routing:** IntentClassifier (LLM + YAML), 5 intent, clarification flow.
- [x] **Conversation Memory:** Sliding Window K=5, entity carry-over, nút Reset phiên.

## 6. Ngữ cảnh làm việc hiện tại (Current Working Context)
- **Phiên vừa hoàn thành (Sprint 03):** Triển khai Hybrid Intent Classification + Conversation Memory.
- **Sprint Log chi tiết:** Xem `Memory/Sprint03_Intent_Routing_Memory.md`
- **Trạng thái:** Dự án hiện tại ở `v3.0-stable`. Tất cả file syntax OK. Sẵn sàng test bằng `streamlit run app.py`.

## 7. Kế hoạch tiếp theo (Next Steps / TODOs)
- Đợi User confirm 5 test case Acceptance Criteria đã pass (xem Sprint03 log).
- **[Trưng hạn]** Hybrid Search: Kết hợp BM25 (keyword) + ChromaDB (vector) để xử lý từ khóa viết tắt (TDN, KKHT, mã môn).
- **[Trung hạn]** Structured Knowledge Base cho tài liệu ngoại ngữ (JSON mapping ngành → TOEIC/IELTS).
- **[Dài hạn]** Containerization: Dockerfile + docker-compose.yml để deploy production.