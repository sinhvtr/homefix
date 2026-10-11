"""Ghi nhật ký thao tác (NFR06). Gọi trong DAO, bên trong transaction.atomic() của thao tác ghi."""

from contextvars import ContextVar

from django.db import models

from .models import NhatKyThaoTac

# IP của yêu cầu đang xử lý — DAO không nhận request nên middleware đặt sẵn ở đây (tác vụ nền: None)
_ip_yeu_cau: ContextVar[str | None] = ContextVar("ip_yeu_cau", default=None)


def ten_doi_tuong(doi_tuong) -> str:
    """'DonSuaChua:HF261010-007' — ưu tiên mã nghiệp vụ (ma_don, ma), không có thì dùng khóa chính."""
    if isinstance(doi_tuong, str):
        return doi_tuong
    if isinstance(doi_tuong, models.Model):
        ma = getattr(doi_tuong, "ma_don", None) or getattr(doi_tuong, "ma", None) or doi_tuong.pk
        return f"{type(doi_tuong).__name__}:{ma}"
    raise TypeError("doi_tuong phải là chuỗi hoặc đối tượng mô hình")


def lay_dia_chi_ip(request) -> str | None:
    """IP người dùng. Máy chủ chỉ nghe 127.0.0.1 sau tunnel nên tin X-Forwarded-For."""
    if request is None:
        return None
    chuoi = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if chuoi:
        return chuoi.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR") or None


class GhiIPNhatKyMiddleware:
    """Đặt IP người dùng cho mọi nhật ký ghi trong yêu cầu này (NFR06: truy vết ai, lúc nào, từ đâu)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        moc = _ip_yeu_cau.set(lay_dia_chi_ip(request))
        try:
            return self.get_response(request)
        finally:
            _ip_yeu_cau.reset(moc)


def ghi_nhat_ky(
    nguoi_dung,
    hanh_dong: str,
    doi_tuong,
    du_lieu_truoc: dict | None = None,
    du_lieu_sau: dict | None = None,
    dia_chi_ip: str | None = None,
) -> NhatKyThaoTac:
    if nguoi_dung is not None and not getattr(nguoi_dung, "is_authenticated", False):
        nguoi_dung = None
    return NhatKyThaoTac.objects.create(
        nguoi_dung=nguoi_dung,
        hanh_dong=hanh_dong,
        doi_tuong=ten_doi_tuong(doi_tuong),
        du_lieu_truoc=du_lieu_truoc,
        du_lieu_sau=du_lieu_sau,
        dia_chi_ip=dia_chi_ip or _ip_yeu_cau.get(),
    )
