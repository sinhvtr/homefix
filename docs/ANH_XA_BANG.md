# Ánh xạ lớp ↔ bảng ↔ cột ↔ kiểu

Sinh tự động bằng `python manage.py sinh_anh_xa_bang` từ `_meta` của các model — **không sửa tay**.
Kiểu CSDL theo PostgreSQL 16. Mọi bảng kế thừa `MoHinhCoBan` có thêm `tao_luc`, `cap_nhat_luc`.

## Mục lục

- `BoDemMaDon` → `tblBoDemMaDon` (he_thong)
- `CauHinh` → `tblCauHinh` (he_thong)
- `NhatKyThaoTac` → `tblNhatKy` (he_thong)
- `DangKyPush` → `tblDangKyPush` (thong_bao)
- `ThongBao` → `tblThongBao` (thong_bao)
- `NguoiDung` → `tblNhanVien` (tai_khoan)
- `DiaChi` → `tblDiaChi` (danh_muc)
- `DichVu` → `tblDichVu` (danh_muc)
- `KhachHang` → `tblKhachHang` (danh_muc)
- `KhuVuc` → `tblKhuVuc` (danh_muc)
- `ThietBi` → `tblThietBi` (danh_muc)
- `Tho` → `tblTho` (danh_muc)
- `AnhHienTruong` → `tblAnhHienTruong` (don_sua_chua)
- `DonSuaChua` → `tblDonSuaChua` (don_sua_chua)
- `HangMucSuaChua` → `tblHangMucSuaChua` (don_sua_chua)
- `LichHen` → `tblLichHen` (tiep_nhan_dieu_phoi)
- `PhanCong` → `tblPhanCong` (tiep_nhan_dieu_phoi)
- `PhieuDoiSoat` → `tblPhieuDoiSoat` (tai_chinh)
- `ThanhToan` → `tblThanhToan` (tai_chinh)
- `PhieuBaoHanh` → `tblPhieuBaoHanh` (bao_hanh)

## BoDemMaDon → `tblBoDemMaDon`

App `he_thong` · bộ đếm mã đơn

> Bộ đếm số thứ tự đơn trong ngày để sinh mã HFyyMMdd-nnn (SPEC 5.2).

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ngay` | `ngay` | DateField | date |  | UNIQUE | ngày |
| `so_cuoi` | `so_cuoi` | PositiveIntegerField | integer |  | mặc định 0 | số cuối |

## CauHinh → `tblCauHinh`

App `he_thong` · cấu hình

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `khoa` | `khoa` | CharField | varchar(60) |  | UNIQUE | khóa |
| `gia_tri` | `gia_tri` | CharField | varchar(1000) |  |  | giá trị |
| `kieu` | `kieu` | CharField | varchar(4) |  | chọn: INT, BOOL, STR, JSON; mặc định 'STR' | kiểu |
| `mo_ta` | `mo_ta` | CharField | varchar(255) |  |  | mô tả |

## NhatKyThaoTac → `tblNhatKy`

App `he_thong` · nhật ký thao tác

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `nguoi_dung` | `nguoi_dung_id` | ForeignKey | bigint | có | FK → tblNhanVien (NguoiDung), PROTECT | người dùng |
| `thoi_diem` | `thoi_diem` | DateTimeField | timestamp with time zone |  |  | thời điểm |
| `hanh_dong` | `hanh_dong` | CharField | varchar(50) |  |  | hành động |
| `doi_tuong` | `doi_tuong` | CharField | varchar(100) |  |  | đối tượng |
| `du_lieu_truoc` | `du_lieu_truoc` | JSONField | jsonb | có |  | dữ liệu trước |
| `du_lieu_sau` | `du_lieu_sau` | JSONField | jsonb | có |  | dữ liệu sau |
| `dia_chi_ip` | `dia_chi_ip` | GenericIPAddressField | inet | có |  | địa chỉ IP |

## DangKyPush → `tblDangKyPush`

App `thong_bao` · đăng ký Web Push

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `nguoi_dung` | `nguoi_dung_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), CASCADE | người dùng |
| `endpoint` | `endpoint` | CharField | varchar(500) |  | UNIQUE | endpoint |
| `p256dh` | `p256dh` | CharField | varchar(200) |  |  | p256dh |
| `auth` | `auth` | CharField | varchar(100) |  |  | auth |
| `user_agent` | `user_agent` | CharField | varchar(300) |  |  | trình duyệt |

## ThongBao → `tblThongBao`

App `thong_bao` · thông báo

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `nguoi_nhan` | `nguoi_nhan_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), CASCADE | người nhận |
| `tieu_de` | `tieu_de` | CharField | varchar(200) |  |  | tiêu đề |
| `noi_dung` | `noi_dung` | TextField | text |  |  | nội dung |
| `duong_dan` | `duong_dan` | CharField | varchar(255) |  |  | đường dẫn |
| `da_doc` | `da_doc` | BooleanField | boolean |  | mặc định False | đã đọc |

Chỉ mục:

- `thong_bao_nguoi_nhan_idx`: (nguoi_nhan, da_doc)

## NguoiDung → `tblNhanVien`

App `tai_khoan` · người dùng

> Người dùng hệ thống [SRS: NhanVien]. Mỗi người đúng một vai trò; khóa tài khoản bằng is_active.

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `password` | `password` | CharField | varchar(128) |  |  | Mật khẩu |
| `last_login` | `last_login` | DateTimeField | timestamp with time zone | có |  | Lần cuối đăng nhập |
| `is_superuser` | `is_superuser` | BooleanField | boolean |  | mặc định False | trạng thái superuser |
| `username` | `username` | CharField | varchar(150) |  | UNIQUE | Tên đăng nhập |
| `first_name` | `first_name` | CharField | varchar(150) |  |  | Tên |
| `last_name` | `last_name` | CharField | varchar(150) |  |  | Họ |
| `email` | `email` | CharField | varchar(254) |  |  | địa chỉ email |
| `is_staff` | `is_staff` | BooleanField | boolean |  | mặc định False | tình trạng nhân viên |
| `is_active` | `is_active` | BooleanField | boolean |  | mặc định True | Kích hoạt |
| `date_joined` | `date_joined` | DateTimeField | timestamp with time zone |  |  | Ngày tham gia |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ho_ten` | `ho_ten` | CharField | varchar(100) |  |  | họ tên |
| `so_dien_thoai` | `so_dien_thoai` | CharField | varchar(10) |  | UNIQUE | số điện thoại |
| `vai_tro` | `vai_tro` | CharField | varchar(10) |  | chọn: QUAN_TRI, TONG_DAI, THO, KE_TOAN, GIAM_DOC | vai trò |
| `phai_doi_mat_khau` | `phai_doi_mat_khau` | BooleanField | boolean |  | mặc định False | phải đổi mật khẩu |

Quan hệ nhiều–nhiều (bảng trung gian):

- `groups` → `auth_group` (Group) qua bảng `tblNhanVien_groups`
- `user_permissions` → `auth_permission` (Permission) qua bảng `tblNhanVien_user_permissions`

Ràng buộc CSDL:

- `nguoi_dung_vai_tro_hop_le`: CHECK (AND: ('vai_tro__in', ['QUAN_TRI', 'TONG_DAI', 'THO', 'KE_TOAN', 'GIAM_DOC']))

## DiaChi → `tblDiaChi`

App `danh_muc` · địa chỉ

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `khach_hang` | `khach_hang_id` | ForeignKey | bigint |  | FK → tblKhachHang (KhachHang), CASCADE | khách hàng |
| `dia_chi_chi_tiet` | `dia_chi_chi_tiet` | CharField | varchar(255) |  |  | địa chỉ chi tiết |
| `khu_vuc` | `khu_vuc_id` | ForeignKey | bigint |  | FK → tblKhuVuc (KhuVuc), PROTECT | khu vực |
| `ghi_chu_duong_di` | `ghi_chu_duong_di` | TextField | text |  |  | ghi chú đường đi |
| `la_mac_dinh` | `la_mac_dinh` | BooleanField | boolean |  | mặc định False | mặc định |

Ràng buộc CSDL:

- `mot_dia_chi_mac_dinh`: UNIQUE (khach_hang) WHERE (AND: ('la_mac_dinh', True))

## DichVu → `tblDichVu`

App `danh_muc` · dịch vụ

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ma` | `ma` | CharField | varchar(20) |  | UNIQUE | mã |
| `ten_dich_vu` | `ten_dich_vu` | CharField | varchar(150) |  |  | tên dịch vụ |
| `nhom_dich_vu` | `nhom_dich_vu` | CharField | varchar(25) |  | chọn: VE_SINH_BAO_DUONG, SUA_CHUA_THAY_VAT_TU | nhóm dịch vụ |
| `loai_thiet_bi` | `loai_thiet_bi` | CharField | varchar(20) |  | chọn: DIEU_HOA, MAY_GIAT, TU_LANH, BINH_NONG_LANH, DIEN_NUOC, KHAC | loại thiết bị |
| `don_gia_tham_khao` | `don_gia_tham_khao` | BigIntegerField | bigint |  |  | đơn giá tham khảo (đ) |
| `don_vi_tinh` | `don_vi_tinh` | CharField | varchar(20) |  |  | đơn vị tính |
| `thoi_han_bao_hanh_ngay` | `thoi_han_bao_hanh_ngay` | PositiveIntegerField | integer |  |  | thời hạn bảo hành (ngày) |
| `dang_ap_dung` | `dang_ap_dung` | BooleanField | boolean |  | mặc định True | đang áp dụng |

Ràng buộc CSDL:

- `dich_vu_don_gia_khong_am`: CHECK (AND: ('don_gia_tham_khao__gte', 0))

## KhachHang → `tblKhachHang`

App `danh_muc` · khách hàng

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ho_ten` | `ho_ten` | CharField | varchar(100) |  |  | họ tên |
| `so_dien_thoai` | `so_dien_thoai` | CharField | varchar(10) |  | UNIQUE | số điện thoại |
| `so_dien_thoai_phu` | `so_dien_thoai_phu` | CharField | varchar(10) |  |  | số điện thoại phụ |
| `loai_khach` | `loai_khach` | CharField | varchar(6) |  | chọn: THUONG, VIP; mặc định 'THUONG' | loại khách |
| `vip_thu_cong` | `vip_thu_cong` | BooleanField | boolean |  | mặc định False | VIP thủ công |
| `ly_do_vip` | `ly_do_vip` | CharField | varchar(200) |  |  | lý do VIP |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |

## KhuVuc → `tblKhuVuc`

App `danh_muc` · khu vực

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ma` | `ma` | CharField | varchar(20) |  | UNIQUE | mã |
| `ten` | `ten` | CharField | varchar(100) |  |  | tên |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |

## ThietBi → `tblThietBi`

App `danh_muc` · thiết bị

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `dia_chi` | `dia_chi_id` | ForeignKey | bigint |  | FK → tblDiaChi (DiaChi), CASCADE | địa chỉ |
| `loai_thiet_bi` | `loai_thiet_bi` | CharField | varchar(20) |  | chọn: DIEU_HOA, MAY_GIAT, TU_LANH, BINH_NONG_LANH, DIEN_NUOC, KHAC | loại thiết bị |
| `hang_san_xuat` | `hang_san_xuat` | CharField | varchar(50) |  |  | hãng sản xuất |
| `model` | `model` | CharField | varchar(50) |  |  | model |
| `vi_tri_lap` | `vi_tri_lap` | CharField | varchar(100) |  |  | vị trí lắp |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |

## Tho → `tblTho`

App `danh_muc` · thợ

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `nguoi_dung` | `nguoi_dung_id` | OneToOneField | bigint |  | UNIQUE; FK → tblNhanVien (NguoiDung), PROTECT | người dùng |
| `ho_ten` | `ho_ten` | CharField | varchar(100) |  |  | họ tên |
| `so_dien_thoai` | `so_dien_thoai` | CharField | varchar(10) |  | UNIQUE | số điện thoại |
| `hinh_thuc` | `hinh_thuc` | CharField | varchar(15) |  | chọn: CONG_TAC_VIEN, CHINH_THUC | hình thức |
| `dang_nhan_viec` | `dang_nhan_viec` | BooleanField | boolean |  | mặc định True | sẵn sàng nhận việc |
| `nghi_den` | `nghi_den` | DateTimeField | timestamp with time zone | có |  | nghỉ đến |
| `kenh_thong_bao` | `kenh_thong_bao` | CharField | varchar(10) |  | chọn: WEB_PUSH, TELEGRAM; mặc định 'WEB_PUSH' | kênh thông báo |
| `telegram_chat_id` | `telegram_chat_id` | CharField | varchar(50) | có |  | Telegram chat id |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |

Quan hệ nhiều–nhiều (bảng trung gian):

- `ky_nang` → `tblDichVu` (DichVu) qua bảng `tblTho_ky_nang`
- `khu_vuc_phu_trach` → `tblKhuVuc` (KhuVuc) qua bảng `tblTho_khu_vuc_phu_trach`

## AnhHienTruong → `tblAnhHienTruong`

App `don_sua_chua` · ảnh hiện trường

> Ảnh hiện trường / ảnh báo giá của đơn (UC08, UC09). Lớp hỗ trợ — A-67. Phục vụ qua /anh/<id>/ có kiểm quyền.

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `don` | `don_id` | ForeignKey | bigint |  | FK → tblDonSuaChua (DonSuaChua), CASCADE | đơn |
| `loai` | `loai` | CharField | varchar(12) |  | chọn: HIEN_TRUONG, BAO_GIA; mặc định 'HIEN_TRUONG' | loại |
| `tep` | `tep` | FileField | varchar(100) |  |  | tệp ảnh |
| `rong` | `rong` | PositiveIntegerField | integer |  |  | rộng (px) |
| `cao` | `cao` | PositiveIntegerField | integer |  |  | cao (px) |
| `nguoi_tai` | `nguoi_tai_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), PROTECT | người tải |

## DonSuaChua → `tblDonSuaChua`

App `don_sua_chua` · đơn sửa chữa

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ma_don` | `ma_don` | CharField | varchar(16) |  | UNIQUE | mã đơn |
| `khach_hang` | `khach_hang_id` | ForeignKey | bigint |  | FK → tblKhachHang (KhachHang), PROTECT | khách hàng |
| `dia_chi` | `dia_chi_id` | ForeignKey | bigint |  | FK → tblDiaChi (DiaChi), PROTECT | địa chỉ |
| `dich_vu_yeu_cau` | `dich_vu_yeu_cau_id` | ForeignKey | bigint |  | FK → tblDichVu (DichVu), PROTECT | dịch vụ yêu cầu |
| `kenh_tiep_nhan` | `kenh_tiep_nhan` | CharField | varchar(16) |  | chọn: DIEN_THOAI, ZALO, GIAM_DOC_CHUYEN, KHAC | kênh tiếp nhận |
| `mo_ta_su_co` | `mo_ta_su_co` | TextField | text |  |  | mô tả sự cố |
| `khung_gio_mong_muon` | `khung_gio_mong_muon` | CharField | varchar(100) |  |  | khung giờ mong muốn |
| `trang_thai` | `trang_thai` | CharField | varchar(20) |  | chọn: CHO_XAC_NHAN_LICH, CHO_CU_THO, DA_CO_THO, CHO_DUYET_GIA, DANG_SUA, HOAN_THANH, DANG_BAO_HANH, DA_HUY, DA_DONG | trạng thái |
| `loai_don` | `loai_don` | CharField | varchar(10) |  | chọn: THUONG, BAO_HANH; mặc định 'THUONG' | loại đơn |
| `don_goc` | `don_goc_id` | ForeignKey | bigint | có | FK → tblDonSuaChua (DonSuaChua), PROTECT | đơn gốc |
| `nguyen_nhan_bao_hanh` | `nguyen_nhan_bao_hanh` | CharField | varchar(15) | có | chọn: CHUA_XAC_DINH, TAY_NGHE, VAT_TU | nguyên nhân bảo hành |
| `tho` | `tho_id` | ForeignKey | bigint | có | FK → tblTho (Tho), PROTECT | thợ phụ trách |
| `uu_tien` | `uu_tien` | BooleanField | boolean |  | mặc định False | ưu tiên |
| `so_lan_giuc` | `so_lan_giuc` | PositiveSmallIntegerField | smallint |  | mặc định 0 | số lần khách giục |
| `so_lan_nhac_xac_nhan` | `so_lan_nhac_xac_nhan` | PositiveSmallIntegerField | smallint |  | mặc định 0 | số lần nhắc xác nhận |
| `lan_nhac_cuoi` | `lan_nhac_cuoi` | DateTimeField | timestamp with time zone | có |  | lần nhắc cuối |
| `bao_gia_tong` | `bao_gia_tong` | BigIntegerField | bigint | có |  | tổng báo giá |
| `bao_gia_nguoi_xac_nhan` | `bao_gia_nguoi_xac_nhan` | CharField | varchar(100) |  |  | người xác nhận báo giá |
| `bao_gia_xac_nhan_luc` | `bao_gia_xac_nhan_luc` | DateTimeField | timestamp with time zone | có |  | báo giá xác nhận lúc |
| `cho_tong_dai_xac_nhan_gia` | `cho_tong_dai_xac_nhan_gia` | BooleanField | boolean |  | mặc định False | chờ tổng đài xác nhận giá |
| `tong_tien_phai_thu` | `tong_tien_phai_thu` | BigIntegerField | bigint | có |  | tổng tiền phải thu |
| `ly_do_huy` | `ly_do_huy` | TextField | text |  |  | lý do hủy |
| `nguoi_tao` | `nguoi_tao_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), PROTECT | người tạo |
| `ngay_tiep_nhan` | `ngay_tiep_nhan` | DateTimeField | timestamp with time zone |  |  | ngày tiếp nhận |
| `canh_bao_chua_cu_duoc` | `canh_bao_chua_cu_duoc` | BooleanField | boolean |  | mặc định False | chưa cử được thợ |
| `ly_do_chua_cu_duoc` | `ly_do_chua_cu_duoc` | TextField | text |  |  | lý do chưa cử được |

Quan hệ nhiều–nhiều (bảng trung gian):

- `thiet_bi` → `tblThietBi` (ThietBi) qua bảng `tblDonSuaChua_thiet_bi`

Ràng buộc CSDL:

- `don_trang_thai_hop_le`: CHECK (AND: ('trang_thai__in', ['CHO_XAC_NHAN_LICH', 'CHO_CU_THO', 'DA_CO_THO', 'CHO_DUYET_GIA', 'DANG_SUA', 'HOAN_THANH', 'DANG_BAO_HANH', 'DA_HUY', 'DA_DONG']))
- `don_bao_hanh_co_don_goc`: CHECK (OR: (AND: ('don_goc__isnull', True), ('loai_don', 'THUONG')), (AND: ('don_goc__isnull', False), ('loai_don', 'BAO_HANH')))

Chỉ mục:

- `don_trang_thai_idx`: (trang_thai)

## HangMucSuaChua → `tblHangMucSuaChua`

App `don_sua_chua` · hạng mục sửa chữa

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `don` | `don_id` | ForeignKey | bigint |  | FK → tblDonSuaChua (DonSuaChua), CASCADE | đơn |
| `loai` | `loai` | CharField | varchar(10) |  | chọn: CONG, VAT_TU, PHI_KHAC | loại |
| `dich_vu` | `dich_vu_id` | ForeignKey | bigint | có | FK → tblDichVu (DichVu), PROTECT | dịch vụ |
| `thiet_bi` | `thiet_bi_id` | ForeignKey | bigint | có | FK → tblThietBi (ThietBi), PROTECT | thiết bị |
| `mo_ta` | `mo_ta` | CharField | varchar(255) |  |  | mô tả |
| `so_luong` | `so_luong` | DecimalField | numeric(10, 2) |  |  | số lượng |
| `don_gia_thuc_te` | `don_gia_thuc_te` | BigIntegerField | bigint |  |  | đơn giá thực tế (đ) |
| `gia_mua` | `gia_mua` | BigIntegerField | bigint | có |  | giá mua (đ) |
| `co_hoa_don` | `co_hoa_don` | BooleanField | boolean |  | mặc định False | có hóa đơn |
| `nguoi_ung` | `nguoi_ung` | CharField | varchar(10) |  | chọn: THO, CONG_TY; mặc định 'THO' | người ứng tiền |
| `la_bao_gia` | `la_bao_gia` | BooleanField | boolean |  | mặc định False | thuộc báo giá đã duyệt |
| `ben_chiu_chi_phi` | `ben_chiu_chi_phi` | CharField | varchar(10) |  | chọn: KHACH, THO, CONG_TY; mặc định 'KHACH' | bên chịu chi phí |

Ràng buộc CSDL:

- `hang_muc_so_luong_duong`: CHECK (AND: ('so_luong__gt', 0))
- `hang_muc_don_gia_khong_am`: CHECK (AND: ('don_gia_thuc_te__gte', 0))

## LichHen → `tblLichHen`

App `tiep_nhan_dieu_phoi` · lịch hẹn

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `don` | `don_id` | ForeignKey | bigint |  | FK → tblDonSuaChua (DonSuaChua), CASCADE | đơn |
| `bat_dau` | `bat_dau` | DateTimeField | timestamp with time zone |  |  | bắt đầu |
| `ket_thuc` | `ket_thuc` | DateTimeField | timestamp with time zone |  |  | kết thúc |
| `trang_thai` | `trang_thai` | CharField | varchar(12) |  | chọn: HIEU_LUC, DA_THAY_THE, DA_HUY; mặc định 'HIEU_LUC' | trạng thái |
| `ly_do_doi_hen` | `ly_do_doi_hen` | TextField | text |  |  | lý do đổi hẹn |
| `nguoi_tao` | `nguoi_tao_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), PROTECT | người tạo |

Ràng buộc CSDL:

- `mot_lich_hieu_luc_moi_don`: UNIQUE (don) WHERE (AND: ('trang_thai', 'HIEU_LUC'))
- `lich_ket_thuc_sau_bat_dau`: CHECK (AND: ('ket_thuc__gt', F(bat_dau)))

Chỉ mục:

- `lich_hen_don_trang_thai_idx`: (don, trang_thai)

## PhanCong → `tblPhanCong`

App `tiep_nhan_dieu_phoi` · phân công

> Một lượt đề nghị nhận việc gửi một thợ (SPEC 5.2). Máy trạng thái mục 6.2.

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `don` | `don_id` | ForeignKey | bigint |  | FK → tblDonSuaChua (DonSuaChua), CASCADE | đơn |
| `tho` | `tho_id` | ForeignKey | bigint |  | FK → tblTho (Tho), PROTECT | thợ |
| `nguoi_giao` | `nguoi_giao_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), PROTECT | người giao |
| `thoi_diem_giao` | `thoi_diem_giao` | DateTimeField | timestamp with time zone |  |  | thời điểm giao |
| `han_phan_hoi` | `han_phan_hoi` | DateTimeField | timestamp with time zone |  |  | hạn phản hồi |
| `trang_thai` | `trang_thai` | CharField | varchar(12) |  | chọn: CHO_PHAN_HOI, DA_NHAN, TU_CHOI, QUA_HAN, DA_HUY; mặc định 'CHO_PHAN_HOI' | trạng thái |
| `thoi_diem_phan_hoi` | `thoi_diem_phan_hoi` | DateTimeField | timestamp with time zone | có |  | thời điểm phản hồi |
| `ly_do_tu_choi` | `ly_do_tu_choi` | CharField | varchar(25) | có | chọn: BAN, XA, KHONG_DUNG_CHUYEN_MON, KHAC | lý do từ chối |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |
| `tien_cong_du_kien` | `tien_cong_du_kien` | BigIntegerField | bigint |  |  | tiền công dự kiến (đ) |
| `giao_qua_dien_thoai` | `giao_qua_dien_thoai` | BooleanField | boolean |  | mặc định False | thợ đồng ý qua điện thoại |

Ràng buộc CSDL:

- `mot_phan_cong_da_nhan_moi_don`: UNIQUE (don) WHERE (AND: ('trang_thai', 'DA_NHAN'))

Chỉ mục:

- `phan_cong_trang_thai_idx`: (trang_thai)
- `phan_cong_tho_trang_thai_idx`: (tho, trang_thai)

## PhieuDoiSoat → `tblPhieuDoiSoat`

App `tai_chinh` · phiếu đối soát

> Phiếu đối soát tiền thợ đã thu (UC12, SPEC 5.2). so_phai_nop âm = công ty phải trả thợ.

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ma` | `ma` | CharField | varchar(30) |  | UNIQUE | mã |
| `tho` | `tho_id` | ForeignKey | bigint |  | FK → tblTho (Tho), PROTECT | thợ |
| `tu_ngay` | `tu_ngay` | DateField | date |  |  | từ ngày |
| `den_ngay` | `den_ngay` | DateField | date |  |  | đến ngày |
| `tong_tien_thu` | `tong_tien_thu` | BigIntegerField | bigint |  | mặc định 0 | tổng tiền thu (đ) |
| `tong_vat_tu_ung` | `tong_vat_tu_ung` | BigIntegerField | bigint |  | mặc định 0 | tổng vật tư thợ ứng (đ) |
| `so_phai_nop` | `so_phai_nop` | BigIntegerField | bigint |  | mặc định 0 | số phải nộp (đ) |
| `trang_thai` | `trang_thai` | CharField | varchar(8) |  | chọn: NHAP, DA_CHOT, DA_NOP; mặc định 'NHAP' | trạng thái |
| `nguoi_lap` | `nguoi_lap_id` | ForeignKey | bigint |  | FK → tblNhanVien (NguoiDung), PROTECT | người lập |
| `xac_nhan_luc` | `xac_nhan_luc` | DateTimeField | timestamp with time zone | có |  | xác nhận nộp lúc |
| `ghi_chu` | `ghi_chu` | TextField | text |  |  | ghi chú |

Ràng buộc CSDL:

- `doi_soat_den_sau_tu`: CHECK (AND: ('den_ngay__gte', F(tu_ngay)))
- `doi_soat_so_phai_nop_khop`: CHECK (AND: ('so_phai_nop', <CombinedExpression: F(tong_tien_thu) - F(tong_vat_tu_ung)>))

## ThanhToan → `tblThanhToan`

App `tai_chinh` · thanh toán

> Một khoản tiền thợ ghi nhận đã thu của khách (SPEC 5.2).

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `don` | `don_id` | ForeignKey | bigint |  | FK → tblDonSuaChua (DonSuaChua), PROTECT | đơn |
| `tho` | `tho_id` | ForeignKey | bigint |  | FK → tblTho (Tho), PROTECT | thợ |
| `so_tien` | `so_tien` | BigIntegerField | bigint |  |  | số tiền (đ) |
| `hinh_thuc` | `hinh_thuc` | CharField | varchar(22) |  | chọn: TIEN_MAT, CK_TAI_KHOAN_CONG_TY, CK_TAI_KHOAN_THO | hình thức |
| `thoi_diem_thu` | `thoi_diem_thu` | DateTimeField | timestamp with time zone |  |  | thời điểm thu |
| `trang_thai` | `trang_thai` | CharField | varchar(14) |  | chọn: CHUA_NOP, DA_NOP, KHONG_CAN_NOP | trạng thái |
| `anh_chung_tu` | `anh_chung_tu` | FileField | varchar(100) |  |  | ảnh chứng từ |
| `phieu_doi_soat` | `phieu_doi_soat_id` | ForeignKey | bigint | có | FK → tblPhieuDoiSoat (PhieuDoiSoat), PROTECT | phiếu đối soát |

Ràng buộc CSDL:

- `thanh_toan_so_tien_khong_am`: CHECK (AND: ('so_tien__gte', 0))

Chỉ mục:

- `thanh_toan_tho_trang_thai_idx`: (tho, trang_thai)

## PhieuBaoHanh → `tblPhieuBaoHanh`

App `bao_hanh` · phiếu bảo hành

| Trường | Cột | Kiểu Django | Kiểu CSDL | Null | Ràng buộc | Mô tả |
|---|---|---|---|---|---|---|
| `id` | `id` | BigAutoField | bigint |  | PK | ID |
| `tao_luc` | `tao_luc` | DateTimeField | timestamp with time zone |  |  | tạo lúc |
| `cap_nhat_luc` | `cap_nhat_luc` | DateTimeField | timestamp with time zone |  |  | cập nhật lúc |
| `ma` | `ma` | CharField | varchar(20) |  | UNIQUE | mã |
| `don` | `don_id` | OneToOneField | bigint |  | UNIQUE; FK → tblDonSuaChua (DonSuaChua), PROTECT | đơn |
| `ngay_bat_dau` | `ngay_bat_dau` | DateField | date |  |  | ngày bắt đầu |
| `ngay_het_han` | `ngay_het_han` | DateField | date |  |  | ngày hết hạn |
| `dieu_kien` | `dieu_kien` | TextField | text |  |  | điều kiện bảo hành |

Ràng buộc CSDL:

- `bao_hanh_het_han_sau_bat_dau`: CHECK (AND: ('ngay_het_han__gte', F(ngay_bat_dau)))
