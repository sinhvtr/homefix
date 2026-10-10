"""Màn hình tổng đài: bảng đơn (UC06), tiếp nhận (UC02), chi tiết đơn + lịch hẹn (UC03). View chỉ gọi DAO."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.danh_muc.dao import KhachHangDAO
from apps.don_sua_chua.dao import GHI_DON, XEM_BANG_DON, XEM_DON, DonSuaChuaDAO, HienTruongDAO, LocBangDon
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import ChuyenTrangThaiKhongHopLe, TrangThaiDon
from apps.he_thong.bieu_mau import gan_loi_vao_form
from apps.he_thong.cau_hinh import cau_hinh
from apps.tai_khoan.phan_quyen import co_vai_tro, yeu_cau_vai_tro

from .dao import DUOC_DOI_HEN, LichHenDAO, TiepNhanDAO
from .forms import HuyDonForm, LichHenForm, LocBangDonForm, TiepNhanForm
from .tin_nhan import tin_nhan_goi_lai, tin_nhan_xac_nhan_lich

T = TrangThaiDon


def _lay_don(request, ma_don: str) -> DonSuaChua:
    try:
        return DonSuaChuaDAO.lay_theo_ma(request.user, ma_don)
    except DonSuaChua.DoesNotExist as loi:
        raise Http404("Không có đơn này.") from loi


# ================================================================ UC06 — bảng đơn


@yeu_cau_vai_tro(*XEM_BANG_DON)
def bang_don(request):
    form_loc = LocBangDonForm(request.GET or None)
    loc = LocBangDon()
    if form_loc.is_valid():
        d = form_loc.cleaned_data
        loc = LocBangDon(
            ngay=d["ngay"],
            khu_vuc=d["khu_vuc"].pk if d["khu_vuc"] else None,
            trang_thai=d["trang_thai"],
            tho=d["tho"],
            tu_khoa=d["q"],
        )
    bang = DonSuaChuaDAO.bang_don_trong_ngay(request.user, loc)
    ngu_canh = {
        "bang": bang,
        "form_loc": form_loc,
        "duoc_ghi": co_vai_tro(request.user, *GHI_DON),  # giám đốc xem chỉ đọc
        "goi_lai": [(d, tin_nhan_goi_lai(d)) for d in bang.goi_lai_khach],
        "phut_canh_bao": cau_hinh("CANH_BAO_CHO_CU_THO_PHUT"),
    }
    if request.htmx:  # tự làm mới mỗi 30 giây: chỉ trả phần bảng
        return render(request, "tiep_nhan/_bang_don_noi_dung.html", ngu_canh)
    return render(request, "tiep_nhan/bang_don.html", ngu_canh)


@require_POST
@yeu_cau_vai_tro(*GHI_DON)
def khach_giuc(request, ma_don):
    don = _lay_don(request, ma_don)
    try:
        so_lan = DonSuaChuaDAO.khach_giuc(request.user, don)
        messages.success(request, f"{don.ma_don}: khách giục lần {so_lan}.")
    except ValueError as loi:
        messages.error(request, str(loi))
    return redirect(request.POST.get("tiep") or "tong_dai")


# ================================================================ UC02 — tiếp nhận


@yeu_cau_vai_tro(*GHI_DON)
def tra_cuu_khach(request):
    """HTMX: gõ SĐT → tên, nhãn VIP, địa chỉ, thiết bị theo địa chỉ, 5 đơn gần nhất."""
    sdt_vao = (request.GET.get("sdt") or request.GET.get("so_dien_thoai") or "").strip()
    ngu_canh = {"sdt": sdt_vao, "chon_dia_chi": request.GET.get("dia_chi_id"), "chon_thiet_bi": []}
    if sdt_vao:
        try:
            ngu_canh["kh"] = KhachHangDAO.tra_cuu_theo_sdt(request.user, sdt_vao)
        except ValidationError as loi:
            ngu_canh["loi"] = " ".join(loi.messages)
    return render(request, "tiep_nhan/_ket_qua_tra_cuu.html", ngu_canh)


@yeu_cau_vai_tro(*GHI_DON)
def tiep_nhan(request):
    form = TiepNhanForm(request.POST or None, initial={"so_dien_thoai": request.GET.get("sdt", "")})
    if request.method == "POST" and form.is_valid():
        try:
            kq = TiepNhanDAO.tiep_nhan(request.user, form.cleaned_data)
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            messages.success(request, f"Đã tạo đơn {kq.don.ma_don} — {kq.don.get_trang_thai_display()}.")
            if kq.ds_trung:
                messages.warning(
                    request, f"Có thể trùng đơn {', '.join(kq.ds_trung)} (cùng địa chỉ, cùng loại thiết bị)."
                )
            return redirect("chi_tiet_don", ma_don=kq.don.ma_don)
    # Vẽ sẵn khối tra cứu khi đã có SĐT (mở lại form lỗi hoặc “Tạo thêm đơn cho cuộc gọi này”)
    sdt = request.POST.get("so_dien_thoai") or request.GET.get("sdt") or ""
    kh = None
    if sdt:
        try:
            kh = KhachHangDAO.tra_cuu_theo_sdt(request.user, sdt)
        except ValidationError:
            kh = None
    return render(
        request,
        "tiep_nhan/gd_tiep_nhan.html",
        {
            "form": form,
            "kh": kh,
            "sdt": sdt,
            "chon_dia_chi": request.POST.get("dia_chi_id") or request.GET.get("dia_chi"),
            "chon_thiet_bi": request.POST.getlist("thiet_bi_ids"),
        },
    )


# ================================================================ Chi tiết đơn, UC03 — lịch hẹn


@yeu_cau_vai_tro(*XEM_DON)
def chi_tiet_don(request, ma_don):
    don = _lay_don(request, ma_don)
    duoc_ghi = co_vai_tro(request.user, *GHI_DON)
    lich = don.lich_hieu_luc
    return render(
        request,
        "tiep_nhan/chi_tiet_don.html",
        {
            "don": don,
            "lich": lich,
            "lich_su_lich": LichHenDAO.lich_su(don),
            "nhat_ky": DonSuaChuaDAO.nhat_ky_don(request.user, don),
            "duoc_ghi": duoc_ghi,
            "an_sdt": not duoc_ghi,  # OI-05
            "tin_nhan": tin_nhan_xac_nhan_lich(don) if lich else "",
            "tin_nhan_goi_lai": tin_nhan_goi_lai(don) if don.trang_thai == T.CHO_XAC_NHAN_LICH else "",
            "form_chot_lich": LichHenForm(prefix="chot")
            if duoc_ghi and don.trang_thai == T.CHO_XAC_NHAN_LICH
            else None,
            "form_doi_hen": (
                LichHenForm(prefix="doi", doi_hen=True)
                if duoc_ghi and lich and don.trang_thai in DUOC_DOI_HEN
                else None
            ),
            "dang_xu_ly": don.dang_xu_ly,
            "tien": don.bang_tinh_tien(),
            "ds_anh": list(don.ds_anh.all()),
            "ds_thanh_toan": list(don.ds_thanh_toan.all()),
            "phieu_bao_hanh": getattr(don, "phieu_bao_hanh", None),
        },
    )


def _form_lich(request, ma_don, doi_hen: bool):
    don = _lay_don(request, ma_don)
    form = LichHenForm(request.POST, prefix="doi" if doi_hen else "chot", doi_hen=doi_hen)
    if form.is_valid():
        d = form.cleaned_data
        try:
            if doi_hen:
                lich = LichHenDAO.doi_hen(request.user, don, d["ngay"], d["khung_gio"], d["ly_do"])
                messages.success(request, f"Đã đổi hẹn sang {lich.khung_gio}.")
            else:
                lich = LichHenDAO.chot_lich(request.user, don, d["ngay"], d["khung_gio"])
                messages.success(request, f"Đã chốt lịch {lich.khung_gio}. Đơn chuyển sang “Chờ cử thợ”.")
        except (ValidationError, ChuyenTrangThaiKhongHopLe) as loi:
            messages.error(request, " ".join(getattr(loi, "messages", [str(loi)])))
    else:
        messages.error(
            request, "; ".join(f"{form.fields[k].label}: {' '.join(v)}" for k, v in form.errors.items())
        )
    return redirect("chi_tiet_don", ma_don=ma_don)


@require_POST
@yeu_cau_vai_tro(*GHI_DON)
def chot_lich(request, ma_don):
    return _form_lich(request, ma_don, doi_hen=False)


@require_POST
@yeu_cau_vai_tro(*GHI_DON)
def doi_hen(request, ma_don):
    return _form_lich(request, ma_don, doi_hen=True)


@require_POST
@yeu_cau_vai_tro(*GHI_DON)
def khach_chua_tra_loi(request, ma_don):
    """Nút “Khách chưa trả lời” — đếm chung với BR08 (UC03)."""
    don = _lay_don(request, ma_don)
    try:
        con_luot = DonSuaChuaDAO.nhac_xac_nhan(request.user, don)
    except ChuyenTrangThaiKhongHopLe as loi:
        messages.error(request, str(loi))
    else:
        if con_luot:
            messages.info(request, "Đã ghi nhận khách chưa trả lời.")
        else:
            messages.warning(request, "Đã nhắc đủ số lần tối đa — đơn bị hủy (BR08).")
    return redirect("chi_tiet_don", ma_don=ma_don)


@yeu_cau_vai_tro(*GHI_DON)
def huy_don(request, ma_don):
    don = _lay_don(request, ma_don)
    form = HuyDonForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            DonSuaChuaDAO.huy(request.user, don, form.cleaned_data["ly_do"])
        except ChuyenTrangThaiKhongHopLe as loi:
            form.add_error(None, str(loi))
        else:
            messages.success(request, f"Đã hủy đơn {don.ma_don}.")
            return redirect("chi_tiet_don", ma_don=ma_don)
    return render(
        request,
        "chung/bieu_mau.html",
        {
            "form": form,
            "tieu_de": f"Hủy đơn {don.ma_don}",
            "ghi_chu": "Khách hủy đơn: lịch hẹn hiệu lực và đề nghị nhận việc đang chờ cũng bị hủy.",
            "nut": "Hủy đơn",
            "quay_lai": reverse("chi_tiet_don", args=[ma_don]),
        },
    )


@require_POST
@yeu_cau_vai_tro(*GHI_DON)
def xac_nhan_gia(request, ma_don):
    """T12: tổng đài đã gọi khách xác nhận báo giá vượt ngưỡng (OI-08)."""
    don = _lay_don(request, ma_don)
    try:
        HienTruongDAO.tong_dai_xac_nhan_gia(request.user, don)
    except ChuyenTrangThaiKhongHopLe as loi:
        messages.error(request, str(loi))
    else:
        messages.success(request, "Đã xác nhận báo giá với khách — thợ được báo bắt đầu sửa.")
    return redirect("chi_tiet_don", ma_don=ma_don)
