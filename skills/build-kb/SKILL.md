---
name: build-kb
description: Build lại toàn bộ Knowledge Base của dự án AgenticRAG
---

# Build Knowledge Base Skill

Sử dụng skill này khi người dùng yêu cầu cập nhật lại toàn bộ hệ thống cơ sở tri thức (tài liệu quy chế, vector DB, và schema).

## Hướng dẫn thực thi:

1. Chạy lệnh sau trong terminal, bắt buộc phải ở thư mục gốc của dự án (`c:\Users\PC\Desktop\ĐATN`):
   `python scripts/build_knowledge_base.py`

2. Lệnh này sẽ thực hiện pipeline gồm:
   - Xử lý PDF sang JSON.
   - Chunking dữ liệu.
   - Nhúng dữ liệu vào Vector DB.
   - Tự động quét và phát hiện Intent Schema mới.

3. Theo dõi log và báo lại cho người dùng khi hoàn tất.
