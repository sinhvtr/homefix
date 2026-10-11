# Vận hành HomeFix Ops v1

Tài liệu cho người cài đặt và trông máy chủ (SPEC 14.3). Mọi lệnh chạy trong thư mục mã nguồn trên máy chủ.

## 1. Phần cứng và phần mềm

- Máy tính hoặc mini PC **2 nhân, 4 GB RAM, 20 GB trống**, bật 24/7. Máy cũ chạy Ubuntu Server 24.04 là đủ;
  Windows dùng Docker Desktop + WSL2 cũng được.
- Docker + Docker Compose, `git`, `make` (Windows: Git Bash có sẵn `make` qua `choco install make`, hoặc gõ thẳng
  lệnh `docker compose …` tương ứng trong Makefile).
- Năm dịch vụ chạy bằng Docker Compose (`docker-compose.yml`), tự khởi động lại (`restart: unless-stopped`):

| Dịch vụ | Việc |
|---|---|
| `db` | PostgreSQL 16, dữ liệu ở volume `pgdata` |
| `web` | `migrate` → `collectstatic` → gunicorn 3 worker × 2 luồng, chỉ nghe `127.0.0.1:8000` |
| `worker` | django-q2: thông báo, tác vụ định kỳ (mục 5) |
| `backup` | cron 02:00 chạy `pg_dump` vào thư mục `backups/` |

## 2. Cài lần đầu

1. `git clone <kho mã> homefix && cd homefix`
2. `cp .env.example .env` rồi sửa:
   - bỏ dấu `#` ở dòng `COMPOSE_FILE=docker-compose.yml` (để **không** nạp cấu hình dev — A-07);
   - `DJANGO_SECRET_KEY`: sinh bằng `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`;
   - `POSTGRES_PASSWORD`: mật khẩu dài ngẫu nhiên;
   - `DJANGO_DEBUG=0`, `DJANGO_COOKIE_SECURE=1`, `THONG_BAO_CHI_CONSOLE=0`.
3. `docker compose up -d --build` — lần đầu mất vài phút (tải image, build CSS). Kiểm tra: `docker compose ps`
   thấy `web` ở trạng thái `healthy`.
4. Khóa Web Push: `docker compose exec web python manage.py tao_khoa_vapid`, chép hai khóa vào `.env`
   (`VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL=mailto:…`) rồi `docker compose up -d`.
5. Tạo tài khoản quản trị đầu tiên: `make quan-tri` (hỏi tên, SĐT, mật khẩu).
6. (Chỉ khi thử nghiệm) dữ liệu mẫu: `make seed` — mật khẩu/PIN in ra **một lần**. Trước khi chạy thật:
   `docker compose exec web python manage.py xoa_du_lieu_mau --xac-nhan`.

## 3. Đưa ra Internet (chọn một; D để demo nhanh)

PWA và Web Push **bắt buộc HTTPS**. Ứng dụng chỉ nghe `127.0.0.1:8000`; HTTPS do tunnel lo.

**A. Tailscale Funnel (không cần tên miền).** Cài Tailscale, đăng nhập, bật *HTTPS Certificates* và *Funnel* trong
trang quản trị Tailscale, chạy `sudo tailscale funnel --bg 8000` → nhận `https://<ten-may>.<tailnet>.ts.net`.

**B. Cloudflare Tunnel (đã có tên miền trên Cloudflare).** Thêm dịch vụ `cloudflared` vào compose với token tunnel,
trỏ `homefix.<ten-mien>` → `http://web:8000`; bật *Always Use HTTPS*.

**C. Chỉ mạng nội bộ.** Đổi cổng bind thành `0.0.0.0:8000:8000`, đặt `DJANGO_COOKIE_SECURE=0`, truy cập
`http://<ip-may-chu>:8000`. PWA và Web Push **không** hoạt động — chỉ để thử giao diện tổng đài.

**D. Demo nhanh — Cloudflare Quick Tunnel (không cần tài khoản, không cần tên miền).** Dùng ngay trên máy dev,
không sửa `.env`: tệp `docker-compose.demo.yml` chạy cấu hình thật (gunicorn, `DEBUG` tắt, cookie chỉ HTTPS) và một
container `cloudflared` mở địa chỉ `https://<ngẫu-nhiên>.trycloudflare.com`.

```bash
make demo        # build + chạy web, worker, db, backup, tunnel
make demo-url    # in địa chỉ https://….trycloudflare.com (đợi ~10 giây sau make demo)
make demo-tat    # tắt tunnel (địa chỉ hết hiệu lực); `make up` để về cấu hình dev
```

Lưu ý: địa chỉ **đổi mỗi lần** bật lại tunnel; không có cam kết uptime (dùng để thử/demo); ai có địa chỉ đều mở được
trang đăng nhập — chỉ phát tài khoản cho người cần thử, nạp lại dữ liệu mẫu để có mật khẩu mới trước buổi demo;
thông báo chỉ in log (`THONG_BAO_CHI_CONSOLE=1`). Muốn địa chỉ cố định → cách A.

Sau khi có địa chỉ (cách A–C), đặt trong `.env` rồi `docker compose up -d`:

```
DJANGO_ALLOWED_HOSTS=<ten-may>.<tailnet>.ts.net
DJANGO_CSRF_TRUSTED_ORIGINS=https://<ten-may>.<tailnet>.ts.net
SITE_URL=https://<ten-may>.<tailnet>.ts.net
```

Thợ mở địa chỉ trên điện thoại → đăng nhập bằng SĐT + PIN → "Thêm vào màn hình chính" → bật thông báo ở
**Cài đặt** (iPhone: iOS 16.4+ và phải mở từ màn hình chính; khuyên dùng Telegram).

## 4. Sao lưu và khôi phục

- **Tự động:** container `backup` chạy `pg_dump -Fc` lúc **02:00** mỗi ngày → `backups/homefix_YYYYmmdd.dump`,
  xóa bản cũ hơn `BACKUP_KEEP_DAYS` (mặc định 14) ngày.
- **Ngay lập tức:** `make backup`.
- **Thử khôi phục (nên làm mỗi tháng):** `make thu-khoi-phuc` — nạp bản mới nhất vào CSDL tạm
  `homefix_thu_khoi_phuc`, so số dòng các bảng chính với CSDL đang chạy rồi xóa CSDL tạm; **không** động vào dữ
  liệu thật. Kết quả mong đợi: dòng cuối "Khôi phục thử thành công…". Đã thử trên máy dev ngày 11/10/2026: 6/6
  bảng khớp số dòng.
- **Khôi phục thật** (mất dữ liệu sau thời điểm sao lưu — dừng ứng dụng trước):

```bash
docker compose stop web worker
docker compose exec -T db pg_restore -U homefix -d homefix --clean --if-exists < backups/homefix_YYYYmmdd.dump
docker compose start web worker
```

- Ảnh hiện trường và ảnh chứng từ nằm ở volume `media` — sao lưu kèm:
  `docker run --rm -v homefix_media:/m -v "$PWD/backups":/b alpine tar czf /b/media_$(date +%Y%m%d).tgz -C /m .`
- Khuyến nghị chép thư mục `backups/` sang ổ khác hoặc Google Drive (`rclone`, tùy chọn).

## 5. Tác vụ nền (django-q2, lịch nằm trong migration dữ liệu)

| Tác vụ | Chu kỳ | Việc |
|---|---|---|
| `kiem_tra_qua_han_phan_cong` | 1 phút | BR02: đề nghị quá 15 phút → quá hạn, báo tổng đài |
| `nhac_xac_nhan_lich` | 1 giờ | BR08: nhắc khách chốt lịch; đủ 3 lần → hủy |
| `dong_don_het_bao_hanh` | 00:15 | BR05: đơn hết hạn bảo hành → Đã đóng |
| `cap_nhat_khach_vip` | 01:00 | BR07: ≥ 3 đơn hoàn thành trong 365 ngày → VIP |
| sao lưu (container `backup`) | 02:00 | mục 4 |
| `don_dep_thong_bao` | hằng tuần | xóa thông báo đã đọc > 90 ngày |

Xem tác vụ đã chạy / lỗi: trang quản trị kỹ thuật `/he-thong-noi-bo/` (superuser, mục *Django Q*) hoặc
`docker compose logs worker`. Mọi tác vụ lũy đẳng — chạy lại không sinh sai lệch.

## 6. Cập nhật phiên bản

```bash
make backup
git pull
docker compose up -d --build   # migration chạy tự động khi web khởi động
```

Sau khi đổi mô hình dữ liệu (lập trình viên): `make anh-xa-bang` để sinh lại `docs/ANH_XA_BANG.md`
(kiểm thử báo đỏ nếu quên).

## 7. Theo dõi và xử lý sự cố

| Hiện tượng | Kiểm tra |
|---|---|
| Trang không mở | `docker compose ps`; `curl http://127.0.0.1:8000/suc-khoe/` trả `{"trang_thai": "ok"}` |
| Lỗi 400 Bad Request | Địa chỉ truy cập chưa có trong `DJANGO_ALLOWED_HOSTS` |
| Lỗi 403 CSRF khi đăng nhập | Thiếu `DJANGO_CSRF_TRUSTED_ORIGINS` (phải có `https://`) hoặc đang dùng http với `DJANGO_COOKIE_SECURE=1` |
| Thợ không nhận thông báo | `THONG_BAO_CHI_CONSOLE=0`? khóa VAPID đã đặt? thợ bấm "Gửi thử" ở Cài đặt; `docker compose logs worker` |
| Tài khoản bị khóa đăng nhập | Khóa 15 phút sau 5 lần sai (theo tài khoản). Mở sớm: `docker compose exec web python manage.py axes_reset_username <tên đăng nhập>` |
| Quên mật khẩu quản trị | Quản trị khác đặt lại ở **Người dùng**, hoặc `docker compose exec web python manage.py changepassword <tên đăng nhập>` |
| Đầy ổ đĩa | `du -sh backups/`; giảm `BACKUP_KEEP_DAYS`; `docker system prune` (không xóa volume) |

Nhật ký thao tác nghiệp vụ (ai làm gì, lúc nào, từ IP nào) xem ở **Quản trị → Nhật ký** (`/quan-tri/nhat-ky/`).
Nhật ký chỉ thêm, không sửa/xóa; v1 không tự xóa nhật ký — giữ tối thiểu 12 tháng (NFR06).

## 8. Rà soát bảo mật (P6)

`docker compose exec web python manage.py check --deploy` **không còn cảnh báo** (kiểm thử
`test_check_deploy_cau_hinh_prod_sach` giữ điều này). Đã có:

- `DEBUG` luôn tắt ở `config.settings.prod`; bí mật chỉ trong `.env` (không commit `.env`, `media/`, `backups/`).
- Cookie phiên và CSRF chỉ qua HTTPS; HSTS 1 năm (kể cả tên miền con); `X-Frame-Options: DENY`; `nosniff`.
- Chuyển hướng HTTP→HTTPS để tunnel lo (cảnh báo `security.W008` đã xét — A-90); không preload HSTS (`W021`).
- Mật khẩu băm mặc định Django; PIN thợ 6 số, bắt buộc đổi lần đầu; khóa 15 phút sau 5 lần sai.
- Phân quyền kiểm tra ở cả view lẫn DAO; thợ đoán URL đơn/ảnh của người khác nhận 404 (NFR04).
- Ảnh không phục vụ công khai (`/media/` không mở) — chỉ qua `/anh/<id>/` có kiểm quyền; EXIF/GPS bị xóa.
- Thư viện JS/CSS tự host (htmx, Chart.js 4.4.7 — `static/js/chart.umd.min.js`; bản gốc từ jsDelivr có SHA-256
  `206b6e8bb00fc7bba2c7ee80ca41db3e9e05ba7be0aa35abeba9cfd5357f5d0e`, đã bỏ dòng cuối `//# sourceMappingURL=…`
  vì không kèm tệp `.map` — nếu để, `collectstatic` của bản chạy thật báo lỗi; SHA-256 sau khi bỏ:
  `42f4dbfe70c430ffc22c7128f36cae8d599cac90b8cd37c8f42a59e565e5deb7`).
- Django Admin chỉ cho superuser kỹ thuật ở `/he-thong-noi-bo/`; tài khoản `QUAN_TRI` không phải superuser.

**Còn để thầy/công ty làm:** rà pháp lý dữ liệu cá nhân (OI-05); thử Web Push thật trên Android qua HTTPS
(tiêu chí P3 — xem "Việc còn treo" trong `docs/GIA_DINH.md`).
