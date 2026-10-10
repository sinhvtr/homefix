# Giả định và lựa chọn mặc định của HomeFix Ops v1

Ghi theo CLAUDE.md: mỗi điểm mơ hồ hoặc đề xuất [ĐX] có mã A-xx, lý do và cách đổi.
Cột **Đã chốt?**: C = thầy/khách hàng đã duyệt, K = chưa duyệt (mặc định K).

## Giả định có sẵn trong SPEC

| Mã | Nội dung | Lý do | Cách đổi | Đã chốt? |
|---|---|---|---|---|
| A-01 | (Không dùng trong SPEC — giữ chỗ để mã khớp bài mẫu) | — | — | — |
| A-02 | Thợ bấm "Đã đến nơi": nhóm sửa chữa → CHO_DUYET_GIA (T9); nhóm vệ sinh → DANG_SUA và tạo dòng CONG theo bảng giá (T10) | SRS không mô tả bước chuyển từ DA_CO_THO | Sửa dòng T9/T10 trong `CHUYEN_TRANG_THAI` (P2) | K |
| A-03 | Thợ báo bận / tổng đài rút việc: DA_CO_THO → CHO_CU_THO (T8) | SRS chưa có luồng trả việc | Dòng T8 | K |
| A-04 | Khách từ chối báo giá: thu phí kiểm tra `PHI_KIEM_TRA_KHI_TU_CHOI` (mặc định 0 đ) | Thực tế thợ đã mất công đến | Cấu hình `PHI_KIEM_TRA_KHI_TU_CHOI` | K |

## Đề xuất [ĐX] và vấn đề mở đã chọn mặc định trong SPEC

| Mã | Nội dung | Lý do | Cách đổi | Đã chốt? |
|---|---|---|---|---|
| A-10 | Thợ đăng nhập bằng SĐT + **PIN 6 số** thay cho OTP (lệch NFR05) | SMS OTP có phí | Cài `XacThucOTP` ở v2 | K |
| A-11 | BR08: hết 3 lần nhắc → **DA_HUY** (SRS ghi "đóng") | DA_DONG dành cho đơn hoàn thành hết bảo hành | Dòng T5 | K |
| A-12 | Giữ 9 trạng thái; "Chưa cử được thợ" là cờ `canh_bao_chua_cu_duoc` trên đơn CHO_CU_THO | Danh sách 9 trạng thái của bài mẫu không có giá trị này | Thêm trạng thái thứ 10 vào bảng chuyển | K |
| A-13 | Thợ bấm Nhận sau khi đề nghị QUA_HAN mà đơn vẫn CHO_CU_THO → vẫn cho nhận, ghi "nhận muộn" | Hạn 15 phút để cảnh báo, không để chặn | `PhanCongDAO.nhan_viec` (P3) | K |
| A-14 | Gợi ý thợ: kỹ năng chứa dịch vụ yêu cầu **hoặc** dịch vụ cùng loại thiết bị | Bảng kỹ năng ban đầu chưa đủ chi tiết | `ThoDAO.goi_y_tho` (P3) | K |
| A-15 | Tổng đài ghi "thợ đã đồng ý qua điện thoại" → PhanCong DA_NHAN trực tiếp | Khớp cách làm hiện tại | Ẩn nút ở UC04 | K |
| A-16 | `lam_tron_nghin` làm tròn giảm giá VIP tới 1.000 đ gần nhất | Thu tiền mặt thuận tiện | `tinh_tien.py` | K |
| A-17 | OI-01: một đơn = một địa chỉ + một dịch vụ yêu cầu, nhiều thiết bị cùng loại | SRS còn mở | Quy trình UC02 | K |
| A-18 | OI-02: giảm VIP áp cho tiền công | SRS còn mở | `VIP_PHAM_VI_GIAM` | K |
| A-19 | OI-03: vai trò QUAN_TRI gán cho tổ trưởng tổng đài | Giám đốc đề xuất | Gán vai trò | K |
| A-20 | OI-04: thợ tự mua vật tư, `nguoi_ung = THO` | SRS còn mở | Mặc định trường | K |
| A-21 | OI-07: xuất MISA dạng CSV/XLSX cột chung | Chưa có mẫu cột | `tai_chinh/xuat_misa.py` | K |
| A-22 | OI-08: báo giá ≥ 2.000.000 đ chờ tổng đài xác nhận (0 = tắt) | Giảm tranh chấp giá | `NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN` | K |
| A-23 | Khung giờ hẹn cố định 5 khung, đệm di chuyển 30 phút, cảnh báo chờ cử thợ 30 phút, ≥ 1 ảnh khi hoàn thành | Đề xuất trợ giảng | Các khóa `CauHinh` tương ứng | K |
| A-24 | Đổi hẹn khi đơn DA_CO_THO: báo thợ xác nhận lại; trùng lịch thì rút việc (T8) sau khi tổng đài đồng ý | Đề xuất trợ giảng | UC03 (P2–P3) | K |
| A-25 | Thời hạn bảo hành đơn gốc không gia hạn sau khi bảo hành | Đề xuất trợ giảng | UC11 (P5) | K |
| A-26 | Tổng mới vượt báo giá > 10% → cảnh báo "cần khách xác nhận lại" | Đề xuất trợ giảng | UC09 (P4) | K |

## Lựa chọn khi cài đặt (phát sinh theo giai đoạn)

| Mã | GĐ | Nội dung | Lý do | Cách đổi | Đã chốt? |
|---|---|---|---|---|---|
| A-05 | P0 | Các trang đích sau đăng nhập (`/tong-dai/`, `/tho/`, `/ke-toan/doi-soat/`, `/bao-cao/`) tạm là trang "sẽ có ở giai đoạn sau", chỉ yêu cầu đăng nhập | Cần trang đích để kiểm thử chuyển hướng theo vai trò và hai bố cục; màn hình thật thuộc P2–P6 | Thay route trong `config/urls.py` khi làm màn hình thật | K |
| A-06 | P0 | Tên đăng nhập của QUAN_TRI tạo bằng `tao_quan_tri` = số điện thoại; tài khoản này **không** phải superuser Django | SPEC: Django Admin chỉ cho superuser kỹ thuật; đăng nhập chung một kiểu bằng SĐT | Tạo superuser kỹ thuật riêng bằng `createsuperuser` | K |
| A-07 | P0 | `docker-compose.override.yml` (dev) tự nạp khi chạy `docker compose`; trên máy chủ đặt `COMPOSE_FILE=docker-compose.yml` trong `.env` để bỏ qua | SPEC đặt tên tệp dev là override nhưng máy chủ cũng chạy `docker compose up` | Bỏ dấu `#` dòng `COMPOSE_FILE` trong `.env` | K |
| A-08 | P0 | Nhật ký thao tác chỉ-thêm được chặn ở tầng ứng dụng (mô hình + QuerySet), chưa có trigger CSDL; người dùng có nhật ký không xóa được (PROTECT) | Đơn giản, đủ cho NFR06 khi mọi ghi đi qua Django | Thêm trigger PostgreSQL chặn UPDATE/DELETE trên `tblNhatKy` | K |
| A-09 | P0 | `make test`/`make check` chạy trong container (Python 3.12 + PostgreSQL 16); chạy trên máy: `make check RUN=` với CSDL dev ở cổng 5433 | Một môi trường kiểm thử thống nhất, đúng phiên bản SPEC | Biến `RUN` trong Makefile | K |
| A-27 | P0 | Tham số `CauHinh` mặc định nạp bằng migration dữ liệu (không ghi đè giá trị đã sửa); thiếu bản ghi thì `cau_hinh()` dùng giá trị trong `MAC_DINH` | Quản trị sửa được ngay trên giao diện (P1) | `apps/he_thong/cau_hinh.py` | K |
| A-28 | P0 | Không dùng `dj-database-url` riêng; `django-environ` đọc `DATABASE_URL` | Bớt một phụ thuộc trùng chức năng | Thêm lại nếu cần | K |
| A-29 | P0 | Khóa tài khoản sau 5 lần sai (`django-axes`), PIN thợ, đổi PIN lần đầu, ghi nhớ đăng nhập 30 ngày, phân quyền theo ma trận 3.1 để sang P1 | SPEC 15 xếp UC01 ở P0–P1; P0 chỉ yêu cầu trang đăng nhập | — | K |
