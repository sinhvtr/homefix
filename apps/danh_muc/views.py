"""Màn hình danh mục (UC13). View chỉ gọi DAO; quyền theo SPEC 3.1 kiểm ở cả view lẫn DAO."""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.he_thong.bieu_mau import gan_loi_vao_form
from apps.tai_khoan.phan_quyen import (
    CHI_QUAN_TRI,
    GHI_KHACH_HANG,
    MOI_VAI_TRO,
    VAN_PHONG,
    co_vai_tro,
    yeu_cau_vai_tro,
)

from . import nhap_excel
from .dao import DiaChiDAO, DichVuDAO, KhachHangDAO, KhuVucDAO, ThietBiDAO, ThoDAO
from .forms import DiaChiForm, DichVuForm, KhachHangForm, KhuVucForm, TepExcelForm, ThietBiForm, ThoForm
from .models import DiaChi, DichVu, KhachHang, KhuVuc, LoaiThietBi, ThietBi, Tho

LOAI_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _bieu_mau(request, form, ham_luu, tieu_de, tiep, thong_bao, quay_lai, ghi_chu=""):
    """Form chuẩn: hợp lệ → gọi DAO; lỗi DAO gắn vào form; thành công → chuyển trang."""
    if request.method == "POST" and form.is_valid():
        try:
            ket_qua = ham_luu(form.cleaned_data)
        except ValidationError as loi:
            gan_loi_vao_form(form, loi)
        else:
            messages.success(request, thong_bao)
            return redirect(tiep(ket_qua) if callable(tiep) else tiep)
    return render(
        request,
        "chung/bieu_mau.html",
        {"form": form, "tieu_de": tieu_de, "quay_lai": quay_lai, "ghi_chu": ghi_chu},
    )


def _xoa(request, ham_xoa, tiep, thong_bao):
    try:
        ham_xoa()
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
    else:
        messages.success(request, thong_bao)
    return redirect(tiep)


def _tai_xlsx(noi_dung: bytes, ten_tep: str) -> HttpResponse:
    phan_hoi = HttpResponse(noi_dung, content_type=LOAI_XLSX)
    phan_hoi["Content-Disposition"] = f'attachment; filename="{ten_tep}"'
    return phan_hoi


def _nhap(request, ham_nhap, tieu_de, url_mau, url_danh_sach):
    form = TepExcelForm(request.POST or None, request.FILES or None)
    ket_qua = None
    if request.method == "POST" and form.is_valid():
        ket_qua = ham_nhap(request.user, form.cleaned_data["tep"])
        if ket_qua.thanh_cong:
            messages.success(request, f"Đã nhập: thêm {ket_qua.so_tao}, cập nhật {ket_qua.so_cap_nhat}.")
            if not ket_qua.ds_pin:
                return redirect(url_danh_sach)
    return render(
        request,
        "danh_muc/nhap_excel.html",
        {
            "form": form,
            "ket_qua": ket_qua,
            "tieu_de": tieu_de,
            "url_mau": url_mau,
            "url_danh_sach": url_danh_sach,
        },
    )


# ================================================================ Khu vực


@yeu_cau_vai_tro(*VAN_PHONG)
def khu_vuc_danh_sach(request):
    return render(
        request,
        "danh_muc/khu_vuc_danh_sach.html",
        {"ds": KhuVucDAO.lay_danh_sach(request.user), "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI)},
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def khu_vuc_moi(request):
    return _bieu_mau(
        request,
        KhuVucForm(request.POST or None),
        lambda d: KhuVucDAO.tao(request.user, d),
        "Thêm khu vực",
        "danh_muc:khu_vuc_danh_sach",
        "Đã thêm khu vực.",
        reverse("danh_muc:khu_vuc_danh_sach"),
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def khu_vuc_sua(request, pk):
    kv = get_object_or_404(KhuVuc, pk=pk)
    return _bieu_mau(
        request,
        KhuVucForm(request.POST or None, instance=kv),
        lambda d: KhuVucDAO.sua(request.user, kv, d),
        f"Sửa khu vực {kv.ten}",
        "danh_muc:khu_vuc_danh_sach",
        "Đã lưu khu vực.",
        reverse("danh_muc:khu_vuc_danh_sach"),
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def khu_vuc_xoa(request, pk):
    kv = get_object_or_404(KhuVuc, pk=pk)
    return _xoa(
        request, lambda: KhuVucDAO.xoa(request.user, kv), "danh_muc:khu_vuc_danh_sach", "Đã xóa khu vực."
    )


# ================================================================ Dịch vụ, bảng giá


@yeu_cau_vai_tro(*MOI_VAI_TRO)
def dich_vu_danh_sach(request):
    tu_khoa = request.GET.get("q", "").strip()
    loai = request.GET.get("loai", "")
    return render(
        request,
        "danh_muc/dich_vu_danh_sach.html",
        {
            "ds": DichVuDAO.lay_danh_sach(request.user, tu_khoa, loai),
            "q": tu_khoa,
            "loai": loai,
            "ds_loai": LoaiThietBi.choices,
            "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI),
        },
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dich_vu_moi(request):
    return _bieu_mau(
        request,
        DichVuForm(request.POST or None),
        lambda d: DichVuDAO.tao(request.user, d),
        "Thêm dịch vụ",
        "danh_muc:dich_vu_danh_sach",
        "Đã thêm dịch vụ.",
        reverse("danh_muc:dich_vu_danh_sach"),
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dich_vu_sua(request, pk):
    dv = get_object_or_404(DichVu, pk=pk)
    return _bieu_mau(
        request,
        DichVuForm(request.POST or None, instance=dv),
        lambda d: DichVuDAO.sua(request.user, dv, d),
        f"Sửa dịch vụ {dv.ma}",
        "danh_muc:dich_vu_danh_sach",
        "Đã lưu dịch vụ.",
        reverse("danh_muc:dich_vu_danh_sach"),
        ghi_chu="Mọi thay đổi đơn giá được ghi nhật ký (người sửa, giá trước/sau).",
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dich_vu_xoa(request, pk):
    dv = get_object_or_404(DichVu, pk=pk)
    return _xoa(
        request, lambda: DichVuDAO.xoa(request.user, dv), "danh_muc:dich_vu_danh_sach", "Đã xóa dịch vụ."
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dich_vu_mau(request):
    return _tai_xlsx(nhap_excel.tao_mau_bang_gia(), "mau_bang_gia.xlsx")


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dich_vu_nhap(request):
    return _nhap(
        request,
        nhap_excel.nhap_bang_gia,
        "Nhập bảng giá từ Excel",
        reverse("danh_muc:dich_vu_mau"),
        reverse("danh_muc:dich_vu_danh_sach"),
    )


# ================================================================ Thợ


def _hien_pin(request, ho_ten, sdt, pin):
    messages.warning(
        request,
        f"PIN của {ho_ten} ({sdt}): {pin} — chỉ hiện một lần, hãy báo trực tiếp cho thợ. "
        "Thợ phải đổi PIN ở lần đăng nhập đầu.",
    )


@yeu_cau_vai_tro(*VAN_PHONG)
def tho_danh_sach(request):
    tu_khoa = request.GET.get("q", "").strip()
    return render(
        request,
        "danh_muc/tho_danh_sach.html",
        {
            "ds": ThoDAO.lay_danh_sach(request.user, tu_khoa),
            "q": tu_khoa,
            "bay_gio": timezone.now(),
            "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI),
        },
    )


@yeu_cau_vai_tro(*VAN_PHONG)
def tho_chi_tiet(request, pk):
    get_object_or_404(Tho, pk=pk)
    return render(
        request,
        "danh_muc/tho_chi_tiet.html",
        {"tho": ThoDAO.lay_chi_tiet(request.user, pk), "duoc_sua": co_vai_tro(request.user, *CHI_QUAN_TRI)},
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_moi(request):
    def luu(du_lieu):
        tho, pin = ThoDAO.tao(request.user, du_lieu)
        _hien_pin(request, tho.ho_ten, tho.so_dien_thoai, pin)
        return tho

    return _bieu_mau(
        request,
        ThoForm(request.POST or None),
        luu,
        "Thêm thợ",
        lambda tho: reverse("danh_muc:tho_chi_tiet", args=[tho.pk]),
        "Đã thêm thợ.",
        reverse("danh_muc:tho_danh_sach"),
        ghi_chu="Tên đăng nhập của thợ là số điện thoại. Hệ thống tự cấp PIN 6 số.",
    )


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_sua(request, pk):
    tho = get_object_or_404(Tho, pk=pk)
    return _bieu_mau(
        request,
        ThoForm(request.POST or None, instance=tho),
        lambda d: ThoDAO.sua(request.user, tho, d),
        f"Sửa thợ {tho.ho_ten}",
        reverse("danh_muc:tho_chi_tiet", args=[tho.pk]),
        "Đã lưu hồ sơ thợ.",
        reverse("danh_muc:tho_chi_tiet", args=[tho.pk]),
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_cap_pin(request, pk):
    tho = get_object_or_404(Tho, pk=pk)
    _hien_pin(request, tho.ho_ten, tho.so_dien_thoai, ThoDAO.cap_lai_pin(request.user, tho))
    return redirect("danh_muc:tho_chi_tiet", pk=tho.pk)


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_khoa(request, pk):
    tho = get_object_or_404(Tho.objects.select_related("nguoi_dung"), pk=pk)
    khoa = tho.nguoi_dung.is_active
    ThoDAO.dat_khoa(request.user, tho, khoa)
    messages.success(request, f"Đã {'khóa' if khoa else 'mở khóa'} tài khoản thợ {tho.ho_ten}.")
    return redirect("danh_muc:tho_chi_tiet", pk=tho.pk)


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_mau(request):
    return _tai_xlsx(nhap_excel.tao_mau_tho(), "mau_tho.xlsx")


@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def tho_nhap(request):
    return _nhap(
        request,
        nhap_excel.nhap_tho,
        "Nhập thợ từ Excel",
        reverse("danh_muc:tho_mau"),
        reverse("danh_muc:tho_danh_sach"),
    )


# ================================================================ Khách hàng, địa chỉ, thiết bị


@yeu_cau_vai_tro(*VAN_PHONG)
def khach_hang_danh_sach(request):
    tu_khoa = request.GET.get("q", "").strip()
    return render(
        request,
        "danh_muc/khach_hang_danh_sach.html",
        {
            "ds": KhachHangDAO.lay_danh_sach(request.user, tu_khoa)[:200],
            "q": tu_khoa,
            "duoc_ghi": co_vai_tro(request.user, *GHI_KHACH_HANG),
        },
    )


@yeu_cau_vai_tro(*VAN_PHONG)
def khach_hang_chi_tiet(request, pk):
    get_object_or_404(KhachHang, pk=pk)
    return render(
        request,
        "danh_muc/khach_hang_chi_tiet.html",
        {
            "kh": KhachHangDAO.lay_chi_tiet(request.user, pk),
            "duoc_ghi": co_vai_tro(request.user, *GHI_KHACH_HANG),
            "duoc_xoa": co_vai_tro(request.user, *CHI_QUAN_TRI),
        },
    )


def _url_khach(kh_id):
    return reverse("danh_muc:khach_hang_chi_tiet", args=[kh_id])


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def khach_hang_moi(request):
    return _bieu_mau(
        request,
        KhachHangForm(request.POST or None),
        lambda d: KhachHangDAO.tao(request.user, d),
        "Thêm khách hàng",
        lambda kh: _url_khach(kh.pk),
        "Đã thêm khách hàng.",
        reverse("danh_muc:khach_hang_danh_sach"),
    )


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def khach_hang_sua(request, pk):
    kh = get_object_or_404(KhachHang, pk=pk)
    return _bieu_mau(
        request,
        KhachHangForm(request.POST or None, instance=kh),
        lambda d: KhachHangDAO.sua(request.user, kh, d),
        f"Sửa khách hàng {kh}",
        _url_khach(kh.pk),
        "Đã lưu khách hàng.",
        _url_khach(kh.pk),
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def khach_hang_xoa(request, pk):
    kh = get_object_or_404(KhachHang, pk=pk)
    try:
        KhachHangDAO.xoa(request.user, kh)
    except ValidationError as loi:
        messages.error(request, " ".join(loi.messages))
        return redirect(_url_khach(kh.pk))
    messages.success(request, "Đã xóa khách hàng.")
    return redirect("danh_muc:khach_hang_danh_sach")


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def dia_chi_moi(request, pk):
    kh = get_object_or_404(KhachHang, pk=pk)
    return _bieu_mau(
        request,
        DiaChiForm(request.POST or None),
        lambda d: DiaChiDAO.tao(request.user, kh, d),
        f"Thêm địa chỉ cho {kh}",
        _url_khach(kh.pk),
        "Đã thêm địa chỉ.",
        _url_khach(kh.pk),
    )


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def dia_chi_sua(request, pk):
    dc = get_object_or_404(DiaChi, pk=pk)
    return _bieu_mau(
        request,
        DiaChiForm(request.POST or None, instance=dc),
        lambda d: DiaChiDAO.sua(request.user, dc, d),
        "Sửa địa chỉ",
        _url_khach(dc.khach_hang_id),
        "Đã lưu địa chỉ.",
        _url_khach(dc.khach_hang_id),
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def dia_chi_xoa(request, pk):
    dc = get_object_or_404(DiaChi, pk=pk)
    return _xoa(
        request, lambda: DiaChiDAO.xoa(request.user, dc), _url_khach(dc.khach_hang_id), "Đã xóa địa chỉ."
    )


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def thiet_bi_moi(request, pk):
    dc = get_object_or_404(DiaChi, pk=pk)
    return _bieu_mau(
        request,
        ThietBiForm(request.POST or None),
        lambda d: ThietBiDAO.tao(request.user, dc, d),
        f"Thêm thiết bị tại {dc.dia_chi_chi_tiet}",
        _url_khach(dc.khach_hang_id),
        "Đã thêm thiết bị.",
        _url_khach(dc.khach_hang_id),
    )


@yeu_cau_vai_tro(*GHI_KHACH_HANG)
def thiet_bi_sua(request, pk):
    tb = get_object_or_404(ThietBi.objects.select_related("dia_chi"), pk=pk)
    kh_id = tb.dia_chi.khach_hang_id
    return _bieu_mau(
        request,
        ThietBiForm(request.POST or None, instance=tb),
        lambda d: ThietBiDAO.sua(request.user, tb, d),
        "Sửa thiết bị",
        _url_khach(kh_id),
        "Đã lưu thiết bị.",
        _url_khach(kh_id),
    )


@require_POST
@yeu_cau_vai_tro(*CHI_QUAN_TRI)
def thiet_bi_xoa(request, pk):
    tb = get_object_or_404(ThietBi.objects.select_related("dia_chi"), pk=pk)
    kh_id = tb.dia_chi.khach_hang_id
    return _xoa(request, lambda: ThietBiDAO.xoa(request.user, tb), _url_khach(kh_id), "Đã xóa thiết bị.")
