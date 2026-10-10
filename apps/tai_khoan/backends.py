from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


class XacThucSdtHoacTenDangNhap(ModelBackend):
    """Đăng nhập bằng tên đăng nhập hoặc số điện thoại (UC01)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        NguoiDung = get_user_model()
        nguoi_dung = NguoiDung.objects.filter(username=username).first()
        if nguoi_dung is None:
            try:
                sdt = chuan_hoa_sdt(username)
            except ValidationError:
                sdt = None
            if sdt:
                nguoi_dung = NguoiDung.objects.filter(so_dien_thoai=sdt).first()
        if nguoi_dung is None:
            # Chạy băm mật khẩu để thời gian phản hồi không lộ việc tài khoản có tồn tại hay không.
            NguoiDung().set_password(password)
            return None
        if nguoi_dung.check_password(password) and self.user_can_authenticate(nguoi_dung):
            return nguoi_dung
        return None
