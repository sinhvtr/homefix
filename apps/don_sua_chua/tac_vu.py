"""Tác vụ nền của gói lõi (SPEC 12). Mọi tác vụ lũy đẳng: chạy lại không sinh sai lệch."""

import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

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
