"""Tác vụ nền của gói lõi (SPEC 12). Mọi tác vụ lũy đẳng: chạy lại không sinh sai lệch."""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.danh_muc.models import TRANG_THAI_DA_LAM_XONG, KhachHang
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.nhat_ky import ghi_nhat_ky

from .dao import ghi_doi_trang_thai
from .models import DonSuaChua
from .trang_thai import TrangThaiDon

log = logging.getLogger(__name__)


def _den_han_nhac(moc):
    """Đơn chờ xác nhận lịch mà lần nhắc cuối (hoặc lúc tiếp nhận nếu chưa nhắc) cách hiện tại ≥ N giờ."""
    return Q(trang_thai=TrangThaiDon.CHO_XAC_NHAN_LICH) & (
        Q(lan_nhac_cuoi__lte=moc) | Q(lan_nhac_cuoi__isnull=True, ngay_tiep_nhan__lte=moc)
    )


def nhac_xac_nhan_lich(bay_gio=None) -> dict[str, int]:
    """BR08 — chạy mỗi giờ: còn lượt → tăng số lần nhắc, tạo việc “Gọi lại khách” (T4); hết lượt → hủy (T5)."""
    bay_gio = bay_gio or timezone.now()
    moc = bay_gio - timedelta(hours=cau_hinh("NHAC_XAC_NHAN_SAU_GIO"))
    ket_qua = {"da_nhac": 0, "da_huy": 0}
    for pk in DonSuaChua.objects.filter(_den_han_nhac(moc)).values_list("pk", flat=True):
        with transaction.atomic():
            # Khóa dòng rồi kiểm tra lại điều kiện → hai worker chạy trùng không nhắc hai lần.
            don = DonSuaChua.objects.select_for_update().filter(_den_han_nhac(moc), pk=pk).first()
            if don is None:
                continue
            con_luot = don.ghi_nhan_nhac_xac_nhan(bay_gio)
            ghi_nhat_ky(
                None, "NHAC_XAC_NHAN", don, du_lieu_sau={"so_lan": don.so_lan_nhac_xac_nhan, "tu_dong": True}
            )
            ghi_doi_trang_thai(None, don, "" if con_luot else don.ly_do_huy)
            ket_qua["da_nhac" if con_luot else "da_huy"] += 1
    if any(ket_qua.values()):
        log.info("BR08 nhắc xác nhận lịch: %s", ket_qua)
    return ket_qua


def cap_nhat_khach_vip(bay_gio=None) -> dict[str, int]:
    """BR07 — hằng ngày 01:00: khách có ≥ VIP_SO_DON_TOI_THIEU đơn hoàn thành trong 365 ngày, hoặc VIP thủ công
    (giám đốc giới thiệu) → VIP; hết điều kiện → THUONG. Lũy đẳng; mỗi thay đổi ghi nhật ký."""
    bay_gio = bay_gio or timezone.now()
    nguong = cau_hinh("VIP_SO_DON_TOI_THIEU")
    qs = KhachHang.objects.annotate(
        so_don=Count(
            "ds_don",
            filter=Q(
                ds_don__trang_thai__in=TRANG_THAI_DA_LAM_XONG,
                # thời điểm hoàn thành = lúc ghi nhận tiền thu (A-85); ThanhToan ở tầng trên — chỉ dùng tên quan hệ
                ds_don__ds_thanh_toan__thoi_diem_thu__gte=bay_gio - timedelta(days=365),
            ),
            distinct=True,
        )
    )
    ket_qua = {"len_vip": 0, "ve_thuong": 0}
    with transaction.atomic():
        for kh in qs.filter(Q(vip_thu_cong=True) | Q(so_don__gte=nguong)).exclude(
            loai_khach=KhachHang.LoaiKhach.VIP
        ):
            _doi_loai_khach(kh, KhachHang.LoaiKhach.VIP)
            ket_qua["len_vip"] += 1
        for kh in qs.filter(vip_thu_cong=False, so_don__lt=nguong, loai_khach=KhachHang.LoaiKhach.VIP):
            _doi_loai_khach(kh, KhachHang.LoaiKhach.THUONG)
            ket_qua["ve_thuong"] += 1
    return ket_qua


def _doi_loai_khach(kh, loai: str) -> None:
    truoc = kh.loai_khach
    kh.loai_khach = loai
    kh.save(update_fields=["loai_khach", "cap_nhat_luc"])
    ghi_nhat_ky(
        None, "CAP_NHAT_VIP", kh, {"loai_khach": truoc}, {"loai_khach": loai, "so_don_365_ngay": kh.so_don}
    )
