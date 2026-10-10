"""Tác vụ nền điều phối (SPEC 12)."""

from .dao import PhanCongDAO


def kiem_tra_qua_han_phan_cong(bay_gio=None) -> dict[str, int]:
    """BR02 — mỗi phút."""
    return PhanCongDAO.kiem_tra_qua_han(bay_gio)
