"""Mật khẩu tạm cho nhân viên văn phòng và mã PIN 6 số cho thợ (UC01, A-10)."""

import re
import secrets

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import VaiTro

_PIN = re.compile(r"\d{6}")
_TANG = "0123456789012345"
_GIAM = _TANG[::-1]


def kiem_tra_pin(pin: str) -> None:
    if not _PIN.fullmatch(pin or ""):
        raise ValidationError("Mã PIN phải gồm đúng 6 chữ số.", code="pin_sai_dang")
    if len(set(pin)) == 1 or pin in _TANG or pin in _GIAM:
        raise ValidationError("Mã PIN quá dễ đoán (6 số giống nhau hoặc liên tiếp).", code="pin_de_doan")


def kiem_tra_mat_khau_moi(mat_khau: str, nguoi_dung) -> None:
    """Thợ dùng PIN 6 số; các vai trò khác dùng bộ kiểm tra mật khẩu của Django."""
    if nguoi_dung.vai_tro == VaiTro.THO:
        kiem_tra_pin(mat_khau)
    else:
        validate_password(mat_khau, nguoi_dung)


def sinh_pin() -> str:
    while True:
        pin = f"{secrets.randbelow(1_000_000):06d}"
        try:
            kiem_tra_pin(pin)
        except ValidationError:
            continue
        return pin


def sinh_mat_khau_tam() -> str:
    return secrets.token_urlsafe(9)


def sinh_bi_mat(vai_tro: str) -> str:
    return sinh_pin() if vai_tro == VaiTro.THO else sinh_mat_khau_tam()
