# Tự chạy bản demo HomeFix (không cần Claude)

Bản demo chạy trên máy Windows này và được đưa ra Internet qua **Cloudflare Quick Tunnel** (miễn phí, không cần tài
khoản). Sinh viên mở một địa chỉ `https://….trycloudflare.com` trên máy tính hoặc điện thoại.

## Cần có

- Docker Desktop đã cài (đã có trên máy này).
- Thư mục dự án: `C:\Users\ADMIN\PythonProjects\homefix`.
- Kết nối Internet.

## Bật demo — 1 bước

**Nhấp đúp `demo.bat`** trong thư mục dự án (hoặc mở PowerShell tại thư mục đó và gõ `.\demo.bat`).

Script tự làm:

1. Bật Docker Desktop nếu đang tắt, đợi đến khi sẵn sàng. Nếu Docker kẹt (lỗi "socket cũ" từng gặp), script tự dọn
   thư mục `%LOCALAPPDATA%\Docker\run` rồi bật lại.
2. Chạy bản demo ở cấu hình thật (CSDL, web, worker, sao lưu) — lần đầu sau khi Docker bị dọn có thể mất vài phút
   để build lại.
3. Mở tunnel và **in địa chỉ demo** (đồng thời chép vào clipboard nếu được):

```
  Địa chỉ demo (đã chép vào clipboard):
  https://cleaning-poker-bridges-walk.trycloudflare.com
```

Gửi địa chỉ này cho sinh viên. **Địa chỉ đổi mỗi lần bật** — lần sau phải gửi lại địa chỉ mới.

## Các lệnh khác

Mở PowerShell tại thư mục dự án:

| Lệnh | Việc |
|---|---|
| `.\demo.bat` | Bật demo, in địa chỉ mới |
| `.\demo.bat diachi` | In lại địa chỉ đang dùng (không đổi gì) |
| `.\demo.bat tat` | Tắt tunnel sau buổi học — địa chỉ hết hiệu lực ngay, dữ liệu giữ nguyên |
| `.\demo.bat dev` | Tắt tunnel và quay về cấu hình dev (`http://localhost:8000`) để lập trình tiếp |

Nếu đã cài `make` thì có lệnh tương đương: `make demo`, `make demo-url`, `make demo-tat`, `make up`.

## Tài khoản đăng nhập

Dữ liệu mẫu (hư cấu) đã nạp sẵn. Tên đăng nhập theo vai trò:

| Vai trò | Tên đăng nhập |
|---|---|
| Quản trị | `0900000001` |
| Tổng đài | `0900000002` – `0900000004` |
| Kế toán | `0900000005` |
| Giám đốc | `0900000006` |
| Thợ (PIN 6 số) | `0900000101` – `0900000112` |

Mật khẩu/PIN nằm trong tệp **`mat_khau_mau.txt`** ở thư mục dự án (tệp này nằm trong `.gitignore`, không bị
commit; đừng gửi công khai). Mất tệp hoặc muốn đổi mật khẩu trước buổi học thì cấp bộ mới — **giữ nguyên dữ liệu**:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml exec -T web python manage.py cap_lai_mat_khau_mau > mat_khau_mau.txt
```

(Chạy khi demo đang bật. Mở tệp bằng Notepad; mật khẩu cũ hết hiệu lực ngay.)

### Làm sạch dữ liệu mẫu (xóa cả các đơn sinh viên đã tạo)

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo.yml exec -T web python manage.py xoa_du_lieu_mau --xac-nhan
docker compose -f docker-compose.yml -f docker-compose.demo.yml exec -T web python manage.py nap_du_lieu_mau > mat_khau_mau.txt
```

## Mẹo cho buổi học

- Máy phải **bật và không ngủ** suốt buổi (Windows: Cài đặt → Hệ thống → Nguồn → Ngủ: Không bao giờ khi cắm điện).
- Mỗi nhóm sinh viên nên dùng **một tài khoản thợ riêng** (có 12 tài khoản) để không giẫm lên việc của nhau.
- Trên điện thoại: mở địa chỉ → menu trình duyệt → **Thêm vào màn hình chính** để dùng như ứng dụng (PWA).
- Thông báo đẩy ở bản demo chỉ ghi vào log (không gửi thật); chuông thông báo trong ứng dụng vẫn hoạt động.

## Khi gặp sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Script báo "Docker Desktop vẫn chưa chạy" | Mở Docker Desktop bằng tay, đợi biểu tượng cá voi ở khay hệ thống đứng yên, chạy lại `demo.bat` |
| Địa chỉ mở không được / ngừng giữa buổi | Quick Tunnel không cam kết uptime: `.\demo.bat tat` rồi `.\demo.bat`, gửi địa chỉ mới |
| Báo "Không chạy được web" | Xem lỗi: `docker compose -f docker-compose.yml -f docker-compose.demo.yml logs web --tail 50` |
| Gõ sai mật khẩu 5 lần, bị khóa 15 phút | `docker compose -f docker-compose.yml -f docker-compose.demo.yml exec -T web python manage.py axes_reset_username <tên đăng nhập>` |
| PowerShell chặn chạy script | Dùng `demo.bat` (đã kèm `-ExecutionPolicy Bypass` cho riêng script này) |
| Trang hiện lỗi 400 Bad Request | Đang mở bằng địa chỉ khác `*.trycloudflare.com`/`localhost` — dùng đúng địa chỉ script in ra |

## An toàn

- Ai có địa chỉ đều thấy trang đăng nhập; chỉ phát tài khoản cho người cần thử.
- **Tắt tunnel sau buổi học** (`.\demo.bat tat`).
- Dữ liệu mẫu là hư cấu. Không nhập dữ liệu khách hàng thật vào bản demo.
- Muốn một địa chỉ cố định, không đổi mỗi lần: dùng Tailscale Funnel (`docs/VAN_HANH.md` mục 3A).
