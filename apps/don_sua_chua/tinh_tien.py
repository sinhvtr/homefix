"""Công thức tiền (SPEC 7.2) — hàm thuần, không truy cập CSDL. Tiền là số nguyên đồng; tính trung gian bằng Decimal.

tien_cong   = Σ thanh_tien (loai = CONG,     ben_chiu = KHACH)
tien_vat_tu = Σ thanh_tien (loai = VAT_TU,   ben_chiu = KHACH)
phi_khac    = Σ thanh_tien (loai = PHI_KHAC, ben_chiu = KHACH)
giam_vip    = 0 nếu khách không VIP
            = lam_tron_nghin(tien_cong × VIP_TY_LE_GIAM / 100)                  nếu phạm vi = TIEN_CONG
            = lam_tron_nghin((tien_cong + tien_vat_tu) × VIP_TY_LE_GIAM / 100)  nếu phạm vi = CONG_VA_VAT_TU
tong_tien   = tien_cong + tien_vat_tu + phi_khac − giam_vip
(đơn bảo hành: mọi dòng ben_chiu ≠ KHACH → tổng 0)
"""

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

TIEN_CONG = "TIEN_CONG"
CONG_VA_VAT_TU = "CONG_VA_VAT_TU"


@dataclass(frozen=True)
class DongTien:
    loai: str  # CONG | VAT_TU | PHI_KHAC
    thanh_tien: int
    ben_chiu: str = "KHACH"


@dataclass(frozen=True)
class KetQuaTinhTien:
    tien_cong: int
    tien_vat_tu: int
    phi_khac: int
    giam_vip: int
    tong_tien: int


def lam_tron_nghin(so: Decimal | int) -> int:
    """Làm tròn đến 1.000 đ gần nhất, nửa lên (A-16): 14.500 → 15.000; 14.499 → 14.000."""
    return int((Decimal(so) / 1000).quantize(Decimal(1), rounding=ROUND_HALF_UP) * 1000)


def thanh_tien(so_luong: Decimal | int | str, don_gia: int) -> int:
    """so_luong × đơn giá, làm tròn đến đồng."""
    return int((Decimal(str(so_luong)) * don_gia).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def tinh_tien(
    cac_dong: Iterable[DongTien], la_vip: bool = False, ty_le_giam: int = 10, pham_vi: str = TIEN_CONG
) -> KetQuaTinhTien:
    if pham_vi not in (TIEN_CONG, CONG_VA_VAT_TU):
        raise ValueError(f"Phạm vi giảm VIP không hợp lệ: {pham_vi}")
    tong = {"CONG": 0, "VAT_TU": 0, "PHI_KHAC": 0}
    for dong in cac_dong:
        if dong.ben_chiu == "KHACH":
            tong[dong.loai] += int(dong.thanh_tien)
    co_so_giam = tong["CONG"] + (tong["VAT_TU"] if pham_vi == CONG_VA_VAT_TU else 0)
    giam = lam_tron_nghin(Decimal(co_so_giam) * ty_le_giam / 100) if la_vip else 0
    return KetQuaTinhTien(
        tien_cong=tong["CONG"],
        tien_vat_tu=tong["VAT_TU"],
        phi_khac=tong["PHI_KHAC"],
        giam_vip=giam,
        tong_tien=tong["CONG"] + tong["VAT_TU"] + tong["PHI_KHAC"] - giam,
    )
