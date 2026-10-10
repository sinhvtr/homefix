"""UC04 — cử thợ (gd_phan_cong.html), UC05 — lưới lịch thợ theo ngày. View chỉ gọi DAO."""

from datetime import datetime

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import redirect, render
from django.utils import timezone

from apps.don_sua_chua.dao import GHI_DON, XEM_BANG_DON, DonSuaChuaDAO
from apps.don_sua_chua.trang_thai import TrangThaiDon
from apps.he_thong.cau_hinh import cau_hinh
from apps.tai_khoan.phan_quyen import co_vai_tro, yeu_cau_vai_tro

from .dao import DANG_BAN, PhanCongDAO, ThoDAO
from .models import LichHen, PhanCong
from .views import _lay_don

T = TrangThaiDon


def _thong_diep_loi(loi) -> str:
    return " ".join(getattr(loi, "messages", [str(loi)]))


@yeu_cau_vai_tro(*XEM_BANG_DON)
def cu_tho(request, ma_don):
    """Bảng gợi ý bên trái, thông tin đơn và đề nghị bên phải. Giám đốc xem chỉ đọc."""
    don = _lay_don(request, ma_don)
    duoc_ghi = co_vai_tro(request.user, *GHI_DON)
    if request.method == "POST":
        if not duoc_ghi:
            raise PermissionDenied
        _xu_ly_hanh_dong(request, don)
        return redirect("cu_tho", ma_don=ma_don)

    lich = don.lich_hieu_luc
    goi_y = ThoDAO.goi_y_tho(don, lich) if don.trang_thai == T.CHO_CU_THO and lich else []
    return render(
        request,
        "dieu_phoi/gd_phan_cong.html",
        {
            "don": don,
            "lich": lich,
            "phu_hop": [g for g in goi_y if g.phu_hop],
            "khong_phu_hop": [g for g in goi_y if not g.phu_hop],
            "ds_phan_cong": PhanCong.objects.filter(don=don).select_related("tho", "nguoi_giao"),
            "duoc_ghi": duoc_ghi,
            "ly_do_tu_choi": PhanCong.LyDoTuChoi,
        },
    )


def _xu_ly_hanh_dong(request, don) -> None:
    hanh_dong = request.POST.get("hanh_dong")
    nguoi = request.user
    try:
        if hanh_dong == "gui":
            ds = [int(x) for x in request.POST.getlist("tho") if x.isdigit()]
            if not ds:
                raise ValidationError("Chọn ít nhất một thợ.")
            da_gui = PhanCongDAO.gui_de_nghi(nguoi, don, ds)
            if da_gui:
                messages.success(
                    request,
                    f"Đã gửi đề nghị cho {len(da_gui)} thợ. Hạn trả lời {cau_hinh('THOI_HAN_PHAN_HOI_PHUT')} phút.",
                )
            if len(da_gui) < len(ds):
                messages.warning(
                    request, f"{len(ds) - len(da_gui)} thợ không gửi được (không còn phù hợp hoặc đang chờ)."
                )
        elif hanh_dong == "dien_thoai":  # luồng 3a
            tho_id = request.POST.get("tho_dien_thoai", "")
            pc = PhanCong(
                don=don,
                tho_id=int(tho_id) if tho_id.isdigit() else 0,
                nguoi_giao=nguoi,
                giao_qua_dien_thoai=True,
                ghi_chu=request.POST.get("ghi_chu", "").strip(),
            )
            if PhanCongDAO.giao_viec(pc):
                messages.success(request, "Đã ghi nhận thợ đồng ý qua điện thoại — đơn chuyển “Đã có thợ”.")
            else:
                messages.error(request, "Không giao được: thợ không phù hợp hoặc đơn không còn chờ cử thợ.")
        elif hanh_dong == "thu_hoi":
            PhanCongDAO.thu_hoi(nguoi, int(request.POST["phan_cong"]))
            messages.info(request, "Đã thu hồi đề nghị.")
        elif hanh_dong == "doi_lich":  # luồng 2a
            DonSuaChuaDAO.de_nghi_doi_lich(nguoi, don)
            messages.info(request, "Đơn chuyển về “Chờ khách xác nhận lịch”. Hãy gọi khách hẹn giờ khác.")
        elif hanh_dong == "chua_cu_duoc":  # luồng 2a
            DonSuaChuaDAO.danh_dau_chua_cu_duoc(nguoi, don, request.POST.get("ly_do", ""))
            messages.warning(request, "Đã đánh dấu “Chưa cử được thợ”.")
        elif hanh_dong == "rut_viec":
            PhanCongDAO.tra_viec(nguoi, don, request.POST.get("ly_do", ""))
            messages.info(request, "Đã rút việc — đơn quay lại “Chờ cử thợ”.")
        else:
            messages.error(request, "Thao tác không hợp lệ.")
    except (ValidationError, ValueError, KeyError) as loi:
        messages.error(request, _thong_diep_loi(loi))
    except PhanCong.DoesNotExist:
        messages.error(request, "Không có đề nghị này.")


@yeu_cau_vai_tro(*XEM_BANG_DON)
def lich_tho(request):
    """UC05: lưới khung giờ × thợ trong một ngày để tổng đài nhìn tổng thể."""
    try:
        ngay = datetime.strptime(request.GET.get("ngay", ""), "%Y-%m-%d").date()
    except ValueError:
        ngay = timezone.localdate()
    khung = cau_hinh("KHUNG_GIO")
    ds_tho = list(ThoDAO.lay_danh_sach(request.user).filter(nguoi_dung__is_active=True))
    lich = (
        LichHen.objects.filter(trang_thai="HIEU_LUC", bat_dau__date=ngay, don__tho__isnull=False)
        .filter(don__trang_thai__in=(*DANG_BAN, T.HOAN_THANH))
        .values("don__tho_id", "don__ma_don", "don__trang_thai", "bat_dau", "ket_thuc")
    )
    theo_tho: dict[int, list] = {}
    for dong in lich:
        theo_tho.setdefault(dong["don__tho_id"], []).append(dong)

    def o_trong(tho_id, kg):
        bd, kt = kg.split("-")
        dau = timezone.make_aware(datetime.combine(ngay, datetime.strptime(bd, "%H:%M").time()))
        cuoi = timezone.make_aware(datetime.combine(ngay, datetime.strptime(kt, "%H:%M").time()))
        return [d for d in theo_tho.get(tho_id, []) if d["bat_dau"] < cuoi and d["ket_thuc"] > dau]

    hang = []
    for tho in ds_tho:
        nghi = bool(
            tho.nghi_den and tho.nghi_den > timezone.make_aware(datetime.combine(ngay, datetime.min.time()))
        )
        hang.append({"tho": tho, "nghi": nghi, "o": [o_trong(tho.pk, kg) for kg in khung]})
    return render(request, "dieu_phoi/lich_tho.html", {"ngay": ngay, "khung": khung, "hang": hang})
