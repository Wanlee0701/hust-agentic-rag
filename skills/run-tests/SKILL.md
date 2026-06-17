---
name: run-tests
description: Chạy bộ unit tests và integration tests của dự án
---

# Run Tests Skill

Sử dụng skill này khi người dùng yêu cầu kiểm tra lỗi, hoặc sau mỗi lần refactor hệ thống lõi.

## Hướng dẫn thực thi:

1. Chạy lệnh sau trong terminal, bắt buộc ở thư mục gốc của dự án (`c:\Users\PC\Desktop\ĐATN`):
   `pytest tests/`

2. Phân tích kết quả test (nếu có lỗi). Báo cáo tóm tắt cho người dùng (ví dụ: "3/3 tests PASS" hoặc "Test bị lỗi ở module `orchestrator.py`").
3. Nếu có lỗi, bạn nên tự chủ động phân tích nguyên nhân bằng cách xem chi tiết log lỗi và báo lại cho người dùng cách sửa.
