"""Chuẩn hóa số điện thoại Việt Nam về dạng 0xxxxxxxxx (SPEC 5)."""

import re

from django.core.exceptions import ValidationError

_KY_TU_PHAN_CACH = re.compile(r"[\s.\-()]")
_DANG_CHUAN = re.compile(r"0\d{9}")


def chuan_hoa_sdt(gia_tri: str | None) -> str:
    so = _KY_TU_PHAN_CACH.sub("", gia_tri or "")
    if so.startswith("+84"):
        so = "0" + so[3:]
    elif so.startswith("0084"):
        so = "0" + so[4:]
    elif so.startswith("84") and len(so) == 11:
        so = "0" + so[2:]
    if not _DANG_CHUAN.fullmatch(so):
        raise ValidationError(
            "Số điện thoại không hợp lệ: cần 10 chữ số, bắt đầu bằng 0 hoặc +84.",
            code="sdt_khong_hop_le",
        )
    return so
