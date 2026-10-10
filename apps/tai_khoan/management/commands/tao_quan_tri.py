import getpass
import os

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.tai_khoan.dao import NguoiDungDAO

BIEN_MAT_KHAU = "HOMEFIX_MAT_KHAU_QUAN_TRI"


class Command(BaseCommand):
    help = "Tạo tài khoản QUAN_TRI đầu tiên (hỏi họ tên, số điện thoại, mật khẩu)."

    def add_arguments(self, parser):
        parser.add_argument("--ho-ten")
        parser.add_argument("--sdt")
        parser.add_argument(
            "--no-input",
            action="store_true",
            help=f"Không hỏi; mật khẩu lấy từ biến môi trường {BIEN_MAT_KHAU}.",
        )

    def handle(self, *args, ho_ten=None, sdt=None, no_input=False, **options):
        if no_input:
            mat_khau = os.environ.get(BIEN_MAT_KHAU, "")
            if not (ho_ten and sdt and mat_khau):
                raise CommandError(f"Cần --ho-ten, --sdt và biến môi trường {BIEN_MAT_KHAU}.")
        else:
            ho_ten = ho_ten or input("Họ tên: ")
            sdt = sdt or input("Số điện thoại: ")
            mat_khau = getpass.getpass("Mật khẩu: ")
            if mat_khau != getpass.getpass("Nhập lại mật khẩu: "):
                raise CommandError("Hai lần nhập mật khẩu không khớp.")
        try:
            nguoi_dung = NguoiDungDAO.tao_quan_tri(ho_ten, sdt, mat_khau)
        except ValidationError as loi:
            raise CommandError("; ".join(loi.messages)) from loi
        self.stdout.write(
            self.style.SUCCESS(f"Đã tạo quản trị {nguoi_dung.ho_ten}, đăng nhập bằng {nguoi_dung.username}.")
        )
