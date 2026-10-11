"""Màn hình kế toán (UC12): tổng hợp theo thợ, phiếu đối soát, xuất MISA. View chỉ gọi DAO.
SPEC 3.1 — Phiếu đối soát: KT CRU; QT, GĐ chỉ xem; thợ xem phiếu của mình ở /tho/doi-soat/."""

from datetime import date

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.danh_muc.models import Tho
from apps.tai_khoan.phan_quyen import co_vai_tro, yeu_cau_vai_tro

from .dao import GHI_DOI_SOAT, XEM_DOI_SOAT, DoiSoatDAO
from .models import PhieuDoiSoat
from .xuat_misa import phieu_trong_ky, xuat_csv, xuat_xlsx


def _ngay(chuoi) -> date | None:
    try:
        return date.fromisoformat(chuoi) if chuoi else None
    except ValueError as loi:
        raise ValidationError(f"Ngày “{chuoi}” không hợp lệ.") from loi


def _so(chuoi) -> int:
    return int(chuoi) if (chuoi or "").isdigit() else 0


def _bao_loi(request, loi) -> None:
    messages.error(request, " ".join(getattr(loi, "messages", [str(loi)])))


@yeu_cau_vai_tro(*XEM_DOI_SOAT)
def tong_hop(request):
    hom_nay = timezone.localdate()
    return render(
        request,
        "tai_chinh/doi_soat.html",
        {
            "bang": DoiSoatDAO.tong_hop_theo_tho(request.user),
            "ds_phieu": DoiSoatDAO.danh_sach_phieu(request.user),
            "duoc_ghi": co_vai_tro(request.user, *GHI_DOI_SOAT),
            "xuat_tu": hom_nay.replace(day=1),
            "xuat_den": hom_nay,
        },
    )


@require_POST
@yeu_cau_vai_tro(*GHI_DOI_SOAT)
def lap_phieu(request):
    tho = Tho.objects.filter(pk=_so(request.POST.get("tho"))).first()
    if tho is None:
        messages.error(request, "Chọn thợ để lập phiếu.")
        return redirect("tai_chinh:tong_hop")
    try:
        phieu = DoiSoatDAO.lap_phieu(
            request.user, tho, _ngay(request.POST.get("tu_ngay")), _ngay(request.POST.get("den_ngay"))
        )
    except ValidationError as loi:
        _bao_loi(request, loi)
        return redirect("tai_chinh:tong_hop")
    messages.success(
        request, f"Đã lập phiếu nháp {phieu.ma} — bỏ chọn dòng chưa đối chiếu được rồi bấm Chốt."
    )
    return redirect("tai_chinh:phieu", ma=phieu.ma)


@yeu_cau_vai_tro(*XEM_DOI_SOAT)
def phieu(request, ma):
    try:
        p = DoiSoatDAO.lay_phieu(request.user, ma)
    except PhieuDoiSoat.DoesNotExist as loi:
        raise Http404 from loi
    if request.method == "POST":
        if not co_vai_tro(request.user, *GHI_DOI_SOAT):
            raise PermissionDenied
        hanh_dong = request.POST.get("hanh_dong")
        try:
            if hanh_dong == "cap_nhat":
                DoiSoatDAO.cap_nhat_dong(request.user, p, request.POST.getlist("thanh_toan"))
                messages.success(request, "Đã cập nhật các dòng của phiếu.")
            elif hanh_dong == "chot":  # chốt theo đúng các dòng đang tích trên màn hình
                p = DoiSoatDAO.cap_nhat_dong(request.user, p, request.POST.getlist("thanh_toan"))
                DoiSoatDAO.chot(request.user, p)
                messages.success(request, f"Đã chốt phiếu {p.ma}. Các dòng đã khóa.")
            elif hanh_dong == "da_nop":
                DoiSoatDAO.xac_nhan_da_nop(request.user, p)
                messages.success(request, f"Đã xác nhận thợ nộp tiền phiếu {p.ma}.")
            elif hanh_dong == "mo_lai":
                DoiSoatDAO.mo_lai(request.user, p, request.POST.get("ly_do", ""))
                messages.warning(request, f"Đã mở lại phiếu {p.ma} về nháp.")
            elif hanh_dong == "huy":
                DoiSoatDAO.huy_nhap(request.user, p)
                messages.info(request, f"Đã bỏ phiếu nháp {p.ma}.")
                return redirect("tai_chinh:tong_hop")
            else:
                raise ValidationError("Thao tác không hợp lệ.")
        except ValidationError as loi:
            _bao_loi(request, loi)
        return redirect("tai_chinh:phieu", ma=ma)
    return render(
        request,
        "tai_chinh/phieu.html",
        {
            "phieu": p,
            "ds_dong": DoiSoatDAO.dong_cua_phieu(p),
            "ds_them": DoiSoatDAO.dong_co_the_them(p),
            "duoc_ghi": co_vai_tro(request.user, *GHI_DOI_SOAT),
        },
    )


@yeu_cau_vai_tro(*XEM_DOI_SOAT)
def xuat(request):
    """Xuất MISA: ?dinh_dang=csv|xlsx&tu=YYYY-MM-DD&den=YYYY-MM-DD (mặc định: đầu tháng đến hôm nay)."""
    hom_nay = timezone.localdate()
    try:
        tu = _ngay(request.GET.get("tu")) or hom_nay.replace(day=1)
        den = _ngay(request.GET.get("den")) or hom_nay
    except ValidationError as loi:
        _bao_loi(request, loi)
        return redirect("tai_chinh:tong_hop")
    ds = phieu_trong_ky(request.user, tu, den)
    ten = f"doi_soat_{tu:%Y%m%d}_{den:%Y%m%d}"
    if request.GET.get("dinh_dang") == "csv":
        phan_hoi = HttpResponse(xuat_csv(ds), content_type="text/csv; charset=utf-8")
        phan_hoi["Content-Disposition"] = f'attachment; filename="{ten}.csv"'
    else:
        phan_hoi = HttpResponse(
            xuat_xlsx(ds), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        phan_hoi["Content-Disposition"] = f'attachment; filename="{ten}.xlsx"'
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi
