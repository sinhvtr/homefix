from django.core.management.base import BaseCommand, CommandError

from apps.danh_muc.du_lieu_mau import DaCoDuLieuMau, nap_danh_muc


class Command(BaseCommand):
    help = "Nạp dữ liệu mẫu hư cấu để thử (SPEC 14.4). P1: khu vực, dịch vụ, người dùng, thợ, khách hàng."

    def handle(self, *args, **options):
        try:
            tai_khoan = nap_danh_muc()
        except DaCoDuLieuMau as loi:
            raise CommandError(str(loi)) from loi
        self.stdout.write(
            self.style.SUCCESS("Đã nạp dữ liệu mẫu: 12 khu vực, 20 dịch vụ, 18 người dùng, 40 khách.")
        )
        self.stdout.write(
            self.style.WARNING("Mật khẩu / PIN dưới đây chỉ in MỘT lần — hãy lưu lại nếu cần thử:")
        )
        self.stdout.write(f"{'Vai trò':<10} {'Họ tên':<26} {'Tên đăng nhập':<14} Mật khẩu/PIN")
        for vai_tro, ho_ten, ten_dang_nhap, bi_mat in tai_khoan:
            self.stdout.write(f"{vai_tro:<10} {ho_ten:<26} {ten_dang_nhap:<14} {bi_mat}")
