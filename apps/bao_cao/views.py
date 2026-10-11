"""UC14 — /bao-cao/ (bộ chọn kỳ, thẻ số, biểu đồ Chart.js tự host) và /bao-cao/xuat/ (XLSX mọi bảng)."""

from datetime import date

from django.http import HttpResponse
from django.shortcuts import render

from apps.tai_khoan.phan_quyen import yeu_cau_vai_tro

from .dao import KY, MOC_CONG_NO, MOC_KHONG_CU_DUOC, XEM_BAO_CAO, BaoCao, BaoCaoDAO, chon_ky
from .xuat import xuat_xlsx


def _ngay(chuoi) -> date | None:
    try:
        return date.fromisoformat(chuoi) if chuoi else None
    except ValueError:
        return None


def phan_tram(ty_le) -> str:
    return "—" if ty_le is None else f"{ty_le * 100:.1f}%".replace(".", ",")


def tien(so) -> str:
    return f"{int(so):,} đ".replace(",", ".")


def phut(so) -> str:
    if so is None:
        return "—"
    return f"{so:.0f} phút" if so < 120 else f"{so / 60:.1f} giờ".replace(".", ",")


def the_chi_so(bc: BaoCao) -> list[tuple[str, str, str, bool]]:
    """(nhãn, giá trị, dòng phụ, vượt mốc hiện trạng?) — thẻ số đầu trang."""
    the = [
        ("Đơn tiếp nhận", str(bc.so_tiep_nhan), "", False),
        ("Đơn hoàn thành", str(bc.so_hoan_thanh), "", False),
        ("Doanh thu", tien(bc.doanh_thu), "Σ tổng phải thu của đơn hoàn thành", False),
        (
            "Công nợ thợ hiện tại",
            tien(bc.cong_no_hien_tai),
            f"Mốc hiện trạng {MOC_CONG_NO[0] // 1_000_000}–{MOC_CONG_NO[1] // 1_000_000} triệu",
            bc.cong_no_hien_tai >= MOC_CONG_NO[0],
        ),
    ]
    if bc.xem_van_hanh:
        k, c, ll = bc.khong_cu_duoc, bc.co_tho_trong_30_phut, bc.lam_lai
        the += [
            ("Đơn hủy", str(bc.so_huy), "Đơn tiếp nhận trong kỳ đã hủy", False),
            (
                "Tỷ lệ không cử được thợ",
                phan_tram(k.ty_le),
                f"{k.tu_so}/{k.mau_so} đơn · mốc hiện trạng {MOC_KHONG_CU_DUOC:.0%}",
                (k.ty_le or 0) >= MOC_KHONG_CU_DUOC,
            ),
            (
                "Trung vị tiếp nhận → có thợ",
                phut(bc.trung_vi_phut_co_tho),
                f"{phan_tram(c.ty_le)} có thợ trong 30 phút",
                False,
            ),
            (
                "Tỷ lệ làm lại",
                phan_tram(ll.ty_le),
                f"{ll.tu_so} đơn bảo hành / {ll.mau_so} đơn hoàn thành",
                False,
            ),
        ]
    return the


def _ky(request):
    g = request.GET
    return chon_ky(g.get("ky"), _ngay(g.get("tu")), _ngay(g.get("den")))


@yeu_cau_vai_tro(*XEM_BAO_CAO)
def bao_cao(request):
    bc = BaoCaoDAO.lap(request.user, _ky(request))
    bieu_do = {
        "ngay": [f"{n:%d/%m}" for n, _, _ in bc.don_theo_ngay],
        "tiep_nhan": [a for _, a, _ in bc.don_theo_ngay],
        "hoan_thanh": [b for _, _, b in bc.don_theo_ngay],
        "doanh_thu": [t for _, t in bc.doanh_thu_theo_ngay],
    }
    for d in bc.lam_lai_theo_tho:
        d.ty_le_hien_thi = phan_tram(d.ty_le)
    for d in bc.de_nghi_theo_tho:
        d["ty_le_nhan_hien_thi"] = phan_tram(d["ty_le_nhan"])
    return render(
        request,
        "bao_cao/bao_cao.html",
        {
            "bc": bc,
            "ds_ky": KY.items(),
            "the": the_chi_so(bc),
            "bang_doanh_thu": [
                ("Doanh thu theo dịch vụ", "Dịch vụ", bc.doanh_thu_theo_dich_vu),
                ("Doanh thu theo thợ", "Thợ", bc.doanh_thu_theo_tho),
                ("Doanh thu theo khu vực", "Khu vực", bc.doanh_thu_theo_khu_vuc),
            ],
            "bieu_do": bieu_do,
            "chuoi_ky": request.GET.urlencode(),
        },
    )


@yeu_cau_vai_tro(*XEM_BAO_CAO)
def xuat(request):
    bc = BaoCaoDAO.lap(request.user, _ky(request))
    phan_hoi = HttpResponse(
        xuat_xlsx(bc), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    phan_hoi["Content-Disposition"] = (
        f'attachment; filename="bao_cao_{bc.ky.tu:%Y%m%d}_{bc.ky.den:%Y%m%d}.xlsx"'
    )
    phan_hoi["Cache-Control"] = "private, no-store"
    return phan_hoi
