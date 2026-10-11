"""UC11 — tạo đơn bảo hành / làm lại (tổng đài). View chỉ gọi DAO."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render

from apps.don_sua_chua.dao import GHI_DON, DonSuaChuaDAO
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.bieu_mau import gan_loi_vao_form
from apps.tai_khoan.phan_quyen import yeu_cau_vai_tro

from .dao import BaoHanhDAO
from .forms import DonBaoHanhForm


@yeu_cau_vai_tro(*GHI_DON)
def tao_don_bao_hanh(request):
    """/bao-hanh/moi/?don_goc=<ma_don>: kiểm tra đơn gốc HOAN_THANH + phiếu còn hạn; hết hạn → chặn, gợi ý đơn thường."""
    ma_goc = request.GET.get("don_goc") or request.POST.get("don_goc") or ""
    try:
        goc = DonSuaChuaDAO.lay_theo_ma(request.user, ma_goc)
    except DonSuaChua.DoesNotExist as loi:
        raise Http404("Không có đơn gốc này.") from loi
    loi_goc = ""
    try:
        BaoHanhDAO.kiem_tra_don_goc(goc)
    except ValidationError as loi:
        loi_goc = " ".join(loi.messages)
    form = DonBaoHanhForm(request.POST or None, initial={"mo_ta_su_co": ""})
    if request.method == "POST" and not loi_goc and form.is_valid():
        d = form.cleaned_data
        try:
            don_bh = BaoHanhDAO.tao_don_bao_hanh(
                request.user,
                goc,
                mo_ta_su_co=d["mo_ta_su_co"],
                kenh_tiep_nhan=d["kenh_tiep_nhan"],
                ngay_hen=d["ngay_hen"],
                khung_gio=d["khung_gio"],
            )
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            messages.success(
                request,
                f"Đã tạo đơn bảo hành {don_bh.ma_don} — {don_bh.get_trang_thai_display()}. "
                f"Đơn gốc {goc.ma_don} chuyển “Đang bảo hành”.",
            )
            return redirect("chi_tiet_don", ma_don=don_bh.ma_don)
    return render(
        request,
        "bao_hanh/tao_don_bao_hanh.html",
        {"goc": goc, "phieu": getattr(goc, "phieu_bao_hanh", None), "loi_goc": loi_goc, "form": form},
    )
