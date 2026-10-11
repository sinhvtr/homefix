from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.he_thong.bieu_mau import gan_loi_vao_form
from apps.he_thong.models import CauHinh

from .dao import CauHinhDAO, NguoiDungDAO
from .forms import CauHinhForm, DangNhapForm, DoiMatKhauForm, NguoiDungForm
from .models import NguoiDung, VaiTro
from .phan_quyen import CHI_QUAN_TRI, QUAN_TRI_GIAM_DOC, co_vai_tro, yeu_cau_vai_tro

TRANG_DICH_THEO_VAI_TRO = {
    VaiTro.QUAN_TRI: "tong_dai",
    VaiTro.TONG_DAI: "tong_dai",
    VaiTro.THO: "thuc_hien:trang_chu",
    VaiTro.KE_TOAN: "tai_chinh:tong_hop",
    VaiTro.GIAM_DOC: "bao_cao",
}

GHI_NHO_THO_GIAY = 30 * 24 * 3600  # Ghi nhớ đăng nhập 30 ngày trên điện thoại thợ (UC01)


class DangNhapView(auth_views.LoginView):
    template_name = "tai_khoan/dang_nhap.html"
    authentication_form = DangNhapForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        phan_hoi = super().form_valid(form)
        if self.request.user.vai_tro == VaiTro.THO:
            self.request.session.set_expiry(GHI_NHO_THO_GIAY)
        return phan_hoi


@login_required
def trang_chu(request):
    """Chuyển hướng sau đăng nhập theo vai trò (UC01)."""
    return redirect(TRANG_DICH_THEO_VAI_TRO.get(request.user.vai_tro, "tai_khoan:dang_nhap"))


@login_required
def doi_mat_khau(request):
    form = DoiMatKhauForm(request.user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        NguoiDungDAO.doi_mat_khau(request.user, form.cleaned_data["mat_khau_moi"])
        update_session_auth_hash(request, request.user)
        messages.success(request, "Đã đổi mật khẩu / PIN.")
        return redirect("tai_khoan:trang_chu")
    return render(
        request,
        "chung/bieu_mau.html",
        {
            "form": form,
            "tieu_de": "Đổi mã PIN" if request.user.vai_tro == VaiTro.THO else "Đổi mật khẩu",
            "ghi_chu": "Bạn cần đổi mật khẩu / PIN trước khi tiếp tục."
            if request.user.phai_doi_mat_khau
            else "",
            "nut": "Đổi",
        },
    )


# ---------- Quản trị: người dùng ----------


@yeu_cau_vai_tro(*QUAN_TRI_GIAM_DOC)
def nguoi_dung_danh_sach(request):
    tu_khoa = request.GET.get("q", "").strip()
    return render(
        request,
        "tai_khoan/nguoi_dung_danh_sach.html",
        {
            "ds": NguoiDungDAO.lay_danh_sach(request.user, tu_khoa),
            "q": tu_khoa,
            "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI),
        },
    )


def _hien_bi_mat(request, nguoi, bi_mat):
    loai = "mã PIN" if nguoi.vai_tro == VaiTro.THO else "mật khẩu tạm"
    messages.warning(
        request,
        f"{loai.capitalize()} của {nguoi.ho_ten} ({nguoi.username}): {bi_mat} — chỉ hiện một lần, "
        "hãy báo trực tiếp cho người dùng. Họ phải đổi ở lần đăng nhập đầu.",
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def nguoi_dung_moi(request):
    form = NguoiDungForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            nguoi, mat_khau = NguoiDungDAO.tao_nguoi_dung(request.user, **form.cleaned_data)
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            _hien_bi_mat(request, nguoi, mat_khau)
            return redirect("tai_khoan:nguoi_dung_danh_sach")
    return render(
        request, "chung/bieu_mau.html", {"form": form, "tieu_de": "Thêm người dùng", "quay_lai": "../"}
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def nguoi_dung_sua(request, pk):
    doi_tuong = get_object_or_404(NguoiDung, pk=pk)
    if doi_tuong.vai_tro == VaiTro.THO and hasattr(doi_tuong, "tho"):
        return redirect("danh_muc:tho_sua", pk=doi_tuong.tho.pk)
    ban_dau = {
        "ho_ten": doi_tuong.ho_ten,
        "so_dien_thoai": doi_tuong.so_dien_thoai,
        "vai_tro": doi_tuong.vai_tro,
    }
    form = NguoiDungForm(request.POST or None, initial=ban_dau, cho_phep_tho=doi_tuong.vai_tro == VaiTro.THO)
    if request.method == "POST" and form.is_valid():
        try:
            NguoiDungDAO.cap_nhat(request.user, doi_tuong, **form.cleaned_data)
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            messages.success(request, "Đã lưu người dùng.")
            return redirect("tai_khoan:nguoi_dung_danh_sach")
    return render(
        request,
        "chung/bieu_mau.html",
        {"form": form, "tieu_de": f"Sửa người dùng {doi_tuong.ho_ten}", "quay_lai": "../../"},
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def nguoi_dung_khoa(request, pk):
    doi_tuong = get_object_or_404(NguoiDung, pk=pk)
    try:
        doi_tuong = NguoiDungDAO.dat_khoa(request.user, doi_tuong, khoa=doi_tuong.is_active)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, f"Đã {'mở khóa' if doi_tuong.is_active else 'khóa'} {doi_tuong.ho_ten}.")
    return redirect(request.POST.get("tiep") or "tai_khoan:nguoi_dung_danh_sach")


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def nguoi_dung_dat_lai_mat_khau(request, pk):
    doi_tuong = get_object_or_404(NguoiDung, pk=pk)
    _hien_bi_mat(request, doi_tuong, NguoiDungDAO.dat_lai_mat_khau(request.user, doi_tuong))
    return redirect(request.POST.get("tiep") or "tai_khoan:nguoi_dung_danh_sach")


# ---------- Quản trị: cấu hình ----------


@yeu_cau_vai_tro(*QUAN_TRI_GIAM_DOC)
def cau_hinh_danh_sach(request):
    return render(
        request,
        "tai_khoan/cau_hinh_danh_sach.html",
        {"ds": CauHinhDAO.lay_danh_sach(request.user), "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI)},
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def cau_hinh_sua(request, pk):
    ban_ghi = get_object_or_404(CauHinh, pk=pk)
    form = CauHinhForm(request.POST or None, initial={"gia_tri": ban_ghi.gia_tri})
    if request.method == "POST" and form.is_valid():
        try:
            CauHinhDAO.sua(request.user, ban_ghi, form.cleaned_data["gia_tri"])
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            messages.success(request, f"Đã lưu {ban_ghi.khoa}.")
            return redirect("tai_khoan:cau_hinh_danh_sach")
    return render(
        request,
        "chung/bieu_mau.html",
        {
            "form": form,
            "tieu_de": f"Sửa cấu hình {ban_ghi.khoa}",
            "ghi_chu": f"{ban_ghi.mo_ta} (kiểu {ban_ghi.get_kieu_display()})",
            "quay_lai": "../../",
        },
    )
