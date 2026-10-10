from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ValidationError

from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


def tim_nguoi_dung(ten_dang_nhap: str | None):
    """Tìm theo tên đăng nhập; không thấy thì chuẩn hóa như số điện thoại rồi tìm theo SĐT."""
    if not ten_dang_nhap:
        return None
    NguoiDung = get_user_model()
    nguoi_dung = NguoiDung.objects.filter(username=ten_dang_nhap).first()
    if nguoi_dung is None:
        try:
            sdt = chuan_hoa_sdt(ten_dang_nhap)
        except ValidationError:
            return None
        nguoi_dung = NguoiDung.objects.filter(so_dien_thoai=sdt).first()
    return nguoi_dung


def ten_dang_nhap_chuan(request, credentials) -> str | None:
    """Cho django-axes: '0912.345.678' và '+84912345678' tính chung một bộ đếm sai với tài khoản đó."""
    ten = (credentials or {}).get("username")
    nguoi_dung = tim_nguoi_dung(ten)
    if nguoi_dung is not None:
        return nguoi_dung.username
    try:
        return chuan_hoa_sdt(ten)
    except ValidationError:
        return ten


class XacThucSdtHoacTenDangNhap(ModelBackend):
    """Đăng nhập bằng tên đăng nhập hoặc số điện thoại (UC01)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        nguoi_dung = tim_nguoi_dung(username)
        if nguoi_dung is None:
            # Chạy băm mật khẩu để thời gian phản hồi không lộ việc tài khoản có tồn tại hay không.
            get_user_model()().set_password(password)
            return None
        if nguoi_dung.check_password(password) and self.user_can_authenticate(nguoi_dung):
            return nguoi_dung
        return None
