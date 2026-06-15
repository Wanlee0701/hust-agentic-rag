---
name: docker-rebuild
description: Dọn dẹp và khởi chạy lại các docker containers
---

# Docker Rebuild Skill

Sử dụng skill này khi cần dọn dẹp các container hiện có và build lại môi trường mới từ file `docker-compose.yml`.

## Hướng dẫn thực thi:

1. Chạy chuỗi lệnh sau trong terminal, bắt buộc ở thư mục gốc của dự án (`c:\Users\PC\Desktop\ĐATN`):
   `docker-compose down && docker-compose up -d --build`

2. Kiểm tra log khởi tạo để đảm bảo các service đang chạy thành công:
   `docker-compose logs --tail 20`

3. Báo cho người dùng biết trạng thái của các container.
