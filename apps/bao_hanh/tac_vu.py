"""Tác vụ nền bảo hành (SPEC 12): dong_don_het_bao_hanh — hằng ngày 00:15, BR05 (T18). Lũy đẳng."""

import logging

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.don_sua_chua.dao import ghi_doi_trang_thai
from apps.don_sua_chua.models import DonSuaChua
from apps.don_sua_chua.trang_thai import TrangThaiDon

log = logging.getLogger(__name__)


def _het_han(hom_nay) -> Q:
    """Đơn HOAN_THANH có phiếu hết hạn trước hôm nay; đơn bảo hành con (không có phiếu riêng) theo phiếu đơn gốc."""
    return Q(trang_thai=TrangThaiDon.HOAN_THANH) & (
        Q(phieu_bao_hanh__ngay_het_han__lt=hom_nay)
        | Q(
            loai_don=DonSuaChua.LoaiDon.BAO_HANH,
            phieu_bao_hanh__isnull=True,
            don_goc__phieu_bao_hanh__ngay_het_han__lt=hom_nay,
        )
    )


def dong_don_het_bao_hanh(bay_gio=None) -> dict[str, int]:
    """BR05/T18: ngày hết hạn D vẫn còn hạn cả ngày D (giờ Việt Nam); lần chạy 00:15 ngày D+1 đóng đơn → DA_DONG.
    Đơn gốc đang bảo hành (DANG_BAO_HANH) chưa đóng — đóng ở lần chạy sau khi đơn con kết thúc (T17)."""
    hom_nay = timezone.localdate(bay_gio or timezone.now())
    da_dong = 0
    for pk in DonSuaChua.objects.filter(_het_han(hom_nay)).values_list("pk", flat=True):
        with transaction.atomic():
            don = DonSuaChua.objects.select_for_update(of=("self",)).filter(_het_han(hom_nay), pk=pk).first()
            if don is None:  # worker khác vừa đóng
                continue
            don.dong()
            ghi_doi_trang_thai(None, don, "Hết hạn bảo hành")
            da_dong += 1
    if da_dong:
        log.info("BR05 đóng %s đơn hết hạn bảo hành", da_dong)
    return {"da_dong": da_dong}
