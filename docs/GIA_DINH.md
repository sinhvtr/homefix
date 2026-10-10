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
| A-29 | P0 | Khóa tài khoản sau 5 lần sai, PIN thợ, đổi PIN lần đầu, ghi nhớ 30 ngày, phân quyền 3.1 để sang P1 (**đã làm ở P1**) | SPEC 15 xếp UC01 ở P0–P1 | — | K |
| A-30 | P1 | Thêm trường `NguoiDung.phai_doi_mat_khau` (không có trong bảng 5.2). Bật khi quản trị cấp/đặt lại mật khẩu hoặc PIN; middleware buộc đổi trước khi dùng chức năng khác | UC01 yêu cầu "bắt buộc đổi ở lần đăng nhập đầu" nhưng mô hình không có cờ; là trường hỗ trợ, không đổi quan hệ | Bỏ trường + middleware nếu không cần | K |
| A-31 | P1 | **Mã thợ** = `T` + khóa chính 3 chữ số (`T007`), là thuộc tính tính toán, không thêm cột | SPEC dùng "mã thợ" trong mã phiếu đối soát và xuất MISA nhưng lớp `Tho` không có trường mã | Thêm cột `ma` vào `Tho` nếu công ty đã có mã thợ riêng | K |
| A-32 | P1 | Nhập Excel **tất cả hoặc không**: có dòng lỗi thì không ghi dòng nào, báo lỗi theo số dòng. Thợ: SĐT đã có → lỗi (không cập nhật). Bảng giá: mã đã có → cập nhật (đổi giá ghi `SUA_GIA`), mã mới → thêm. Ô SĐT kiểu số còn 9 chữ số → tự thêm số 0 đầu | Tránh nhập dở dang khó lần lại; Excel hay làm mất số 0 đầu | `apps/danh_muc/nhap_excel.py` | K |
| A-33 | P1 | Dữ liệu mẫu nhận diện bằng tiền tố SĐT `0900` (người dùng, thợ, khách) và mã khu vực/dịch vụ mẫu. `xoa_du_lieu_mau --xac-nhan`: người dùng mẫu đã có nhật ký (chỉ-thêm) thì **khóa** thay vì xóa; dịch vụ/khu vực mẫu đang được dữ liệu thật dùng thì giữ. Mật khẩu mẫu không bắt buộc đổi để thử nhanh. Lệnh đặt ở app `danh_muc`, P2+ mở rộng thêm đơn | Nhật ký không được xóa (NFR06); không xóa nhầm dữ liệu thật | `apps/danh_muc/du_lieu_mau.py` | K |
| A-34 | P1 | `django-axes` khóa **theo tài khoản** (không theo IP); 15 phút tính từ **lần thử sai cuối** (thử lại khi đang khóa thì chờ thêm); mọi cách gõ SĐT của cùng tài khoản dùng chung bộ đếm. Tắt cảnh báo `axes.W006` | Sau tunnel mọi yêu cầu chung một IP — khóa theo IP sẽ khóa cả văn phòng | `AXES_*` trong `config/settings/base.py` | K |
| A-35 | P1 | Tài khoản thợ chỉ tạo ở Danh mục → Thợ (đồng thời tạo `NguoiDung` THO và `Tho`); màn hình Người dùng không tạo hay đổi sang/từ vai trò THO; quản trị không tự khóa, không tự đổi vai trò của mình | Giữ 1–1 giữa `Tho` và `NguoiDung`; tránh tự khóa mất quyền quản trị | `NguoiDungDAO` | K |
| A-36 | P1 | "Dịch vụ đã dùng" ở P1 = có thợ mang kỹ năng đó; từ P2 thêm tham chiếu từ đơn/hạng mục (khóa ngoại PROTECT). Khu vực không xóa khi còn địa chỉ hoặc thợ phụ trách. Xóa khách (chỉ QT) kéo theo địa chỉ, thiết bị; bị chặn khi đã có đơn (P2) | UC13: "không xóa dịch vụ đã dùng, chỉ ngừng áp dụng" | `DichVuDAO.da_duoc_dung` | K |
| A-37 | P1 | Mật khẩu tạm (văn phòng) và PIN (thợ) do hệ thống sinh ngẫu nhiên, **hiện một lần** cho quản trị; thông điệp lưu ở session phía máy chủ, không ở cookie | Không để quản trị tự đặt mật khẩu dễ đoán; không lộ bí mật qua cookie | `MESSAGE_STORAGE`, `mat_khau.py` | K |
| A-38 | P1 | OI-05: kế toán, giám đốc thấy SĐT khách dạng ẩn bớt (`090****123`) ở danh mục khách hàng; tổng đài, quản trị thấy đủ | Hai vai trò này không cần gọi khách | Bộ lọc `an_sdt` trong template | K |
| A-39 | P1 | VIP thủ công bắt buộc nhập lý do; bỏ VIP thủ công → về THUONG cho đến khi tác vụ đêm BR07 xét lại theo số đơn. `loai_khach` không sửa tay trên form. Chức năng gộp hai hồ sơ trùng số [COULD] chưa làm | BR07; giữ phạm vi v1 | `KhachHangDAO` | K |
| A-40 | P1 | Mỗi khách luôn có đúng một địa chỉ mặc định (ràng buộc CSDL có điều kiện); địa chỉ đầu tiên tự là mặc định, xóa địa chỉ mặc định thì địa chỉ còn lại lên thay | UC02 cần địa chỉ mặc định để chọn nhanh | `DiaChiDAO` | K |
| A-41 | P1 | Ruff bỏ quy tắc E501; độ dài dòng do `ruff format` kiểm soát | Chuỗi hiển thị tiếng Việt dài không ngắt được | `[tool.ruff.lint] ignore` | K |
| A-42 | P2 | `bat_dau_cu_tho()` (SPEC 5.2 chỉ nêu tên) = khởi tạo đơn đã chốt lịch (T2). `khoi_tao(da_chot_lich)` chọn T1/T2; lịch hẹn của T2 do `TiepNhanDAO` tạo trong cùng giao dịch | LichHen thuộc app tầng trên, gói lõi không được import | `DonSuaChua.bat_dau_cu_tho` | K |
| A-43 | P2 | Mỗi dòng bảng chuyển có một **sự kiện riêng**; khi SPEC phân nhánh theo điều kiện (T1/T2, T4/T5, T9/T10, T11/T12) phương thức nghiệp vụ xét điều kiện rồi chọn sự kiện. T14 là một dòng với tập nguồn = nhóm "Đang xử lý" | Tra bảng theo cặp (trạng thái, sự kiện) là duy nhất, dễ kiểm thử mọi dòng | `don_sua_chua/trang_thai.py` | K |
| A-44 | P2 | Phương thức nghiệp vụ tự lưu đơn; DAO bọc `transaction.atomic()`, khóa dòng đơn, ghi nhật ký `DOI_TRANG_THAI` (trạng thái trước/sau + mã dòng T…). `save()` từ chối mọi thay đổi `trang_thai` không đi qua phương thức nghiệp vụ. Tác vụ nền ghi nhật ký với người dùng = trống ("Hệ thống") | CLAUDE.md: trạng thái chỉ đổi qua bảng CHUYEN_TRANG_THAI | `DonSuaChua.save`, `ghi_doi_trang_thai` | K |
| A-45 | P2 | Đổi hẹn chỉ khi đơn `CHO_CU_THO` hoặc `DA_CO_THO` (đã có lịch, thợ chưa đến). Thông báo thợ xác nhận lại khi đơn đã có thợ: làm ở P3 cùng kênh thông báo | Sau khi thợ đến nơi không còn ý nghĩa đổi hẹn | `DUOC_DOI_HEN` | K |
| A-46 | P2 | Bảng đơn: không chọn ngày → mọi đơn đang xử lý; chọn ngày → theo ngày của lịch hiệu lực, đơn chưa có lịch theo ngày tiếp nhận. "Hoàn thành/hủy hôm nay" theo thời điểm cập nhật cuối. Nhãn "Chờ cử thợ > 30 phút" và các việc cần làm còn lại (cần cử lại, báo giá chờ xác nhận, hẹn trong 2 giờ chưa có thợ) làm ở P3/P4 | SPEC 4: UC06 P2 cơ bản, P3 cảnh báo | `DonSuaChuaDAO.bang_don_trong_ngay` | K |
| A-47 | P2 | Việc cần làm "Gọi lại khách" (BR08) là danh sách dẫn xuất: đơn `CHO_XAC_NHAN_LICH` đã nhắc ≥ 1 lần — không thêm bảng. Tin nhắn mẫu kèm theo dùng mẫu cố định trong mã (SPEC chỉ cấu hình mẫu xác nhận lịch) | Không thêm mô hình ngoài SPEC | `tiep_nhan_dieu_phoi/tin_nhan.py` | K |
| A-48 | P2 | T6 (đề nghị khách đổi lịch) đặt lại bộ đếm nhắc BR08 (`so_lan_nhac_xac_nhan = 0`, mốc 24 giờ tính từ lúc đề nghị) | Đơn quay lại chờ xác nhận lịch như đơn mới | `DonSuaChua.de_nghi_doi_lich` | K |
| A-49 | P2 | T10 tạo một dòng CONG: số lượng = số thiết bị gắn với đơn (tối thiểu 1), đơn giá = đơn giá tham khảo của dịch vụ | Vệ sinh tính theo máy | `DonSuaChua.tho_den_noi` | K |
| A-50 | P2 | Tổng tạm tính ở T11/T12/T15 = Σ thành tiền các dòng khách chịu, **chưa trừ VIP** — P4 thay bằng `tinh_tien.py` (mục 7.2). T13 với phí kiểm tra > 0 tạo dòng `PHI_KHAC` | `tinh_tien.py` thuộc P4 | `tong_tien_khach_tam_tinh` | K |
| A-51 | P2 | Tiếp nhận: SĐT khớp số chính hoặc số phụ của khách; khách đã có tên thì giữ tên cũ (người gọi có thể khác chủ nhà), chỉ bổ sung khi đang trống. Chọn dịch vụ bằng danh sách nhóm theo loại thiết bị kèm ô lọc theo tên (đoạn JS nhỏ trong trang, chưa cần Alpine) | Ít thao tác, không phụ thuộc thư viện ngoài | `TiepNhanDAO`, `gd_tiep_nhan.html` | K |
| A-52 | P2 | Mã đơn quá 999 đơn/ngày dùng 4 chữ số (`HF261010-1000`) — vẫn vừa Char(16) | Không giới hạn số đơn | `sinh_ma_don` | K |
| A-53 | P2 | Kế toán, giám đốc xem chi tiết đơn ở chế độ chỉ đọc, SĐT khách ẩn bớt; giám đốc xem bảng đơn chỉ đọc; kế toán không vào bảng đơn | Ma trận 3.1 (Báo cáo: TĐ chỉ bảng đơn; KT tài chính) | `XEM_DON`, `XEM_BANG_DON` | K |
| A-54 | P2 | Dữ liệu mẫu ~60 đơn ở mọi trạng thái (SPEC 14.4) nạp khi đủ PhanCong, ThanhToan, PhieuBaoHanh (P5). `xoa_du_lieu_mau` đã xóa cả đơn của khách mẫu | Đơn ở các trạng thái sau cần mô hình của P3–P5 | `apps/danh_muc/du_lieu_mau.py` | K |
