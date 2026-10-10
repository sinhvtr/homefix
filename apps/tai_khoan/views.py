from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .forms import DangNhapForm
from .models import VaiTro

TRANG_DICH_THEO_VAI_TRO = {
    VaiTro.QUAN_TRI: "tong_dai",
    VaiTro.TONG_DAI: "tong_dai",
    VaiTro.THO: "tho_trang_chu",
    VaiTro.KE_TOAN: "ke_toan_doi_soat",
    VaiTro.GIAM_DOC: "bao_cao",
}


class DangNhapView(auth_views.LoginView):
    template_name = "tai_khoan/dang_nhap.html"
    authentication_form = DangNhapForm
    redirect_authenticated_user = True


@login_required
def trang_chu(request):
    """Chuyển hướng sau đăng nhập theo vai trò (UC01)."""
    return redirect(TRANG_DICH_THEO_VAI_TRO.get(request.user.vai_tro, "tai_khoan:dang_nhap"))
