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
| `make seed` | Nạp dữ liệu mẫu (danh mục, ~60 đơn mọi trạng thái, bảo hành, đối soát) |
| `make backup` | Sao lưu CSDL ngay vào `backups/` |
| `make thu-khoi-phuc` | Thử khôi phục bản sao lưu mới nhất vào CSDL tạm, so số dòng (không động vào dữ liệu thật) |
| `make anh-xa-bang` | Sinh lại `docs/ANH_XA_BANG.md` (lớp ↔ bảng ↔ cột ↔ kiểu) sau khi đổi mô hình |

Chạy kiểm thử ngoài Docker (đã kích hoạt venv, CSDL dev mở ở `127.0.0.1:5433`):
đặt `DATABASE_URL=postgres://homefix:<mật khẩu>@localhost:5433/homefix` rồi `make check RUN=`.

## Máy chủ thật

Trong `.env` bỏ dấu `#` ở dòng `COMPOSE_FILE=docker-compose.yml` (không nạp cấu hình dev), đặt `DJANGO_DEBUG=0`,
`DJANGO_COOKIE_SECURE=1`, rồi `docker compose up -d --build`. Hướng dẫn đầy đủ (tunnel HTTPS, sao lưu/khôi phục,
tác vụ nền, xử lý sự cố, rà soát bảo mật): [docs/VAN_HANH.md](docs/VAN_HANH.md).

## Tài liệu

- [docs/HUONG_DAN_SU_DUNG.md](docs/HUONG_DAN_SU_DUNG.md) — hướng dẫn theo vai trò (cũng ở trang `/huong-dan/`).
- [docs/ANH_XA_BANG.md](docs/ANH_XA_BANG.md) — ánh xạ lớp ↔ bảng ↔ cột ↔ kiểu, sinh tự động.
- [docs/GIA_DINH.md](docs/GIA_DINH.md) — giả định, lựa chọn và trạng thái đã chốt.
