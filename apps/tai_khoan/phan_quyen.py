"""Phân quyền theo vai trò (SPEC 3.1). Kiểm tra ở cả view (decorator/mixin) lẫn DAO (kiem_tra_vai_tro)."""

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .models import VaiTro

QT, TD, THO, KT, GD = VaiTro.QUAN_TRI, VaiTro.TONG_DAI, VaiTro.THO, VaiTro.KE_TOAN, VaiTro.GIAM_DOC

# Nhóm vai trò dùng nhiều lần. QUAN_TRI tự có quyền của TONG_DAI (NguoiDung.la_vai_tro).
CHI_QUAN_TRI = (QT,)
QUAN_TRI_GIAM_DOC = (QT, GD)
VAN_PHONG = (QT, TD, KT, GD)
MOI_VAI_TRO = (QT, TD, THO, KT, GD)
GHI_KHACH_HANG = (TD,)  # TONG_DAI và QUAN_TRI


def co_vai_tro(nguoi_dung, *vai_tro) -> bool:
    return bool(
        nguoi_dung is not None
        and nguoi_dung.is_authenticated
        and nguoi_dung.is_active
        and nguoi_dung.la_vai_tro(*vai_tro)
    )


def kiem_tra_vai_tro(nguoi_dung, *vai_tro) -> None:
    """Dùng trong DAO: ném PermissionDenied nếu người dùng không có một trong các vai trò."""
    if not co_vai_tro(nguoi_dung, *vai_tro):
        raise PermissionDenied("Bạn không có quyền thực hiện thao tác này.")


def yeu_cau_vai_tro(*vai_tro):
    """Decorator view: chưa đăng nhập → trang đăng nhập; sai vai trò → 403."""

    def trang_tri(view):
        @wraps(view)
        def boc(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            kiem_tra_vai_tro(request.user, *vai_tro)
            return view(request, *args, **kwargs)

        boc.vai_tro_duoc_phep = vai_tro
        return boc

    return trang_tri


class YeuCauVaiTroMixin:
    """Mixin cho class-based view, cùng quy tắc với yeu_cau_vai_tro."""

    vai_tro_duoc_phep: tuple = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        kiem_tra_vai_tro(request.user, *self.vai_tro_duoc_phep)
        return super().dispatch(request, *args, **kwargs)
