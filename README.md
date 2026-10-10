# HomeFix Ops v1

Hệ thống quản lý đơn sửa chữa tại nhà, tự host miễn phí. Đặc tả: [SPEC.md](SPEC.md); quy ước: [CLAUDE.md](CLAUDE.md);
giả định: [docs/GIA_DINH.md](docs/GIA_DINH.md).

## Chạy trên máy dev

Cần Docker (Docker Desktop trên Windows) và `make`.

```bash
cp .env.example .env        # sửa DJANGO_SECRET_KEY, POSTGRES_PASSWORD; dev đặt DJANGO_COOKIE_SECURE=0
make up                     # db, web (runserver), worker, backup
make quan-tri               # tạo tài khoản QUAN_TRI đầu tiên
```

Mở <http://localhost:8000/dang-nhap/>. Kiểm tra sức khỏe: <http://localhost:8000/suc-khoe/>.

| Lệnh | Việc |
|---|---|
| `make up` / `make down` | Bật / tắt toàn bộ dịch vụ |
| `make test` | Chạy pytest (trong container, PostgreSQL thật) |
| `make check` | ruff + format + import-linter + `manage.py check` + kiểm tra migration + pytest |
| `make vapid` | In cặp khóa VAPID cho Web Push |
| `make seed` | Nạp dữ liệu mẫu (có từ P1) |
| `make backup` | Sao lưu CSDL ngay vào `backups/` |

Chạy kiểm thử ngoài Docker (đã kích hoạt venv, CSDL dev mở ở `127.0.0.1:5433`):
đặt `DATABASE_URL=postgres://homefix:<mật khẩu>@localhost:5433/homefix` rồi `make check RUN=`.

## Máy chủ thật

Trong `.env` bỏ dấu `#` ở dòng `COMPOSE_FILE=docker-compose.yml` (không nạp cấu hình dev), đặt `DJANGO_DEBUG=0`,
`DJANGO_COOKIE_SECURE=1`, rồi `docker compose up -d --build`. Hướng dẫn đầy đủ sẽ ở `docs/VAN_HANH.md` (P6).
