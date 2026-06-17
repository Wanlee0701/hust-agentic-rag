---
name: lint-code
description: Tự động format và kiểm tra lỗi cú pháp mã nguồn
---

# Lint Code Skill

Sử dụng skill này để dọn dẹp code, chuẩn hoá PEP8 trước khi commit hoặc khi code có dấu hiệu bị lộn xộn.

## Hướng dẫn thực thi:

1. Chạy formatter Black trên thư mục mã nguồn chính:
   `black .`

2. Kiểm tra lỗi (linting) bằng Flake8 (hoặc ruff nếu người dùng có cài):
   `flake8 src/ scripts/`

3. Báo cáo lại cho người dùng nếu có cảnh báo chưa thể tự sửa tự động (như unused imports hoặc logic lồng nhau quá sâu).
