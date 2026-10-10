# HomeFix Ops v1 — Đặc tả để Claude Code sinh mã nguồn

> **Phiên bản đặc tả:** 1.0 · **Ngày:** 10/10/2026 · **Người lập:** TS. Vũ Trọng Sinh (Khoa CNTT1 – PTIT), trợ giảng Claude
> **Nguồn:** SRS tham chiếu HomeFix Ops (N07-SRS v1.0), bài mẫu Tài liệu phân tích, slide Tuần 8–12 môn Phân tích thiết kế HTTT.
> **Mục đích:** triển khai thử nghiệm **miễn phí, tự host tại nhà** bản v1 của hệ thống quản lý đơn sửa chữa tại nhà HomeFix.

---

## 0. Cách dùng file này với Claude Code

1. Tạo thư mục rỗng `homefix/`, chép file này vào thành `homefix/SPEC.md`.
2. Tạo `homefix/CLAUDE.md` với nội dung ở **Phụ lục A** (quy ước làm việc ngắn gọn, Claude Code đọc mỗi phiên).
3. Mở Claude Code trong thư mục đó, gõ lệnh khởi động:

   ```
   Đọc SPEC.md và CLAUDE.md. Thực hiện Giai đoạn P0 theo mục 15.
   Xong thì chạy toàn bộ kiểm thử, báo cáo kết quả theo "Tiêu chí nghiệm thu" của P0 rồi dừng lại chờ tôi.
   ```

4. Lặp lại cho P1 → P6. **Không** cho Claude Code làm nhiều giai đoạn trong một lượt: mỗi giai đoạn kết thúc bằng kiểm thử xanh và một commit.

### Quy ước nhãn trong đặc tả

| Nhãn | Ý nghĩa |
|---|---|
| **[SRS]** | Lấy từ SRS tham chiếu / bài mẫu phân tích đã dùng trong môn học. Không tự ý đổi. |
| **[ĐX]** | Đề xuất của trợ giảng cho v1, chưa có trong SRS. Cài đặt nhưng **phải cấu hình được** và ghi vào `docs/GIA_DINH.md`. |
| **[OI-xx]** | Phụ thuộc vấn đề còn mở trong SRS. v1 chọn một phương án mặc định, đặt thành tham số cấu hình. |
| **MUST / SHOULD / COULD** | Mức ưu tiên trong v1. |

---

## 1. Bối cảnh nghiệp vụ

**HomeFix** là công ty dịch vụ sửa chữa, vệ sinh thiết bị gia dụng tại nhà ở Hà Nội (điều hòa, máy giặt, tủ lạnh, bình nóng lạnh, điện nước…). Quy mô [SRS]: khoảng 3 nhân viên tổng đài, ~40 thợ (cộng tác viên và chính thức), 1 kế toán, 1 giám đốc; 12–15 lượt cử thợ/ngày, mùa cao điểm 30–40 lượt/ngày.

**Hiện trạng (AS-IS):** đơn nhận qua điện thoại và Zalo, ghi vào file Excel lộn xộn và sổ tay; cử thợ qua nhóm Zalo ("ai nhận thì nhận"); không có trạng thái đơn; tiền thợ thu của khách đối soát thủ công, công nợ thợ tồn 12–15 triệu đồng; khoảng 15% đơn không cử được thợ; một ứng dụng năm 2025 dùng 6 tuần rồi bỏ vì thợ phải nhập quá nhiều.

**Mục tiêu v1 (TO-BE):**
- Mỗi yêu cầu của khách thành **một đơn có mã và trạng thái rõ ràng**.
- Tổng đài **cử thợ bằng danh sách gợi ý** (hệ thống chỉ gợi ý, người quyết định là tổng đài).
- Thợ **nhận việc, báo giá, báo hoàn thành trên điện thoại** với rất ít thao tác.
- Kế toán **đối soát tiền thợ đã thu** theo kỳ.
- Giám đốc **xem báo cáo vận hành, doanh thu, tỷ lệ làm lại**.

**Ngoài phạm vi v1 [SRS – Won't]:** ứng dụng cho khách tự đặt lịch, định vị GPS thợ, trợ lý ảo, tích hợp trực tiếp phần mềm MISA (v1 chỉ xuất file), thanh toán trực tuyến, tính lương/hoa hồng thợ.

---

## 2. Lựa chọn công nghệ cho v1 và lý do

### 2.1. Quyết định

| Hạng mục | Lựa chọn | Lý do chính |
|---|---|---|
| Ngôn ngữ, framework | **Python 3.12 + Django 5.2 LTS** | Có sẵn xác thực, phân quyền, ORM, migration, form, trang quản trị dự phòng; một người vận hành được; LTS hỗ trợ dài hạn; dễ gắn mô-đun AI ở giai đoạn 2 (gợi ý thợ, phân loại sự cố từ tin nhắn). |
| Giao diện | **Django templates + HTMX 2 + Alpine.js**, CSS **Tailwind** qua `django-tailwind-cli` (không cần Node) | Không phải viết SPA riêng; trang nhẹ cho mạng 4G yếu của thợ (NFR02). |
| Ứng dụng thợ | **PWA** (cài lên màn hình chính từ trình duyệt) | Không tốn phí kho ứng dụng, không cần build Android/iOS; một mã nguồn. |
| CSDL | **PostgreSQL 16** | Hỗ trợ **ràng buộc duy nhất có điều kiện** (dùng để chặn ở mức CSDL: một đơn chỉ một lịch hẹn hiệu lực, một phân công đã nhận — BR03), `SELECT … FOR UPDATE`, JSON cho nhật ký. |
| Tác vụ nền, lịch định kỳ | **django-q2** dùng chính PostgreSQL làm hàng đợi | Không cần Redis/RabbitMQ; đủ cho kiểm tra quá hạn 15 phút (BR02), nhắc 24 giờ (BR08), đóng đơn hết bảo hành (BR05). |
| Thông báo cho thợ | **Web Push** (`pywebpush`, khóa VAPID tự sinh) + **Telegram Bot** (dự phòng) + thông báo trong ứng dụng | Đều miễn phí. Zalo OA/ZNS và SMS **có phí** → để sẵn adapter rỗng cho v2. |
| Liên hệ khách | Tổng đài gọi/nhắn Zalo **thủ công**; hệ thống sinh **tin nhắn mẫu để sao chép** và **việc cần làm** | Không phát sinh chi phí; khớp quy trình hiện tại. |
| Xuất file | `openpyxl` (XLSX), `csv` | Báo cáo, dữ liệu đối soát cho kế toán nhập MISA. |
| Ảnh hiện trường | Pillow (nén ≤ 1600px, JPEG 80%), lưu ổ đĩa, phục vụ qua view có kiểm tra quyền | Không lộ ảnh/địa chỉ khách ra ngoài (NFR04). |
| Kiểm thử | `pytest`, `pytest-django`, `factory_boy`, `freezegun` | Kiểm thử quy tắc theo thời gian (15 phút, 24 giờ, hết hạn bảo hành). |
| Chất lượng mã | `ruff` (lint + format) | Một công cụ, nhanh. |
| Đóng gói, chạy | **Docker Compose**: `db`, `web` (gunicorn), `worker` (qcluster), `backup` | Chạy y hệt trên máy cá nhân, mini PC, máy cũ. |
| Đưa ra Internet miễn phí | **Tailscale Funnel** (URL `https://<may>.<tailnet>.ts.net`, không cần tên miền) hoặc **Cloudflare Tunnel** (nếu đã có tên miền trên Cloudflare) | Không mở cổng router, có HTTPS (bắt buộc cho PWA và Web Push). |

### 2.2. Đối chiếu với thiết kế J2EE dùng trong môn học

Mã nguồn v1 **giữ nguyên tên lớp, tên bảng và tên phương thức nghiệp vụ** của mô hình thiết kế trong môn học để sinh viên truy vết được từ biểu đồ sang mã.

| Thiết kế môn học (J2EE ba tầng) | Hiện thực v1 (Django) |
|---|---|
| Gói `model`: `DonSuaChua.java`, `Tho.java`… (có get/set) | `models.py`: `class DonSuaChua(models.Model)`… Trạng thái **chỉ đổi qua phương thức nghiệp vụ** (`don.giao_cho_tho(...)`), không gán `trang_thai` trực tiếp ở view. |
| Gói `dao`: lớp cha `DAO` giữ `Connection`; `DonSuaChuaDAO`, `PhanCongDAO`, `ThoDAO`; giao dịch trong DAO (`setAutoCommit`, `commit/rollback`) | `dao.py` trong từng app: `DonSuaChuaDAO`, `PhanCongDAO`, `ThoDAO`… mỗi phương thức ghi bọc `transaction.atomic()`. Tên phương thức giữ theo Tuần 12: `lay_don_cho_phan_cong()`, `goi_y_tho(don)`, `giao_viec(pc) -> bool`. |
| Gói `view`: `gdPhanCong.jsp`, `gdTiepNhan.jsp` | `views.py` + template `gd_phan_cong.html`, `gd_tiep_nhan.html`. View **không viết truy vấn ORM phức tạp**, chỉ gọi DAO. |
| `ZaloSMSAdapter` | `thong_bao/adapters.py`: giao diện `KenhThongBao`; cài `WebPushKenh`, `TelegramKenh`, `ConsoleKenh`; `ZaloZnsKenh` để rỗng (v2). |
| MySQL, bảng `tblDonSuaChua`, khóa ngoại `idDiaChi` | PostgreSQL, `Meta.db_table = "tblDonSuaChua"`; cột theo kiểu Python `snake_case` (`dia_chi_id`). Bảng ánh xạ cột đầy đủ sinh tự động vào `docs/ANH_XA_BANG.md` (lệnh ở mục 15-P6). |
| Triển khai: trình duyệt/app → Tomcat (`homefix.war`) → MySQL | Trình duyệt/PWA → Tailscale/Cloudflare (HTTPS) → gunicorn (Django) → PostgreSQL; `worker` chạy tác vụ nền. |

> Nếu sau này cần bản Java để làm mẫu chấm cho sinh viên, dùng lại nguyên mục 5–10 của đặc tả này (mô hình, trạng thái, quy tắc, ca sử dụng), chỉ thay mục 2 và 14.

---

## 3. Tác nhân, vai trò và phân quyền

| Vai trò (mã) | Người dùng thực tế | Thiết bị chính |
|---|---|---|
| `QUAN_TRI` | Tổ trưởng tổng đài [OI-03: giám đốc đề xuất, chưa chính thức] | Máy tính |
| `TONG_DAI` | Nhân viên tổng đài | Máy tính |
| `THO` | Thợ sửa chữa | Điện thoại (PWA) — 24/27 Android, 3/27 iPhone [SRS khảo sát] |
| `KE_TOAN` | Kế toán | Máy tính |
| `GIAM_DOC` | Giám đốc | Máy tính, điện thoại |

Một người dùng có **đúng một** vai trò. `QUAN_TRI` có mọi quyền của `TONG_DAI`.

### 3.1. Ma trận quyền (C = tạo, R = xem, U = sửa, — = không)

| Đối tượng / chức năng | QUAN_TRI | TONG_DAI | THO | KE_TOAN | GIAM_DOC |
|---|---|---|---|---|---|
| Người dùng, cấu hình hệ thống | CRUD | — | — | — | R |
| Danh mục: dịch vụ, bảng giá, khu vực | CRUD | R | R (dịch vụ) | R | R |
| Hồ sơ thợ | CRUD | R | R/U (của mình: kênh thông báo, PIN) | R | R |
| Khách hàng, địa chỉ, thiết bị | CRUD | CRU | R **chỉ khách của đơn đã nhận** (NFR04) | R | R |
| Đơn sửa chữa | CRU + hủy | CRU + hủy | R/U đơn được giao (theo trạng thái) | R | R |
| Phân công (cử thợ) | CRU | CRU | U (nhận/từ chối của mình) | — | R |
| Báo giá, hạng mục | R/U | R | CRU (đơn của mình) | R | R |
| Thanh toán (tiền thợ thu) | R | R | C (đơn của mình) | RU | R |
| Phiếu đối soát | R | — | R (của mình) | CRU | R |
| Báo cáo | R | R (bảng đơn) | — | R (tài chính) | R |
| Nhật ký thao tác | R | — | — | — | R |

Kiểm tra quyền **ở cả view lẫn DAO** (DAO nhận tham số `nguoi_dung` cho các thao tác ghi). Kiểm thử phân quyền là bắt buộc (NFR04: 100% truy cập trái phép bị từ chối).

---

## 4. Phạm vi v1 theo ca sử dụng [SRS]

| Mã | Ca sử dụng | Tác nhân chính | Ưu tiên SRS | Giai đoạn v1 |
|---|---|---|---|---|
| UC01 | Đăng nhập và phân quyền | Mọi người dùng | M | P0–P1 |
| UC02 | Tiếp nhận và tạo đơn dịch vụ | Tổng đài | M | P2 |
| UC03 | Lập lịch hẹn và xác nhận với khách (extend UC02) | Tổng đài | M | P2 |
| UC04 | Điều phối, cử thợ cho đơn (include UC05) | Tổng đài | M | P3 |
| UC05 | Tra cứu năng lực và lịch bận của thợ | — (UC04 dùng lại) | M | P3 |
| UC06 | Theo dõi bảng đơn trong ngày | Tổng đài, giám đốc | M | P2 (cơ bản), P3 (cảnh báo) |
| UC07 | Nhận / từ chối đơn được giao | Thợ | M | P3 |
| UC08 | Lập báo giá và ghi nhận xác nhận của khách (extend UC07) | Thợ | M | P4 |
| UC09 | Ghi nhận hoàn thành và tiền đã thu (include UC10) | Thợ | M | P4 |
| UC10 | Ghi nhận vật tư sử dụng cho đơn | Thợ | S | P4 |
| UC11 | Tạo và theo dõi đơn bảo hành / làm lại (include UC04) | Tổng đài | M | P5 |
| UC12 | Đối soát tiền thợ đã thu | Kế toán | M | P5 |
| UC13 | Quản lý hồ sơ thợ, khách hàng, danh mục dịch vụ | Quản trị (tổ trưởng tổng đài) | M | P1 |
| UC14 | Xem báo cáo vận hành và doanh thu | Giám đốc | S | P6 |

---

## 5. Mô hình miền (lớp thực thể → bảng)

Quy ước chung:
- **Tiền:** `BigIntegerField`, đơn vị **đồng**, không bao giờ dùng `float`. Hiển thị `1.250.000 đ`.
- **Thời gian:** `USE_TZ=True`, `TIME_ZONE="Asia/Ho_Chi_Minh"`; hiển thị `dd/MM/yyyy HH:mm`.
- **Số điện thoại:** chuẩn hóa về dạng `0xxxxxxxxx` (10 chữ số), chấp nhận nhập `+84…`, có dấu cách/chấm.
- Mọi bảng có `tao_luc`, `cap_nhat_luc` (lớp cha trừu tượng `MoHinhCoBan`).
- Liệt kê dùng `models.TextChoices` với **mã không dấu viết hoa** và **nhãn tiếng Việt** (nhãn khớp tên trạng thái SRS).

### 5.1. Sơ đồ quan hệ (rút gọn)

```
KhuVuc 1───* DiaChi *───1 KhachHang
                │1
                ├───* ThietBi
                └───* DonSuaChua *───* ThietBi
DonSuaChua 1──◆* HangMucSuaChua *───0..1 DichVu
DonSuaChua 1──◆* LichHen          (tối đa 1 lịch HIEU_LUC)
DonSuaChua 1───* PhanCong *───1 Tho   (tối đa 1 phân công DA_NHAN)
DonSuaChua 1───* ThanhToan *───0..1 PhieuDoiSoat *───1 Tho
DonSuaChua 1───0..1 PhieuBaoHanh
DonSuaChua 0..1───* DonSuaChua      (đơn bảo hành → đơn gốc)
DonSuaChua *───1 DichVu (dịch vụ yêu cầu)
Tho *───* DichVu (kỹ năng)   Tho *───* KhuVuc (khu vực phụ trách)
Tho 1───1 NguoiDung
```

### 5.2. Chi tiết từng lớp

**`NguoiDung`** (kế thừa `AbstractUser`) — `tblNhanVien` [SRS: NhanVien]
| Trường | Kiểu | Ràng buộc / ghi chú |
|---|---|---|
| username | (giữ của Django) | Đặt = số điện thoại cho thợ |
| ho_ten | Char(100) | bắt buộc |
| so_dien_thoai | Char(10) | duy nhất, chuẩn hóa |
| vai_tro | TextChoices | `QUAN_TRI, TONG_DAI, THO, KE_TOAN, GIAM_DOC` |
| dang_hoat_dong | (is_active) | khóa tài khoản thay vì xóa |

**`KhuVuc`** — `tblKhuVuc` [ĐX, slide 10.18 cho phép]
| ma (Char 20, duy nhất) | ten (Char 100) | ghi_chu |

**`KhachHang`** — `tblKhachHang`
| Trường | Kiểu | Ràng buộc / ghi chú |
|---|---|---|
| ho_ten | Char(100) | **cho phép trống** (UC02: lưu đơn khi thiếu tên) |
| so_dien_thoai | Char(10) | duy nhất, bắt buộc — khóa tra cứu chính |
| so_dien_thoai_phu | Char(10) | tùy chọn |
| loai_khach | `THUONG, VIP` | BR07 |
| vip_thu_cong | Bool | giám đốc giới thiệu → VIP bất kể số lần |
| ly_do_vip | Char(200) | |
| ghi_chu | Text | |
| *(dẫn xuất)* so_lan_su_dung_trong_nam | property/annotate | số đơn `HOAN_THANH` hoặc `DA_DONG` trong 365 ngày gần nhất |

**`DiaChi`** — `tblDiaChi`
| khach_hang FK | dia_chi_chi_tiet Char(255) bắt buộc | khu_vuc FK bắt buộc | ghi_chu_duong_di Text | la_mac_dinh Bool |

**`ThietBi`** — `tblThietBi`
| dia_chi FK | loai_thiet_bi TextChoices (`DIEU_HOA, MAY_GIAT, TU_LANH, BINH_NONG_LANH, DIEN_NUOC, KHAC`) | hang_san_xuat Char(50) | model Char(50) | vi_tri_lap Char(100) | ghi_chu |

**`DichVu`** — `tblDichVu`
| Trường | Kiểu | Ghi chú |
|---|---|---|
| ma | Char(20) duy nhất | |
| ten_dich_vu | Char(150) | |
| nhom_dich_vu | `VE_SINH_BAO_DUONG`, `SUA_CHUA_THAY_VAT_TU` | quyết định luồng báo giá (BR06) và thời hạn bảo hành (BR05) |
| loai_thiet_bi | như ThietBi | dùng lọc thợ đúng nghề |
| don_gia_tham_khao | BigInteger | bảng giá; với nhóm sửa chữa là giá "từ…" |
| don_vi_tinh | Char(20) | "máy", "lần", "điểm"… |
| thoi_han_bao_hanh_ngay | PositiveInteger | mặc định 7 (vệ sinh) / 90 (sửa chữa) [SRS BR05] |
| dang_ap_dung | Bool | |

**`Tho`** — `tblTho`
| Trường | Kiểu | Ghi chú |
|---|---|---|
| nguoi_dung | OneToOne NguoiDung | |
| ho_ten, so_dien_thoai | | sao chép từ người dùng để tra cứu nhanh |
| hinh_thuc | `CONG_TAC_VIEN, CHINH_THUC` | |
| ky_nang | M2M DichVu | "đúng nghề" (BR04) |
| khu_vuc_phu_trach | M2M KhuVuc | xếp hạng gợi ý |
| dang_nhan_viec | Bool | thợ tự bật/tắt "Sẵn sàng nhận việc" |
| nghi_den | DateTime null | báo nghỉ đến thời điểm |
| kenh_thong_bao | `WEB_PUSH, TELEGRAM` | |
| telegram_chat_id | Char null | gắn qua liên kết mời bot |
| ghi_chu | Text | |

**`DonSuaChua`** — `tblDonSuaChua` (lớp trung tâm)
| Trường | Kiểu | Ghi chú |
|---|---|---|
| ma_don | Char(16) duy nhất | `HF` + `yyMMdd` + `-` + số thứ tự 3 chữ số trong ngày, ví dụ `HF261010-007`; sinh bằng bảng đếm có khóa dòng |
| khach_hang | FK | người gọi (có thể khác chủ nhà — chấp nhận theo mô hình) |
| dia_chi | FK | |
| dich_vu_yeu_cau | FK DichVu | dịch vụ chính, quyết định nghề và nhóm |
| thiet_bi | M2M ThietBi | [OI-01] |
| kenh_tiep_nhan | `DIEN_THOAI, ZALO, GIAM_DOC_CHUYEN, KHAC` | |
| mo_ta_su_co | Text | |
| khung_gio_mong_muon | Char(100) | ghi tự do khi chưa chốt lịch |
| trang_thai | TextChoices (mục 6.1) | chỉ đổi qua phương thức nghiệp vụ |
| loai_don | `THUONG, BAO_HANH` | |
| don_goc | FK self null | chỉ với đơn bảo hành |
| nguyen_nhan_bao_hanh | `CHUA_XAC_DINH, TAY_NGHE, VAT_TU` null | BR05 |
| tho | FK Tho null | thợ đang phụ trách (phi chuẩn hóa từ PhanCong `DA_NHAN` để truy vấn nhanh) |
| uu_tien | Bool | đặt tự động khi khách VIP (BR07) |
| so_lan_giuc | PositiveSmallInteger | tổng đài bấm "Khách giục" |
| so_lan_nhac_xac_nhan | PositiveSmallInteger 0–3 | BR08 |
| lan_nhac_cuoi | DateTime null | |
| bao_gia_tong | BigInteger null | chốt khi khách duyệt |
| bao_gia_nguoi_xac_nhan | Char(100) | tên người nhà khách xác nhận |
| bao_gia_xac_nhan_luc | DateTime null | |
| cho_tong_dai_xac_nhan_gia | Bool | [ĐX][OI-08] |
| tong_tien_phai_thu | BigInteger null | chốt khi hoàn thành |
| ly_do_huy | Text | |
| nguoi_tao | FK NguoiDung | |
| ngay_tiep_nhan | DateTime | mặc định now |
| canh_bao_chua_cu_duoc | Bool + `ly_do_chua_cu_duoc` Text | xem ghi chú 6.1 |

Phương thức nghiệp vụ bắt buộc (mỗi phương thức kiểm tra trạng thái nguồn, ném `ChuyenTrangThaiKhongHopLe` nếu sai): `chot_lich(lich)`, `bat_dau_cu_tho()`, `giao_cho_tho(phan_cong)`, `huy_phan_cong_hien_tai(ly_do)`, `tho_den_noi()`, `ghi_bao_gia(...)`, `khach_duyet_gia(nguoi, luc)`, `khach_tu_choi_gia(ly_do)`, `hoan_thanh(so_tien, ...)`, `mo_bao_hanh(don_bh)`, `ket_thuc_bao_hanh()`, `huy(ly_do, nguoi)`, `dong()`; thuộc tính `tong_tien` (tính từ hạng mục, mục 7.2), `thieu_thong_tin` (thiếu tên khách hoặc chưa có lịch hiệu lực).

**`HangMucSuaChua`** — `tblHangMucSuaChua`
| Trường | Kiểu | Ghi chú |
|---|---|---|
| don | FK | xóa theo đơn (hợp thành) |
| loai | `CONG, VAT_TU, PHI_KHAC` | |
| dich_vu | FK null | dòng tiền công lấy từ bảng giá |
| thiet_bi | FK null | |
| mo_ta | Char(255) | |
| so_luong | Decimal(10,2) | > 0 |
| don_gia_thuc_te | BigInteger | giá bán cho khách |
| gia_mua | BigInteger null | chỉ `VAT_TU` (UC10) |
| co_hoa_don | Bool | chỉ `VAT_TU` |
| nguoi_ung | `THO, CONG_TY` | chỉ `VAT_TU` [OI-04: mặc định THO] |
| la_bao_gia | Bool | dòng thuộc báo giá đã được khách duyệt |
| ben_chiu_chi_phi | `KHACH, THO, CONG_TY` | đơn bảo hành: không thu khách (BR05) |
| *(dẫn xuất)* thanh_tien | | `so_luong × don_gia_thuc_te`, làm tròn đến đồng |

**`LichHen`** — `tblLichHen`
| don FK | bat_dau DateTime | ket_thuc DateTime (> bat_dau) | trang_thai `HIEU_LUC, DA_THAY_THE, DA_HUY` | ly_do_doi_hen | nguoi_tao FK |
Ràng buộc CSDL: `UniqueConstraint(fields=["don"], condition=Q(trang_thai="HIEU_LUC"))`. Đổi hẹn = tạo lịch mới, lịch cũ thành `DA_THAY_THE` [SRS].

**`PhanCong`** — `tblPhanCong` (một lượt đề nghị nhận việc gửi một thợ)
| Trường | Kiểu | Ghi chú |
|---|---|---|
| don | FK | |
| tho | FK | |
| nguoi_giao | FK NguoiDung | |
| thoi_diem_giao | DateTime | |
| han_phan_hoi | DateTime | `thoi_diem_giao + THOI_HAN_PHAN_HOI_PHUT` (BR02) |
| trang_thai | `CHO_PHAN_HOI, DA_NHAN, TU_CHOI, QUA_HAN, DA_HUY` | mục 6.2 |
| thoi_diem_phan_hoi | DateTime null | |
| ly_do_tu_choi | `BAN, XA, KHONG_DUNG_CHUYEN_MON, KHAC` + `ghi_chu` | |
| tien_cong_du_kien | BigInteger | chụp từ bảng giá lúc gửi (thợ muốn thấy trước khi nhận — 19/27 [SRS]) |
| giao_qua_dien_thoai | Bool | [ĐX] tổng đài ghi nhận thợ đã đồng ý qua điện thoại → tạo thẳng `DA_NHAN` |
Ràng buộc CSDL: `UniqueConstraint(fields=["don"], condition=Q(trang_thai="DA_NHAN"))` — chặn hai thợ cùng nhận (BR03).

**`ThanhToan`** — `tblThanhToan` (một khoản tiền thợ ghi nhận đã thu của khách)
| don FK | tho FK | so_tien BigInteger ≥ 0 | hinh_thuc `TIEN_MAT, CK_TAI_KHOAN_CONG_TY, CK_TAI_KHOAN_THO` | thoi_diem_thu | trang_thai `CHUA_NOP, DA_NOP, KHONG_CAN_NOP` | phieu_doi_soat FK null | anh_chung_tu (file, tùy chọn) |
`CK_TAI_KHOAN_CONG_TY` → `KHONG_CAN_NOP` ngay khi tạo.

**`PhieuDoiSoat`** — `tblPhieuDoiSoat`
| ma Char duy nhất (`DS-yyMM-<mã thợ>-n`) | tho FK | tu_ngay, den_ngay Date | tong_tien_thu BigInteger | tong_vat_tu_ung BigInteger | so_phai_nop BigInteger (có thể âm = công ty phải trả thợ) | trang_thai `NHAP, DA_CHOT, DA_NOP` | nguoi_lap FK | xac_nhan_luc | ghi_chu |

**`PhieuBaoHanh`** — `tblPhieuBaoHanh`
| ma (`BH-` + mã đơn) | don OneToOne | ngay_bat_dau Date | ngay_het_han Date | dieu_kien Text (sinh từ mẫu theo nhóm dịch vụ) |
*(dẫn xuất)* `con_han = hôm nay ≤ ngay_het_han`.

**Lớp hỗ trợ (không thuộc mô hình phân tích, cần cho vận hành):**
- `NhatKyThaoTac` — `tblNhatKy`: `nguoi_dung FK null, thoi_diem, hanh_dong (Char), doi_tuong (Char: "DonSuaChua:HF261010-007"), du_lieu_truoc JSON, du_lieu_sau JSON, dia_chi_ip`. Chỉ thêm, không sửa, không xóa (NFR06).
- `ThongBao` — `tblThongBao`: `nguoi_nhan FK, tieu_de, noi_dung, duong_dan, da_doc, tao_luc`.
- `DangKyPush` — `tblDangKyPush`: `nguoi_dung FK, endpoint (duy nhất), p256dh, auth, user_agent`.
- `CauHinh` — `tblCauHinh`: `khoa (duy nhất), gia_tri (Char), kieu (INT/BOOL/STR/JSON), mo_ta`. Đọc qua hàm `cau_hinh("KHOA")` có bộ nhớ đệm 60 giây. Giá trị mặc định ở mục 8.2.
- `BoDemMaDon` — `tblBoDemMaDon`: `ngay (duy nhất), so_cuoi`.

---

## 6. Máy trạng thái

### 6.1. `DonSuaChua.trang_thai` [SRS — 9 giá trị]

| Mã | Nhãn hiển thị |
|---|---|
| `CHO_XAC_NHAN_LICH` | Chờ khách xác nhận lịch |
| `CHO_CU_THO` | Chờ cử thợ |
| `DA_CO_THO` | Đã có thợ |
| `CHO_DUYET_GIA` | Chờ khách duyệt giá |
| `DANG_SUA` | Đang sửa |
| `HOAN_THANH` | Hoàn thành |
| `DANG_BAO_HANH` | Đang bảo hành |
| `DA_HUY` | Đã hủy |
| `DA_DONG` | Đã đóng |

Nhóm phức hợp (không lưu, dùng để lọc/kiểm tra): **Đang xử lý** = {CHO_XAC_NHAN_LICH, CHO_CU_THO, DA_CO_THO, CHO_DUYET_GIA, DANG_SUA} (khách còn được hủy); **Đang thực hiện** = {CHO_DUYET_GIA, DANG_SUA}.

**Bảng chuyển trạng thái** — cài thành một bảng dữ liệu duy nhất `CHUYEN_TRANG_THAI` trong `don_sua_chua/trang_thai.py`, mọi phương thức nghiệp vụ tra bảng này; có kiểm thử tham số hóa cho **mọi** dòng và cho các chuyển **không** có trong bảng.

| # | Từ | Sự kiện | Điều kiện | Hành động | Đến | Nguồn |
|---|---|---|---|---|---|---|
| T1 | (đầu) | tạo đơn | chưa chốt lịch | — | CHO_XAC_NHAN_LICH | UC02 |
| T2 | (đầu) | tạo đơn | đã chốt lịch | tạo LichHen | CHO_CU_THO | UC02, UC03 |
| T3 | CHO_XAC_NHAN_LICH | khách chốt khung giờ | — | tạo LichHen | CHO_CU_THO | UC03 |
| T4 | CHO_XAC_NHAN_LICH | sau 24 giờ | đã nhắc < 3 lần | tăng `so_lan_nhac`, tạo việc cần làm | (giữ) | BR08 |
| T5 | CHO_XAC_NHAN_LICH | sau 24 giờ | đã nhắc đủ 3 lần | ghi lý do | DA_HUY | BR08 |
| T6 | CHO_CU_THO | không có thợ phù hợp, tổng đài chọn "Đề nghị khách đổi lịch" | — | lịch hiện tại → DA_HUY | CHO_XAC_NHAN_LICH | UC04 nhánh 2a |
| T7 | CHO_CU_THO | thợ nhận việc | đơn chưa có thợ | gán `tho`, hủy các đề nghị khác | DA_CO_THO | UC04; BR03 |
| T8 | DA_CO_THO | thợ báo bận / tổng đài rút việc | — | PhanCong → DA_HUY, `tho = null` | CHO_CU_THO | [ĐX] A-03 |
| T9 | DA_CO_THO | thợ bấm "Đã đến nơi" | nhóm = SUA_CHUA_THAY_VAT_TU | — | CHO_DUYET_GIA | [ĐX] A-02; BR06 |
| T10 | DA_CO_THO | thợ bấm "Đã đến nơi" | nhóm = VE_SINH_BAO_DUONG | tạo dòng CONG theo bảng giá | DANG_SUA | [ĐX] A-02; BR06 |
| T11 | CHO_DUYET_GIA | khách đồng ý giá | không cần tổng đài xác nhận | chốt báo giá | DANG_SUA | UC08; BR06 |
| T12 | CHO_DUYET_GIA | tổng đài xác nhận giá | `cho_tong_dai_xac_nhan_gia` | chốt báo giá | DANG_SUA | [ĐX][OI-08] |
| T13 | CHO_DUYET_GIA | khách từ chối giá | — | ghi lý do, ghi phí kiểm tra nếu > 0 | DA_HUY | UC08; [ĐX] A-04 |
| T14 | Đang xử lý (mọi con) | khách hủy | — | ghi lý do, hủy lịch & đề nghị đang chờ | DA_HUY | Tổng đài |
| T15 | DANG_SUA | thợ báo hoàn thành | đã nhập tiền thu, có ≥ 1 ảnh | chốt `tong_tien_phai_thu`, tạo ThanhToan, phát hành PhieuBaoHanh | HOAN_THANH | UC09 |
| T16 | HOAN_THANH | tạo đơn bảo hành | phiếu bảo hành còn hạn | — | DANG_BAO_HANH | UC11; BR05 |
| T17 | DANG_BAO_HANH | đơn bảo hành con hoàn thành hoặc bị hủy | — | — | HOAN_THANH | UC11 |
| T18 | HOAN_THANH | hết hạn bảo hành (tác vụ hằng ngày) | — | — | DA_DONG | BR05 |

> **Điểm lệch cần thầy chốt:** đặc tả UC04 ghi hậu điều kiện thất bại là đơn chuyển "Chưa cử được thợ", nhưng danh sách 9 trạng thái của bài mẫu không có giá trị này. v1 **giữ 9 trạng thái** và dùng cờ `canh_bao_chua_cu_duoc` + `ly_do_chua_cu_duoc` trên đơn ở `CHO_CU_THO`; bảng đơn hiển thị nhãn đỏ "Chưa cử được thợ". Đổi thành trạng thái thứ 10 chỉ cần thêm một dòng vào bảng chuyển.

### 6.2. `PhanCong.trang_thai`

| Từ | Sự kiện | Đến |
|---|---|---|
| (đầu) | tổng đài gửi đề nghị | CHO_PHAN_HOI |
| (đầu) | tổng đài ghi "thợ đã đồng ý qua điện thoại" [ĐX] | DA_NHAN |
| CHO_PHAN_HOI | thợ bấm Nhận, đơn còn CHO_CU_THO | DA_NHAN |
| CHO_PHAN_HOI | thợ bấm Nhận, đơn đã có thợ khác | DA_HUY (lý do "Đơn đã có thợ nhận") |
| CHO_PHAN_HOI | thợ bấm Từ chối | TU_CHOI |
| CHO_PHAN_HOI | quá `han_phan_hoi` (tác vụ mỗi phút) | QUA_HAN |
| CHO_PHAN_HOI | thợ khác nhận / tổng đài thu hồi / đơn bị hủy | DA_HUY |
| DA_NHAN | thợ báo bận, tổng đài rút việc, đơn bị hủy | DA_HUY |

Thợ bấm Nhận sau khi đã `QUA_HAN` nhưng đơn vẫn `CHO_CU_THO` → **vẫn cho nhận** [ĐX] (hạn 15 phút là để cảnh báo tổng đài, không để chặn thợ); ghi nhật ký "nhận muộn".

### 6.3. `LichHen.trang_thai`: `HIEU_LUC → DA_THAY_THE` (đổi hẹn) · `HIEU_LUC → DA_HUY` (đơn hủy, T6).
### 6.4. `ThanhToan.trang_thai`: `CHUA_NOP → DA_NOP` (kế toán xác nhận phiếu đối soát). Không có chuyển ngược trừ thao tác "Mở lại phiếu" của kế toán (ghi nhật ký).

---

## 7. Quy tắc nghiệp vụ

### 7.1. Danh sách và cách hiện thực

| Mã | Quy tắc [SRS] | Hiện thực v1 | Kiểm thử bắt buộc |
|---|---|---|---|
| **BR01** | Hệ thống chỉ gợi ý; tổng đài quyết định giao đơn | Không có chức năng tự giao. Gợi ý chỉ là danh sách xếp hạng; chỉ người dùng `TONG_DAI/QUAN_TRI` tạo được `PhanCong`. | Không tồn tại đường đi nào tạo PhanCong không có `nguoi_giao`. |
| **BR02** | Thợ có 15 phút để nhận/từ chối; quá hạn cảnh báo, gợi ý nhóm kế tiếp | `han_phan_hoi`; tác vụ `kiem_tra_qua_han` mỗi phút → `QUA_HAN`; nếu đơn hết đề nghị đang chờ mà vẫn `CHO_CU_THO` → thông báo cho tổng đài đã giao + thẻ "Cần cử lại" trên bảng đơn, mở sẵn danh sách gợi ý loại trừ thợ đã từ chối/quá hạn. | freezegun: +14 phút chưa quá hạn; +15 phút 1 giây → QUA_HAN + có ThongBao. |
| **BR03** | Một đơn một thợ; nhiều thợ cùng nhận → người bấm trước | `PhanCongDAO.nhan_viec()` khóa dòng đơn `select_for_update()`; kiểm tra trạng thái; ràng buộc duy nhất có điều kiện làm lưới an toàn. Người đến sau nhận thông báo "Đơn đã có thợ nhận". | Hai luồng song song (`TransactionTestCase` + threads) → đúng một DA_NHAN. |
| **BR04** | Chỉ gợi ý thợ đúng nghề, không trùng lịch khung giờ hẹn | `ThoDAO.goi_y_tho(don)` lọc: thợ hoạt động, `dang_nhan_viec`, không `nghi_den` qua khung giờ, có `ky_nang` chứa `dich_vu_yeu_cau` **hoặc** dịch vụ cùng `loai_thiet_bi` [ĐX], không có đơn DA_CO_THO/Đang thực hiện mà lịch hiệu lực giao với khung giờ (cộng đệm `DEM_DI_CHUYEN_PHUT`). | Thợ sai nghề, thợ trùng lịch, thợ nghỉ đều không xuất hiện. |
| **BR05** | Bảo hành vệ sinh 7 ngày, sửa chữa 3 tháng; lỗi tay nghề thợ chịu công, lỗi vật tư công ty chịu | Khi hoàn thành: `ngay_het_han = ngày hoàn thành + max(thoi_han_bao_hanh_ngay của các dịch vụ trong đơn)`. Đơn bảo hành: khách trả 0 đ; `ben_chiu_chi_phi` theo `nguyen_nhan_bao_hanh` (TAY_NGHE → THO cho dòng CONG, VAT_TU → CONG_TY). Tác vụ hằng ngày đóng đơn hết hạn. | Hết hạn đúng ngày; đơn bảo hành tổng phải thu = 0. |
| **BR06** | Vệ sinh theo bảng giá; sửa chữa báo giá tại chỗ, khách xác nhận trước | Luồng T9/T10. Không cho chuyển `DANG_SUA` với nhóm sửa chữa khi chưa có báo giá được duyệt. Ngưỡng tổng đài gọi xác nhận [OI-08]: `NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN`. | Gọi `khach_duyet_gia` trên đơn vệ sinh → lỗi; báo giá vượt ngưỡng → cần T12. |
| **BR07** | Khách VIP: ≥ 3 lần/năm hoặc GĐ giới thiệu; ưu tiên trong ngày; giảm 10% tiền công | Tác vụ đêm cập nhật `loai_khach`; tạo đơn cho khách VIP đặt `uu_tien=True` (lên đầu bảng đơn, viền vàng). Giảm giá theo `VIP_TY_LE_GIAM` áp vào phạm vi `VIP_PHAM_VI_GIAM` [OI-02: mặc định `TIEN_CONG`]. | Khách 3 đơn hoàn thành trong 365 ngày → VIP; giảm đúng phạm vi. |
| **BR08** | Đơn chưa chốt lịch nhắc sau 24 giờ; 3 lần không phản hồi thì đóng | Tác vụ mỗi giờ: đơn `CHO_XAC_NHAN_LICH` có `lan_nhac_cuoi` (hoặc `ngay_tiep_nhan`) cách ≥ 24 giờ → nếu `so_lan_nhac < 3`: tăng, tạo việc cần làm "Gọi lại khách" kèm tin nhắn mẫu; nếu đã 3 lần → T5 (hủy, lý do "Khách không phản hồi sau 3 lần nhắc"). [SRS ghi "đóng"; v1 dùng `DA_HUY` vì `DA_DONG` dành cho đơn hoàn thành hết bảo hành.] | Chuỗi thời gian 24/48/72/96 giờ cho kết quả đúng. |

### 7.2. Công thức tiền

```
tien_cong   = Σ thanh_tien (loai = CONG,     ben_chiu = KHACH)
tien_vat_tu = Σ thanh_tien (loai = VAT_TU,   ben_chiu = KHACH)
phi_khac    = Σ thanh_tien (loai = PHI_KHAC, ben_chiu = KHACH)
giam_vip    = 0 nếu khách không VIP
            = lam_tron_nghin(tien_cong × VIP_TY_LE_GIAM / 100)                    nếu VIP_PHAM_VI_GIAM = TIEN_CONG
            = lam_tron_nghin((tien_cong + tien_vat_tu) × VIP_TY_LE_GIAM / 100)    nếu = CONG_VA_VAT_TU
tong_tien   = tien_cong + tien_vat_tu + phi_khac − giam_vip      (đơn bảo hành: mọi dòng ben_chiu ≠ KHACH → 0)
```
`lam_tron_nghin`: làm tròn đến 1.000 đ gần nhất [ĐX]. Hàm thuần, đặt ở `don_sua_chua/tinh_tien.py`, kiểm thử bằng bảng ví dụ.

---

## 8. Cấu hình hệ thống

### 8.1. Biến môi trường (`.env`)
`DJANGO_SECRET_KEY`, `DJANGO_DEBUG=0`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, `VAPID_PUBLIC_KEY`, `VAPID_PRIVATE_KEY`, `VAPID_EMAIL`, `TELEGRAM_BOT_TOKEN` (tùy chọn), `TELEGRAM_BOT_USERNAME`, `SITE_URL`, `BACKUP_KEEP_DAYS=14`. Có `.env.example` đầy đủ chú thích; lệnh `python manage.py tao_khoa_vapid` in cặp khóa.

### 8.2. Tham số nghiệp vụ trong `CauHinh` (quản trị sửa trên giao diện)

| Khóa | Mặc định | Nguồn |
|---|---|---|
| `THOI_HAN_PHAN_HOI_PHUT` | 15 | BR02 [SRS] |
| `NHAC_XAC_NHAN_SAU_GIO` | 24 | BR08 [SRS] |
| `SO_LAN_NHAC_TOI_DA` | 3 | BR08 [SRS] |
| `BAO_HANH_VE_SINH_NGAY` / `BAO_HANH_SUA_CHUA_NGAY` | 7 / 90 | BR05 [SRS] — giá trị mặc định khi tạo dịch vụ |
| `VIP_SO_DON_TOI_THIEU` | 3 | BR07 [SRS] |
| `VIP_TY_LE_GIAM` | 10 | BR07 [SRS] |
| `VIP_PHAM_VI_GIAM` | `TIEN_CONG` | [OI-02] |
| `NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN` | 2000000 (0 = tắt) | [ĐX][OI-08] |
| `PHI_KIEM_TRA_KHI_TU_CHOI` | 0 | [ĐX] A-04 |
| `CANH_BAO_CHO_CU_THO_PHUT` | 30 | [ĐX] — dựa trên điểm đau "30 phút điều phối không ra kết quả" |
| `DEM_DI_CHUYEN_PHUT` | 30 | [ĐX] BR04 |
| `KHUNG_GIO` | `["08:00-10:00","10:00-12:00","13:00-15:00","15:00-17:00","17:00-19:00"]` | [ĐX] |
| `SO_ANH_TOI_THIEU_KHI_HOAN_THANH` | 1 | [ĐX] UC09 |
| `MAU_TIN_NHAN_XAC_NHAN_LICH` | (mẫu có biến `{ten_khach}`, `{ma_don}`, `{khung_gio}`) | [ĐX] |

---

## 9. Đặc tả chức năng theo ca sử dụng

Ký hiệu: **Màn hình** (URL — template), **Luồng chính**, **Ngoại lệ**, **Nghiệm thu** (kịch bản kiểm thử phải có).

### UC01 — Đăng nhập và phân quyền
- **Màn hình:** `/dang-nhap/` — `tai_khoan/dang_nhap.html` (một ô "Số điện thoại hoặc tên đăng nhập" + mật khẩu/PIN).
- Nhân viên văn phòng: mật khẩu (băm Argon2/PBKDF2 mặc định của Django).
- **Thợ:** số điện thoại + **mã PIN 6 số** do quản trị cấp lần đầu, bắt buộc đổi ở lần đăng nhập đầu. Ghi nhớ đăng nhập 30 ngày trên điện thoại. **Lệch SRS:** NFR05 yêu cầu OTP; SMS OTP có phí nên v1 dùng PIN, để sẵn giao diện `XacThucOTP` cho v2. Ghi vào `docs/GIA_DINH.md`.
- Khóa 15 phút sau 5 lần sai liên tiếp (`django-axes`).
- Sau đăng nhập chuyển hướng theo vai trò: TONG_DAI/QUAN_TRI → `/tong-dai/`; THO → `/tho/`; KE_TOAN → `/ke-toan/doi-soat/`; GIAM_DOC → `/bao-cao/`.
- **Nghiệm thu:** đăng nhập đúng/sai; thợ không vào được `/tong-dai/` (403); thợ đổi PIN lần đầu; khóa sau 5 lần sai.

### UC02 — Tiếp nhận và tạo đơn dịch vụ
- **Màn hình:** `/don/moi/` — `tiep_nhan/gd_tiep_nhan.html`.
- **Luồng chính:**
  1. Tổng đài gõ số điện thoại → HTMX tra cứu (`/khach-hang/tra-cuu/?sdt=`) hiển thị: tên, nhãn VIP, các địa chỉ, thiết bị theo địa chỉ, **5 đơn gần nhất** (kèm phiếu bảo hành còn hạn — gợi ý chuyển sang UC11).
  2. Chọn địa chỉ có sẵn hoặc thêm mới (bắt buộc khu vực).
  3. Chọn/thêm thiết bị (tùy chọn), chọn **dịch vụ yêu cầu** (ô tìm kiếm theo tên, lọc theo loại thiết bị), nhập mô tả sự cố, kênh tiếp nhận.
  4. Nếu khách chốt giờ ngay → chọn ngày + khung giờ (UC03 nhúng, T2); nếu chưa → nhập `khung_gio_mong_muon` (T1).
  5. Lưu → sinh mã đơn, chuyển tới trang chi tiết đơn, hiện **tin nhắn mẫu xác nhận** có nút "Sao chép".
- **Cho phép lưu khi thiếu:** tên khách, thiết bị, lịch. Bắt buộc tối thiểu: số điện thoại, địa chỉ + khu vực, dịch vụ yêu cầu. Đơn thiếu thông tin có nhãn cam "Thiếu thông tin" trên bảng đơn.
- **Ngoại lệ:** số điện thoại không hợp lệ → báo ngay dưới ô; khách đã có đơn đang xử lý cùng địa chỉ và cùng loại thiết bị → cảnh báo "Có thể trùng đơn HF…", vẫn cho lưu.
- **Nghiệm thu:** tạo đơn khách mới thiếu tên; tạo đơn khách cũ chọn địa chỉ cũ; đơn khách VIP có `uu_tien`; mã đơn tăng đúng trong ngày và về 001 sang ngày mới; cảnh báo trùng.

### UC03 — Lập lịch hẹn và xác nhận với khách
- **Màn hình:** khối "Lịch hẹn" trong chi tiết đơn `/don/<ma_don>/` (HTMX), lịch sử các lịch đã thay thế.
- Chốt lịch (T3), đổi hẹn (lịch cũ → DA_THAY_THE, nếu đơn đang DA_CO_THO thì thông báo cho thợ và yêu cầu thợ xác nhận lại — [ĐX]: nếu trùng lịch thợ thì tự rút việc theo T8 sau khi tổng đài đồng ý).
- Nút "Khách chưa trả lời" → tăng `so_lan_nhac`, cập nhật `lan_nhac_cuoi` (đếm chung với BR08).
- **Nghiệm thu:** không thể có hai lịch hiệu lực; đổi hẹn sinh lịch mới; đơn CHO_XAC_NHAN_LICH chốt lịch → CHO_CU_THO.

### UC04 — Điều phối, cử thợ cho đơn (include UC05) [SRS — đặc tả đầy đủ trong SRS mục 5.5.1]
- **Màn hình:** `/don/<ma_don>/cu-tho/` — `dieu_phoi/gd_phan_cong.html` (bảng gợi ý bên trái, thông tin đơn bên phải).
- **Tiền điều kiện:** đơn `CHO_CU_THO`, có dịch vụ, khu vực, lịch hiệu lực.
- **Luồng chính:**
  1. Tổng đài mở đơn chờ (từ bảng đơn).
  2. Hệ thống hiển thị danh sách thợ gợi ý (UC05) **≤ 3 giây** (NFR01).
  3. Tổng đài chọn một hoặc nhiều thợ → "Gửi đề nghị nhận việc".
  4. Hệ thống tạo các `PhanCong(CHO_PHAN_HOI)`, gửi thông báo qua kênh của từng thợ, hiện đồng hồ đếm ngược 15 phút trên đơn.
  5. Thợ đầu tiên nhận (UC07) → T7; thông báo cho tổng đài; các đề nghị khác → DA_HUY và báo cho thợ tương ứng "Đơn đã có thợ nhận".
- **Luồng thay thế:**
  - 2a. Không có thợ phù hợp → tổng đài chọn: "Đề nghị khách đổi lịch" (T6) hoặc "Đánh dấu chưa cử được" (đặt cờ, nhập lý do bắt buộc).
  - 4a. Hết 15 phút không ai nhận → BR02.
  - 3a. [ĐX] "Thợ đã đồng ý qua điện thoại" → tạo thẳng PhanCong DA_NHAN, bắt buộc ghi chú, ghi nhật ký.
  - Tổng đài "Thu hồi đề nghị" một thợ đang chờ → DA_HUY.
- **Hậu điều kiện thành công:** đơn `DA_CO_THO`, lịch bận của thợ cập nhật, nhật ký cử thợ ghi ai thao tác, lúc nào, gửi cho những thợ nào (NFR06).
- **Lớp và phương thức (giữ tên theo slide Tuần 12):** `DonSuaChuaDAO.lay_don_cho_phan_cong() -> list[DonSuaChua]`; `ThoDAO.goi_y_tho(don) -> list[GoiYTho]`; `PhanCongDAO.giao_viec(pc) -> bool` (ghi PhanCong + đổi trạng thái đơn trong **một giao dịch**; chỉ khi trả `True` mới gọi `KenhThongBao.gui_de_nghi_nhan_viec(tho, don)`).
- **Nghiệm thu:** BR01–BR04; gửi cho 3 thợ, thợ thứ 2 nhận trước → thợ 1, 3 nhận thông báo hủy; luồng 2a; luồng hết hạn; thời gian phản hồi gợi ý với dữ liệu mẫu 200 đơn mở/50 thợ < 3 giây (kiểm thử hiệu năng đơn giản bằng `django_assert_max_num_queries` + đo thời gian).

### UC05 — Tra cứu năng lực và lịch bận của thợ
- **Màn hình:** bảng trong `gd_phan_cong.html`; trang riêng `/tho-lich/?ngay=` (lịch theo ngày của toàn bộ thợ dạng lưới khung giờ × thợ) cho tổng đài nhìn tổng thể.
- **Thuật toán xếp hạng** (minh bạch, hiển thị lý do trên từng dòng):
  1. Lọc theo BR04 (mục 7.1).
  2. Sắp xếp: (a) phụ trách đúng khu vực của địa chỉ trước; (b) số đơn đã nhận trong ngày tăng dần (chia đều việc); (c) thời điểm được giao gần nhất cũ hơn trước; (d) chính thức trước cộng tác viên [ĐX].
  3. Mỗi dòng hiển thị: tên, hình thức, khu vực phụ trách (đánh dấu khớp), số việc hôm nay, khung giờ đã bận, "dự kiến rảnh lúc", tỷ lệ nhận việc 30 ngày (số DA_NHAN / số đề nghị) [ĐX], đã từ chối/quá hạn đơn này chưa.
- Thợ bị loại vẫn xem được trong mục thu gọn "Không phù hợp" kèm lý do (sai nghề / trùng lịch HF… / đang nghỉ / tắt nhận việc) — để tổng đài hiểu vì sao.
- **Nghiệm thu:** thứ tự xếp hạng đúng với bộ dữ liệu cố định; lý do loại hiển thị đúng.

### UC06 — Theo dõi bảng đơn trong ngày
- **Màn hình:** `/tong-dai/` — `tiep_nhan/bang_don.html`. Tự làm mới bằng HTMX mỗi 30 giây (chỉ phần bảng).
- Bố cục: thanh lọc (ngày, khu vực, trạng thái, thợ, ô tìm mã đơn/SĐT) + **các cột theo trạng thái Đang xử lý** (Chờ xác nhận lịch | Chờ cử thợ | Đã có thợ | Đang thực hiện) + khối "Hoàn thành/Hủy hôm nay" thu gọn.
- Thẻ đơn: mã, khu vực, dịch vụ, khung giờ, thợ, thời gian đã chờ; nhãn: **VIP** (vàng), **Khách giục ×n** (đỏ), **Chờ cử thợ > 30 phút** (đỏ nhấp nháy nhẹ), **Chưa cử được thợ**, **Thiếu thông tin** (cam), **Chờ tổng đài xác nhận giá**.
- Khối **"Việc cần làm"** bên phải: gọi lại khách (BR08), đơn hết hạn phản hồi cần cử lại (BR02), báo giá chờ xác nhận (OI-08), đơn hẹn trong 2 giờ tới chưa có thợ.
- Nút "Khách giục" trên thẻ → tăng `so_lan_giuc`, ghi nhật ký.
- Giám đốc xem cùng màn hình ở chế độ chỉ đọc.
- **Nghiệm thu:** đơn VIP nằm đầu cột; đơn quá 30 phút có nhãn; bộ lọc hoạt động; giám đốc không thấy nút thao tác.

### UC07 — Nhận / từ chối đơn được giao (thợ, PWA)
- **Màn hình:** `/tho/` — `thuc_hien/tho_trang_chu.html` gồm 3 khối: **Đề nghị đang chờ** (đếm ngược), **Việc hôm nay**, **Việc sắp tới**. Công tắc "Sẵn sàng nhận việc" ở đầu trang.
- Chi tiết đề nghị `/tho/de-nghi/<id>/`: dịch vụ, quận/khu vực, khung giờ, mô tả sự cố, **tiền công dự kiến**; **không** hiện số điện thoại và địa chỉ chi tiết (NFR04).
- **Nhận việc tối đa 3 lần chạm** từ khi mở thông báo (NFR07): chạm thông báo → trang đề nghị → nút **NHẬN VIỆC** lớn → (không có hộp xác nhận thứ hai) → hiện kết quả. Từ chối: nút phụ → chọn 1 lý do có sẵn (1 chạm) → gửi.
- Sau khi nhận: trang việc `/tho/don/<ma_don>/` hiện đủ tên, **số điện thoại (nút gọi `tel:`)**, địa chỉ chi tiết, ghi chú đường đi, nút "Mở bản đồ" (liên kết tìm kiếm Google Maps theo chuỗi địa chỉ, không gửi tọa độ), lịch sử thiết bị tại địa chỉ.
- Nút "Báo bận / trả việc" (chỉ trước khi "Đã đến nơi") → T8, bắt buộc lý do, thông báo tổng đài.
- **Nghiệm thu:** thợ không xem được địa chỉ chi tiết của đơn chưa nhận (kể cả đoán URL — 404); số chạm; nhận muộn sau quá hạn khi đơn còn chờ.

### UC08 — Lập báo giá và ghi nhận xác nhận của khách (extend UC07)
- **Màn hình:** `/tho/don/<ma_don>/bao-gia/` — chỉ với nhóm `SUA_CHUA_THAY_VAT_TU` ở `CHO_DUYET_GIA`.
- Thợ thêm dòng: chọn dịch vụ từ bảng giá (điền sẵn đơn giá tham khảo, cho sửa) hoặc dòng vật tư (tên, số lượng, giá bán, giá mua, có hóa đơn). Tổng tự tính theo 7.2 (đã trừ VIP), hiển thị chữ to.
- "Khách đồng ý": nhập tên người xác nhận (mặc định tên khách), tùy chọn chụp ảnh báo giá → T11, hoặc nếu tổng ≥ ngưỡng → gắn `cho_tong_dai_xac_nhan_gia`, thông báo tổng đài gọi khách; tổng đài bấm "Đã xác nhận với khách" → T12.
- "Khách từ chối": chọn lý do → T13.
- **Nghiệm thu:** tính tổng đúng; luồng ngưỡng; dòng báo giá được đánh dấu `la_bao_gia`.

### UC09 — Ghi nhận hoàn thành và tiền đã thu (include UC10)
- **Màn hình:** `/tho/don/<ma_don>/hoan-thanh/` — một trang cuộn, ít ô nhập (NFR07: rút kinh nghiệm app 2025):
  1. Danh sách hạng mục (sửa được số lượng/giá; thêm vật tư qua UC10).
  2. Ảnh hiện trường: chụp/tải lên 1–5 ảnh (nén phía máy chủ).
  3. **Số tiền đã thu** (điền sẵn = tổng phải thu) + hình thức (3 nút lớn: Tiền mặt / CK công ty / CK cho thợ). Nếu số thu ≠ tổng phải thu → bắt buộc ghi lý do.
  4. Nút **HOÀN THÀNH** → T15: tạo `ThanhToan`, `PhieuBaoHanh`, thông báo tổng đài; hiển thị tin nhắn mẫu cảm ơn + thông tin bảo hành để thợ gửi khách (sao chép).
- Thay đổi hạng mục sau khi khách đã duyệt báo giá → nhật ký ghi trước/sau (NFR06); nếu tổng mới vượt báo giá > 10% → cảnh báo "cần khách xác nhận lại" [ĐX].
- **Nghiệm thu:** thiếu ảnh không hoàn thành được; phiếu bảo hành đúng hạn theo BR05; ThanhToan CK công ty → KHONG_CAN_NOP; số thu lệch cần lý do.

### UC10 — Ghi nhận vật tư sử dụng cho đơn
- Hộp thoại trong UC08/UC09: tên vật tư (gợi ý từ các tên đã nhập trước — tự hoàn thành), số lượng, giá bán khách, giá mua, có hóa đơn, người ứng tiền (mặc định THO [OI-04]).
- **Nghiệm thu:** vật tư thợ ứng được cộng vào `tong_vat_tu_ung` ở UC12.

### UC11 — Tạo và theo dõi đơn bảo hành / làm lại (include UC04)
- **Màn hình:** `/bao-hanh/moi/?don_goc=<ma_don>`; lối vào từ kết quả tra cứu SĐT ở UC02 và từ chi tiết đơn đã hoàn thành.
- **Luồng:** kiểm tra đơn gốc `HOAN_THANH` và phiếu còn hạn → tạo `DonSuaChua(loai_don=BAO_HANH, don_goc=…)` cùng khách, địa chỉ, thiết bị, dịch vụ; `nguyen_nhan_bao_hanh = CHUA_XAC_DINH`; chốt lịch (UC03) → `CHO_CU_THO`; đơn gốc → T16. Gợi ý ưu tiên cử lại **chính thợ đã làm** nếu nguyên nhân sau này là tay nghề [ĐX] — hiển thị nhãn "Thợ làm đơn gốc" trong danh sách gợi ý.
- Thợ hoặc tổng đài xác định nguyên nhân (TAY_NGHE/VAT_TU) trước khi hoàn thành; mọi dòng của đơn bảo hành có `ben_chiu_chi_phi` ≠ KHACH.
- Đơn gốc hết hạn → chặn, gợi ý "Tạo đơn thường".
- Thời hạn bảo hành của đơn gốc **không** được gia hạn sau khi bảo hành [ĐX].
- **Nghiệm thu:** chặn khi hết hạn; T16/T17; đơn bảo hành thu khách 0 đ; báo cáo tỷ lệ làm lại đếm đúng.

### UC12 — Đối soát tiền thợ đã thu
- **Màn hình:** `/ke-toan/doi-soat/` — bảng tổng hợp theo thợ: tiền mặt + CK cho thợ **chưa nộp**, vật tư thợ ứng chưa thanh toán, số phải nộp, đơn cũ nhất chưa nộp (số ngày). Sắp xếp theo số phải nộp giảm dần.
- **Lập phiếu** cho một thợ và kỳ (mặc định: từ phiếu gần nhất đến hôm nay) → phiếu `NHAP` liệt kê từng ThanhToan và dòng vật tư ứng; kế toán bỏ chọn dòng chưa đối chiếu được → **Chốt** (`DA_CHOT`, khóa các dòng) → khi thợ nộp tiền: **Xác nhận đã nộp** → ThanhToan → `DA_NOP`, phiếu `DA_NOP`.
- Thợ xem phiếu của mình ở `/tho/doi-soat/`.
- **Xuất dữ liệu cho MISA** [OI-07: chưa có mẫu cột]: XLSX và CSV với các cột chung (ngày chứng từ, số chứng từ, diễn giải, đối tượng = mã thợ, số tiền, tài khoản nợ/có để trống). Định nghĩa cột đặt trong một dict cấu hình để sửa nhanh khi có mẫu MISA thật.
- **Nghiệm thu:** một ThanhToan không thể nằm ở hai phiếu; phiếu đã chốt không sửa dòng; số liệu khớp tổng.

### UC13 — Quản lý hồ sơ thợ, khách hàng và danh mục dịch vụ
- **Màn hình** (giao diện riêng, không dùng Django Admin cho người dùng nghiệp vụ; Django Admin chỉ bật cho superuser kỹ thuật ở `/he-thong-noi-bo/`):
  - `/danh-muc/tho/`: thêm/sửa thợ, cấp/đặt lại PIN, kỹ năng (chọn nhiều dịch vụ, nhóm theo loại thiết bị), khu vực phụ trách, khóa/mở.
  - `/danh-muc/khach-hang/`: tìm, sửa, gộp hai hồ sơ trùng số [COULD], đánh dấu VIP thủ công kèm lý do.
  - `/danh-muc/dich-vu/`: bảng giá, nhóm, thời hạn bảo hành; **sửa giá ghi nhật ký** (NFR06); không xóa dịch vụ đã dùng, chỉ ngừng áp dụng.
  - `/danh-muc/khu-vuc/`, `/quan-tri/nguoi-dung/`, `/quan-tri/cau-hinh/`.
- Nhập thợ và bảng giá hàng loạt từ file Excel mẫu (tải mẫu → điền → tải lên, báo lỗi theo dòng) [SHOULD] — vì dữ liệu hiện ở Excel.
- **Nghiệm thu:** CRUD; không xóa được dịch vụ đã dùng; nhập Excel báo lỗi đúng dòng.

### UC14 — Xem báo cáo vận hành và doanh thu
- **Màn hình:** `/bao-cao/` với bộ chọn kỳ (hôm nay, 7 ngày, tháng này, tùy chọn), xuất XLSX mọi bảng.
- Chỉ số (thẻ số + biểu đồ Chart.js tự host):
  - Số đơn tiếp nhận / hoàn thành / hủy (theo lý do).
  - **Tỷ lệ đơn không cử được thợ** (đơn từng gắn cờ chưa cử được hoặc hủy khi đang CHO_CU_THO) — so với mốc 15% của hiện trạng.
  - Thời gian trung vị từ tiếp nhận → có thợ; % đơn có thợ trong 30 phút.
  - Doanh thu (Σ `tong_tien_phai_thu` đơn hoàn thành) theo dịch vụ, thợ, khu vực, ngày.
  - **Tỷ lệ làm lại** = số đơn bảo hành tạo trong kỳ / số đơn hoàn thành trong kỳ; theo thợ.
  - **Công nợ thợ hiện tại** (tổng chưa nộp) — so với mốc 12–15 triệu.
  - Tỷ lệ nhận/từ chối/quá hạn đề nghị theo thợ.
- **Nghiệm thu:** số liệu khớp với bộ dữ liệu kiểm thử cố định.

---

## 10. Yêu cầu phi chức năng → cách đáp ứng

| Mã [SRS] | Yêu cầu | Đáp ứng trong v1 |
|---|---|---|
| NFR01 | Danh sách thợ gợi ý ≤ 3 giây (200 đơn mở, 50 thợ) | Truy vấn gợi ý ≤ 5 câu SQL (prefetch); chỉ mục `(trang_thai)`, `(tho_id, trang_thai)` trên PhanCong, `(don_id, trang_thai)` trên LichHen; kiểm thử hiệu năng. |
| NFR02 | Nhận việc ≤ 5 giây ở 1 Mbps | Trang thợ không dùng thư viện JS nặng; HTMX + Alpine tự host; gzip (WhiteNoise); trang đề nghị < 60 KB. |
| NFR03 | 3 tổng đài + 25 thợ đồng thời | gunicorn 3 worker × 2 thread; đủ dư. |
| NFR04 | Thợ chỉ xem SĐT, địa chỉ khách của đơn đã nhận | Lọc ở DAO + view; ảnh phục vụ qua view có kiểm tra quyền; kiểm thử phân quyền. |
| NFR05 | Mật khẩu băm có muối; thợ đăng nhập SĐT + OTP | Băm mặc định Django; **PIN thay OTP ở v1** (ghi lệch). |
| NFR06 | Nhật ký mọi thao tác cử thợ, sửa giá, ghi tiền; truy vết 12 tháng | `NhatKyThaoTac` chỉ-thêm; ghi qua hàm `ghi_nhat_ky()` gọi trong DAO; trang xem nhật ký có lọc. |
| NFR07 | Thợ nhận một đơn ≤ 3 chạm | Mục UC07. |
| NFR08 | Dùng một tay, đọc ngoài trời: chữ ≥ 16px, vùng bấm ≥ 44px, tương phản AA | Thiết kế mobile-first; nút hành động chính cố định đáy màn hình. |
| NFR09 | Tổng đài mới thành thạo tạo đơn + cử thợ sau ≤ 2 giờ hướng dẫn | Gợi ý nhãn rõ, phím tắt (`/` tìm kiếm, `n` đơn mới) [ĐX]; trang `/huong-dan/` ngắn. |
| NFR10–16 | (xem SRS) | Rà lại khi có bản SRS đầy đủ; Claude Code ghi `TODO-NFR` nếu chưa đáp ứng. |
| — | Sao lưu | `pg_dump` hằng ngày lúc 02:00, giữ 14 ngày; kiểm thử khôi phục trong tài liệu vận hành. |
| — | Dữ liệu cá nhân [OI-05] | Ẩn bớt SĐT trong danh sách cho vai trò không cần (`090****123`); không lưu vị trí thợ; xuất dữ liệu chỉ cho vai trò có quyền. |

---

## 11. Thông báo (adapter `KenhThongBao`)

```python
class KenhThongBao(Protocol):
    def gui(self, nguoi_nhan: NguoiDung, tieu_de: str, noi_dung: str, duong_dan: str) -> bool: ...
```
- `DichVuThongBao.gui(nguoi_nhan, ...)`: **luôn** tạo bản ghi `ThongBao` (chuông trong ứng dụng) rồi gửi qua kênh ưu tiên của người nhận; thất bại kênh chính → thử kênh còn lại; ghi kết quả vào log. Gửi **sau khi giao dịch commit** (`transaction.on_commit`) và chạy nền qua django-q2 để không làm chậm thao tác.
- `WebPushKenh`: `pywebpush`, khóa VAPID; endpoint hết hạn (404/410) → xóa `DangKyPush`.
- `TelegramKenh`: gọi `https://api.telegram.org/bot<token>/sendMessage` bằng `httpx`; gắn tài khoản qua liên kết `https://t.me/<bot>?start=<token_mot_lan>` + webhook hoặc lệnh `python manage.py telegram_poll` chạy trong worker.
- `ConsoleKenh`: in ra log — dùng khi phát triển và kiểm thử.
- `ZaloZnsKenh`, `SmsKenh`: lớp rỗng ném `NotImplementedError` kèm chú thích "v2 — có phí".
- Các sự kiện phát thông báo: gửi đề nghị (thợ), đề nghị bị hủy (thợ), thợ nhận/từ chối/quá hạn (tổng đài đã giao), báo giá chờ xác nhận (tổng đài), thợ trả việc (tổng đài), đổi lịch (thợ), hoàn thành (tổng đài).
- **Lưu ý iPhone:** Web Push trên iOS chỉ hoạt động khi PWA đã được "Thêm vào Màn hình chính" (iOS 16.4+). Trang `/tho/cai-dat/` hướng dẫn từng bước kèm nút "Gửi thử thông báo"; thợ iPhone khuyến nghị dùng Telegram.

---

## 12. Tác vụ nền (django-q2, lịch trong migration dữ liệu)

| Tác vụ | Chu kỳ | Việc |
|---|---|---|
| `kiem_tra_qua_han_phan_cong` | 1 phút | BR02 |
| `nhac_xac_nhan_lich` | 1 giờ | BR08 |
| `dong_don_het_bao_hanh` | hằng ngày 00:15 | BR05 (T18) |
| `cap_nhat_khach_vip` | hằng ngày 01:00 | BR07 |
| `sao_luu_csdl` | hằng ngày 02:00 | `pg_dump -Fc` → `/backups/homefix_YYYYmmdd.dump`, xóa bản > `BACKUP_KEEP_DAYS` (chạy trong container `backup` bằng cron nếu tách riêng) |
| `don_dep_thong_bao` | hằng tuần | xóa ThongBao đã đọc > 90 ngày |

Mọi tác vụ **lũy đẳng** (chạy lại không sinh sai lệch), có kiểm thử với `freezegun`.

---

## 13. Giao diện

- Ngôn ngữ giao diện: **tiếng Việt có dấu**, `LANGUAGE_CODE="vi"`; định dạng số kiểu Việt Nam (`1.250.000 đ`).
- Hai bố cục: **văn phòng** (`base_van_phong.html`: thanh bên trái theo vai trò, rộng ≥ 1280px tối ưu) và **thợ** (`base_tho.html`: mobile-first, thanh điều hướng đáy 4 mục: Việc, Đề nghị, Đối soát, Cài đặt).
- Màu chủ đạo trung tính + một màu nhấn cho hành động chính; trạng thái đơn có màu cố định dùng chung mọi nơi (định nghĩa một lần trong `templatetags/trang_thai.py`).
- PWA: `manifest.webmanifest` (tên "HomeFix Thợ", biểu tượng tự vẽ đơn giản), `service-worker.js` (nhận push, mở URL khi chạm thông báo; cache tĩnh tối thiểu; **không** cache dữ liệu khách hàng).
- Mọi form có kiểm tra phía máy chủ; thông điệp lỗi cụ thể, gắn ngay dưới ô.
- Trang lỗi 403/404/500 tiếng Việt.

### Bản đồ URL tổng hợp

```
/dang-nhap/  /dang-xuat/  /doi-mat-khau/
/tong-dai/                          bảng đơn (UC06)
/don/moi/                           UC02
/don/<ma_don>/                      chi tiết, lịch hẹn (UC03), nhật ký đơn, hành động theo trạng thái
/don/<ma_don>/cu-tho/               UC04, UC05
/don/<ma_don>/huy/  /don/<ma_don>/xac-nhan-gia/
/tho-lich/?ngay=                    lưới lịch thợ (UC05)
/khach-hang/tra-cuu/?sdt=           HTMX
/bao-hanh/moi/?don_goc=             UC11
/tho/  /tho/de-nghi/<id>/  /tho/don/<ma_don>/  /tho/don/<ma_don>/bao-gia/
/tho/don/<ma_don>/hoan-thanh/  /tho/doi-soat/  /tho/cai-dat/
/ke-toan/doi-soat/  /ke-toan/doi-soat/<ma>/  /ke-toan/xuat/
/bao-cao/  /bao-cao/xuat/
/danh-muc/tho/  /danh-muc/khach-hang/  /danh-muc/dich-vu/  /danh-muc/khu-vuc/
/quan-tri/nguoi-dung/  /quan-tri/cau-hinh/  /quan-tri/nhat-ky/
/thong-bao/  /push/dang-ky/  /telegram/webhook/<secret>/
/anh/<id>/                          phục vụ ảnh có kiểm tra quyền
/suc-khoe/                          health check cho Docker
```

---

## 14. Cấu trúc mã nguồn và triển khai

### 14.1. Cây thư mục

```
homefix/
├── SPEC.md  CLAUDE.md  README.md  Makefile  pyproject.toml
├── docker-compose.yml  docker-compose.override.yml (dev)  Dockerfile  .env.example
├── docs/  GIA_DINH.md  VAN_HANH.md  ANH_XA_BANG.md  HUONG_DAN_SU_DUNG.md
├── config/            settings/{base,dev,prod}.py  urls.py  wsgi.py
├── apps/
│   ├── tai_khoan/         NguoiDung, đăng nhập, PIN, phân quyền (UC01)
│   ├── danh_muc/          KhachHang, DiaChi, ThietBi, DichVu, Tho, KhuVuc (UC13) + dao.py
│   ├── don_sua_chua/      [gói lõi] DonSuaChua, HangMucSuaChua, trang_thai.py, tinh_tien.py, dao.py
│   ├── tiep_nhan_dieu_phoi/  LichHen, PhanCong (UC02–UC06) + dao.py, views, templates
│   ├── thuc_hien/         view & template cho thợ (UC07–UC10) — không có lớp thực thể
│   ├── tai_chinh/         ThanhToan, PhieuDoiSoat (UC12)
│   ├── bao_hanh/          PhieuBaoHanh (UC11)
│   ├── bao_cao/           UC14 (chỉ đọc)
│   ├── thong_bao/         ThongBao, DangKyPush, adapters.py
│   └── he_thong/          NhatKyThaoTac, CauHinh, BoDemMaDon, tác vụ nền, lệnh quản trị
├── templates/  static/ (htmx, alpine, chart.js tự host; css build)
└── tests/  (theo app; conftest.py với factory_boy)
```
Phụ thuộc giữa app **một chiều** theo biểu đồ gói Tuần 10: các app nghiệp vụ → `don_sua_chua` (lõi) → `danh_muc`; mọi app → `he_thong`, `thong_bao`. Không import ngược (kiểm tra bằng `import-linter` trong `make check`).

### 14.2. Docker Compose (tóm tắt)

- `db`: `postgres:16-alpine`, volume `pgdata`, healthcheck `pg_isready`.
- `web`: build từ `Dockerfile` (python:3.12-slim), lệnh khởi động: `migrate` → `collectstatic` → `gunicorn config.wsgi -w 3 --threads 2 -b 0.0.0.0:8000`; volume `media`; cổng `127.0.0.1:8000:8000` (chỉ máy chủ, đưa ra ngoài qua tunnel).
- `worker`: cùng image, lệnh `python manage.py qcluster`.
- `backup`: `postgres:16-alpine` + cron chạy `pg_dump` vào `./backups` (thư mục trên máy chủ).
- Mọi dịch vụ `restart: unless-stopped`.

### 14.3. Triển khai tại nhà (ghi vào `docs/VAN_HANH.md`)

**Phần cứng tối thiểu:** máy tính/mini PC 2 nhân, 4 GB RAM, 20 GB trống, bật 24/7 (máy cũ chạy Ubuntu Server 24.04 là đủ; Windows dùng Docker Desktop + WSL2 cũng được).

**Bước cài:**
1. Cài Docker + Docker Compose; `git clone`; `cp .env.example .env`; sinh `DJANGO_SECRET_KEY` và khóa VAPID (`make vapid`).
2. `docker compose up -d --build`
3. `docker compose exec web python manage.py tao_quan_tri` (tạo tài khoản QUAN_TRI đầu tiên, hỏi tên/SĐT/mật khẩu).
4. (Thử nghiệm) `docker compose exec web python manage.py nap_du_lieu_mau` — dữ liệu mục 14.4.
5. **Đưa ra Internet — chọn một:**
   - **A. Tailscale Funnel (không cần tên miền):** cài Tailscale trên máy chủ, đăng nhập, bật HTTPS Certificates và Funnel trong trang quản trị, chạy `sudo tailscale funnel --bg 8000` → nhận URL `https://<ten-may>.<tailnet>.ts.net`. Đặt URL này vào `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, `SITE_URL`.
   - **B. Cloudflare Tunnel (đã có tên miền trên Cloudflare):** thêm dịch vụ `cloudflared` vào compose với token tunnel, trỏ `homefix.<ten-mien>` → `http://web:8000`.
   - **C. Chỉ mạng nội bộ:** truy cập `http://<ip-may-chu>:8000` (đổi cổng bind) — **PWA và Web Push không hoạt động** khi không có HTTPS; chỉ để thử giao diện tổng đài.
6. Thợ mở URL trên điện thoại → đăng nhập → "Thêm vào màn hình chính" → bật thông báo (hoặc liên kết Telegram).

**Cập nhật phiên bản:** `git pull && docker compose up -d --build` (migration chạy tự động). **Khôi phục:** `docker compose exec -T db pg_restore -U homefix -d homefix --clean < backups/<file>.dump`. Khuyến nghị chép thư mục `backups/` sang ổ khác hoặc Google Drive (`rclone`, tùy chọn).

### 14.4. Dữ liệu mẫu (`nap_du_lieu_mau`, toàn bộ hư cấu)
- 12 khu vực: Ba Đình, Hoàn Kiếm, Đống Đa, Hai Bà Trưng, Cầu Giấy, Thanh Xuân, Tây Hồ, Hoàng Mai, Long Biên, Nam Từ Liêm, Bắc Từ Liêm, Hà Đông.
- ~20 dịch vụ ở cả hai nhóm (giá minh họa [ĐX], ví dụ vệ sinh điều hòa treo tường 150.000 đ/máy; vệ sinh máy giặt cửa trên 250.000 đ; nạp gas điều hòa từ 350.000 đ; thay thanh đốt bình nóng lạnh từ 300.000 đ; sửa rò rỉ đường nước từ 200.000 đ…).
- Người dùng: 1 quản trị, 3 tổng đài, 1 kế toán, 1 giám đốc, 12 thợ (kỹ năng, khu vực đa dạng; 2 thợ đang nghỉ); mật khẩu/PIN mặc định in ra màn hình **một lần**, không ghi vào mã nguồn.
- 40 khách (3 VIP), ~60 đơn trải đều **mọi trạng thái** trong 30 ngày qua và hôm nay, có đơn bảo hành, có phiếu đối soát — để thử mọi màn hình và báo cáo.
- Lệnh `xoa_du_lieu_mau` xóa sạch trước khi chạy thật.

---

## 15. Kế hoạch sinh mã theo giai đoạn

Mỗi giai đoạn: viết mã → viết/chạy kiểm thử → `make check` (ruff + import-linter + pytest) xanh → cập nhật `docs/` → commit `P<n>: <mô tả>` → báo cáo và **dừng**.

**P0 — Khung dự án.** Cấu trúc 14.1; settings tách dev/prod; Docker Compose chạy được; `NguoiDung` tùy biến (phải có **trước migration đầu tiên**); `MoHinhCoBan`; `CauHinh`, `NhatKyThaoTac`, `ghi_nhat_ky()`; hai layout; trang đăng nhập; `/suc-khoe/`; Makefile (`up, down, test, check, vapid, seed, backup`).
*Nghiệm thu:* `docker compose up` → mở `/dang-nhap/`; `make check` xanh; tạo quản trị bằng lệnh.

**P1 — Danh mục và tài khoản (UC01, UC13).** Mô hình `KhuVuc, KhachHang, DiaChi, ThietBi, DichVu, Tho`; quản lý người dùng, PIN thợ, phân quyền theo ma trận 3.1 (decorator `@yeu_cau_vai_tro(...)` + mixin); trang danh mục; nhập Excel thợ/bảng giá; `nap_du_lieu_mau` (phần danh mục).
*Nghiệm thu:* kiểm thử phân quyền mọi URL theo ma trận (tham số hóa); CRUD; nhật ký sửa giá.

**P2 — Tiếp nhận (UC02, UC03, UC06 cơ bản).** `DonSuaChua`, `HangMucSuaChua`, `LichHen`, bảng chuyển trạng thái đầy đủ (kể cả chuyển chưa dùng tới, có kiểm thử), sinh mã đơn, tra cứu SĐT, bảng đơn, tin nhắn mẫu, BR08 + tác vụ nền đầu tiên (cài django-q2).
*Nghiệm thu:* kịch bản UC02/UC03; kiểm thử tham số hóa mọi dòng T1–T18 ở mức mô hình; BR08.

**P3 — Điều phối và thợ nhận việc (UC04, UC05, UC07, UC06 cảnh báo).** `PhanCong`, `ThoDAO.goi_y_tho`, `PhanCongDAO.giao_viec/nhan_viec/tu_choi`, BR01–BR04, thông báo (Console + WebPush + Telegram), PWA (manifest, service worker), trang thợ, tác vụ quá hạn.
*Nghiệm thu:* kiểm thử song song BR03; NFR01; NFR04; luồng 2a, 3a, 4a; thử push thật trên một điện thoại Android qua HTTPS.

**P4 — Thực hiện tại hiện trường (UC08, UC09, UC10).** Báo giá, ngưỡng OI-08, ảnh hiện trường + view phục vụ có quyền, hoàn thành, `tinh_tien.py`, `ThanhToan`, `PhieuBaoHanh`.
*Nghiệm thu:* bảng ví dụ tính tiền (thường, VIP hai phạm vi, bảo hành); thiếu ảnh bị chặn; BR05, BR06.

**P5 — Bảo hành và tài chính (UC11, UC12).** Đơn bảo hành T16/T17, BR05 tác vụ đóng đơn, đối soát, xuất CSV/XLSX.
*Nghiệm thu:* các kịch bản UC11, UC12; không trùng ThanhToan giữa phiếu.

**P6 — Báo cáo và hoàn thiện (UC14, NFR, vận hành).** Báo cáo + xuất; trang nhật ký; sao lưu; lệnh `sinh_anh_xa_bang` (đọc `_meta` mọi model → `docs/ANH_XA_BANG.md`: lớp ↔ bảng ↔ cột ↔ kiểu); `docs/VAN_HANH.md`, `docs/HUONG_DAN_SU_DUNG.md` (theo vai trò); rà soát bảo mật prod (`check --deploy` sạch).
*Nghiệm thu:* chạy thử toàn trình một ngày làm việc với dữ liệu mẫu (kịch bản E2E bằng Django test client): tạo đơn → cử thợ → nhận → báo giá → hoàn thành → bảo hành → đối soát → báo cáo.

---

## 16. Vấn đề còn mở và lựa chọn mặc định của v1

| Mã | Vấn đề [SRS] | Mặc định v1 | Đổi ở đâu |
|---|---|---|---|
| OI-01 | Một lần gọi sửa nhiều thiết bị: một hay nhiều đơn? | Một đơn = một địa chỉ + một dịch vụ yêu cầu, nhiều thiết bị cùng loại; khác nghề → tạo đơn riêng (nút "Tạo thêm đơn cho cuộc gọi này" điền sẵn khách/địa chỉ) [ĐX] | Quy trình UC02 |
| OI-02 | Giảm 10% VIP áp cho tiền công hay cả vật tư? | Tiền công | `VIP_PHAM_VI_GIAM` |
| OI-03 | Ai quản trị hệ thống sau bàn giao? | Vai trò `QUAN_TRI` gán cho tổ trưởng tổng đài | Gán vai trò |
| OI-04 | Thợ tự mua vật tư hay mua tập trung? | Thợ tự mua và ứng tiền (`nguoi_ung = THO`) | Mặc định trường |
| OI-05 | Rà soát pháp lý dữ liệu cá nhân | Thu tối thiểu, ẩn SĐT, nhật ký truy cập; cần rà lại trước khi chạy thật | `docs/GIA_DINH.md` |
| OI-06 | (xem SRS) | — | — |
| OI-07 | Định dạng dữ liệu xuất sang MISA | CSV/XLSX cột chung, cấu hình được | `tai_chinh/xuat_misa.py` |
| OI-08 | Ngưỡng báo giá phải gọi tổng đài xác nhận | 2.000.000 đ [ĐX], 0 = tắt | `NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN` |

Các giả định [ĐX] khác (A-02 "Đã đến nơi", A-03 thợ báo bận, A-04 phí kiểm tra, cờ "Chưa cử được thợ", PIN thay OTP, BR08 hủy thay vì đóng…) phải được Claude Code liệt kê đầy đủ trong `docs/GIA_DINH.md` với cột "Đã chốt? (C/K)".

---

## Phụ lục A — Nội dung `CLAUDE.md`

```markdown
# HomeFix Ops v1 — quy ước cho Claude Code

- Nguồn sự thật là SPEC.md. Không thêm tính năng ngoài SPEC. Gặp điểm mơ hồ: chọn phương án đơn giản nhất,
  ghi vào docs/GIA_DINH.md (mã A-xx, lý do, cách đổi) rồi làm tiếp; chỉ dừng hỏi khi ảnh hưởng mô hình dữ liệu.
- Làm đúng MỘT giai đoạn mỗi lượt (SPEC mục 15). Kết thúc: make check xanh, commit "P<n>: ...", báo cáo theo tiêu chí nghiệm thu.
- Tên lớp, tên bảng (tblXxx), tên phương thức DAO giữ đúng SPEC mục 2.2 và 5 — đây là mã dùng để đối chiếu với bài giảng.
- Định danh: tiếng Việt không dấu; lớp PascalCase, còn lại snake_case. Chuỗi hiển thị: tiếng Việt có dấu.
- Tiền là số nguyên (đồng), không dùng float. Thời gian luôn có múi giờ Asia/Ho_Chi_Minh.
- Trạng thái đơn chỉ đổi qua phương thức nghiệp vụ dùng bảng CHUYEN_TRANG_THAI. View không gán trang_thai.
- Thao tác ghi đi qua dao.py, bọc transaction.atomic(), ghi nhật ký (ghi_nhat_ky) cho: cử thợ, sửa giá, ghi tiền, đổi trạng thái.
- Gửi thông báo bằng transaction.on_commit + tác vụ nền; không gọi mạng trong giao dịch.
- Mỗi quy tắc BRxx có ít nhất một kiểm thử mang tên test_brxx_...
- Không đưa bí mật vào mã; dùng .env. Không commit .env, media/, backups/.
- Thư viện JS/CSS tự host trong static/, không dùng CDN (máy chủ tại nhà, mạng thợ yếu).
- Lệnh: make up | make test | make check | make seed | make backup
```

## Phụ lục B — Danh mục gói Python dự kiến

`django>=5.2,<5.3`, `psycopg[binary]`, `dj-database-url`, `django-environ`, `django-q2`, `django-htmx`, `django-tailwind-cli`, `django-axes`, `whitenoise`, `gunicorn`, `pywebpush`, `httpx`, `Pillow`, `openpyxl`, `phonenumberslite` (tùy chọn, có thể tự viết hàm chuẩn hóa SĐT VN). Dev: `pytest`, `pytest-django`, `factory-boy`, `freezegun`, `ruff`, `import-linter`. Ghim phiên bản cụ thể trong `pyproject.toml` khi P0, chọn bản phát hành đã ổn định.

## Phụ lục C — Truy vết nhanh UC ↔ lớp ↔ BR

| UC | Lớp thực thể chính | DAO / dịch vụ | BR | NFR |
|---|---|---|---|---|
| UC02 | KhachHang, DiaChi, ThietBi, DonSuaChua | KhachHangDAO.tra_cuu_theo_sdt, DonSuaChuaDAO.tao_don | BR07 | NFR09 |
| UC03 | LichHen, DonSuaChua | LichHenDAO.chot_lich, doi_hen | BR08 | — |
| UC04/05 | PhanCong, Tho, DonSuaChua, LichHen | DonSuaChuaDAO.lay_don_cho_phan_cong, ThoDAO.goi_y_tho, PhanCongDAO.giao_viec | BR01–BR04 | NFR01, NFR04, NFR06 |
| UC06 | DonSuaChua | DonSuaChuaDAO.bang_don_trong_ngay | BR02, BR07, BR08 | — |
| UC07 | PhanCong | PhanCongDAO.nhan_viec, tu_choi | BR02, BR03 | NFR02, NFR04, NFR07, NFR08 |
| UC08 | HangMucSuaChua, DonSuaChua | DonSuaChuaDAO.ghi_bao_gia, khach_duyet_gia | BR06, BR07 | NFR06 |
| UC09/10 | HangMucSuaChua, ThanhToan, PhieuBaoHanh | DonSuaChuaDAO.hoan_thanh | BR05, BR07 | NFR06, NFR08 |
| UC11 | DonSuaChua (bảo hành), PhieuBaoHanh | BaoHanhDAO.tao_don_bao_hanh | BR05 | — |
| UC12 | ThanhToan, PhieuDoiSoat | DoiSoatDAO.lap_phieu, chot, xac_nhan_da_nop | — | NFR06 |
| UC13 | Tho, KhachHang, DichVu, KhuVuc | các DAO danh mục | BR05, BR07 | NFR04, NFR05 |
| UC14 | (chỉ đọc) | BaoCaoDAO | — | — |
