---
name: update-schema
description: Cập nhật Intent Schema động bằng LLM Auto-Discovery
---

# Update Schema Skill

Sử dụng skill này khi người dùng thay đổi prompt cấu hình hoặc chỉ muốn cập nhật lại logic `university_schema.yaml` từ thư mục `data/` mà không cần phải nhúng lại toàn bộ Vector Database.

## Hướng dẫn thực thi:

1. Chạy lệnh sau trong terminal, bắt buộc phải ở thư mục gốc của dự án (`c:\Users\PC\Desktop\ĐATN`):
   `python scripts/discover_schema.py`

2. Kiểm tra xem file `university_schema.yaml` đã được cập nhật thành công hay chưa bằng cách xem nội dung file đó:
   - Các intent đã được gom nhóm đúng chưa?
   - Danh sách `domain_entities` đã hợp lệ chưa?

3. Báo cáo lại cho người dùng về tổng số intent và entity mới vừa được quét.
