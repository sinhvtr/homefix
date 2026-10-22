from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.danh_muc.du_lieu_mau import TIEN_TO_SDT
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.mat_khau import sinh_mat_khau_tam, sinh_pin
from apps.tai_khoan.models import NguoiDung, VaiTro


class Command(BaseCommand):
    help = (
        "Cấp mật khẩu/PIN mới cho các tài khoản MẪU (SĐT 0900…) mà không xóa dữ liệu — dùng khi mất bảng mật khẩu "
        "hoặc trước buổi demo. In bảng MỘT lần."
    )

    def handle(self, *args, **options):
        ds = list(
            NguoiDung.objects.filter(so_dien_thoai__startswith=TIEN_TO_SDT, is_active=True).order_by(
                "so_dien_thoai"
            )
        )
        if not ds:
            raise CommandError("Chưa có dữ liệu mẫu — chạy `python manage.py nap_du_lieu_mau`.")
        bang = []
        with transaction.atomic():
            for nd in ds:
                bi_mat = sinh_pin() if nd.vai_tro == VaiTro.THO else sinh_mat_khau_tam()
                nd.set_password(bi_mat)
                nd.phai_doi_mat_khau = False
                nd.save(update_fields=["password", "phai_doi_mat_khau"])
                bang.append((nd.get_vai_tro_display(), nd.ho_ten, nd.username, bi_mat))
            ghi_nhat_ky(
                None, "CAP_LAI_MAT_KHAU_MAU", "NguoiDung:mau", du_lieu_sau={"so_tai_khoan": len(bang)}
            )
        self.stdout.write(self.style.WARNING("Mật khẩu / PIN mẫu mới — chỉ in MỘT lần, hãy lưu lại:"))
        self.stdout.write(f"{'Vai trò':<10} {'Họ tên':<26} {'Tên đăng nhập':<14} Mật khẩu/PIN")
        for vai_tro, ho_ten, ten, bi_mat in bang:
            self.stdout.write(f"{vai_tro:<10} {ho_ten:<26} {ten:<14} {bi_mat}")
