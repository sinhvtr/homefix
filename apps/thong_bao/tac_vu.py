"""Tác vụ nền gửi thông báo qua kênh ngoài (chạy trong worker django-q2)."""

import logging
from datetime import timedelta

from django.utils import timezone

from .adapters import cac_kenh_theo_thu_tu
from .models import ThongBao

log = logging.getLogger(__name__)


def gui_qua_kenh(thong_bao_id: int) -> str | None:
    """Thử kênh ưu tiên, thất bại thì kênh còn lại; ghi kết quả vào log. Trả tên kênh đã gửi được (hoặc None)."""
    tb = ThongBao.objects.select_related("nguoi_nhan").filter(pk=thong_bao_id).first()
    if tb is None:
        return None
    for kenh in cac_kenh_theo_thu_tu(tb.nguoi_nhan):
        try:
            if kenh.gui(tb.nguoi_nhan, tb.tieu_de, tb.noi_dung, tb.duong_dan):
                log.info("Thông báo %s gửi qua %s", tb.pk, kenh.ten)
                return kenh.ten
        except Exception:  # một kênh hỏng không được làm hỏng kênh còn lại
            log.exception("Kênh %s lỗi khi gửi thông báo %s", kenh.ten, tb.pk)
    log.info("Thông báo %s chỉ có trong ứng dụng (không kênh ngoài nào gửi được)", tb.pk)
    return None


def don_dep_thong_bao(bay_gio=None) -> int:
    """Hằng tuần: xóa thông báo đã đọc quá 90 ngày (SPEC 12)."""
    moc = (bay_gio or timezone.now()) - timedelta(days=90)
    so, _ = ThongBao.objects.filter(da_doc=True, tao_luc__lt=moc).delete()
    return so
