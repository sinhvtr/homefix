"""Bộ lọc hiển thị dùng chung: tiền (1.250.000 đ), ẩn bớt số điện thoại (OI-05)."""

from django import template

register = template.Library()


@register.filter
def tien(gia_tri) -> str:
    if gia_tri is None or gia_tri == "":
        return ""
    return f"{int(gia_tri):,}".replace(",", ".") + " đ"


@register.filter
def an_sdt(so: str) -> str:
    """0901234123 → 090****123."""
    if not so or len(so) < 7:
        return so or ""
    return f"{so[:3]}****{so[-3:]}"
