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