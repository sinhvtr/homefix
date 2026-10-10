"""Bảng ví dụ tính tiền (SPEC 7.2) — nghiệm thu P4: đơn thường, VIP hai phạm vi, đơn bảo hành."""

from decimal import Decimal

import pytest

from apps.don_sua_chua.tinh_tien import (
    CONG_VA_VAT_TU,
    TIEN_CONG,
    DongTien,
    KetQuaTinhTien,
    lam_tron_nghin,
    thanh_tien,
    tinh_tien,
)

C, V, P = "CONG", "VAT_TU", "PHI_KHAC"

# (tên, các dòng, la_vip, phạm vi, kết quả (công, vật tư, phí khác, giảm VIP, tổng))
BANG_VI_DU = [
    (
        "đơn thường",
        [DongTien(C, 300_000), DongTien(V, 300_000), DongTien(P, 50_000)],
        False,
        TIEN_CONG,
        (300_000, 300_000, 50_000, 0, 650_000),
    ),
    (
        "VIP giảm 10% tiền công, 34.500 làm tròn lên 35.000",
        [DongTien(C, 345_000), DongTien(V, 200_000)],
        True,
        TIEN_CONG,
        (345_000, 200_000, 0, 35_000, 510_000),
    ),
    (
        "VIP giảm tiền công, 34.400 làm tròn xuống 34.000",
        [DongTien(C, 344_000)],
        True,
        TIEN_CONG,
        (344_000, 0, 0, 34_000, 310_000),
    ),
    (
        "VIP phạm vi công + vật tư: (300.000 + 245.000) × 10% = 54.500 → 55.000",
        [DongTien(C, 300_000), DongTien(V, 245_000)],
        True,
        CONG_VA_VAT_TU,
        (300_000, 245_000, 0, 55_000, 490_000),
    ),
    (
        "VIP: phí khác không được giảm",
        [DongTien(C, 100_000), DongTien(P, 500_000)],
        True,
        CONG_VA_VAT_TU,
        (100_000, 0, 500_000, 10_000, 590_000),
    ),
    (
        "đơn bảo hành lỗi tay nghề: công thợ chịu, vật tư công ty chịu → khách trả 0",
        [DongTien(C, 300_000, "THO"), DongTien(V, 450_000, "CONG_TY")],
        True,
        CONG_VA_VAT_TU,
        (0, 0, 0, 0, 0),
    ),
    (
        "đơn bảo hành lỗi vật tư: mọi dòng công ty chịu",
        [DongTien(C, 300_000, "CONG_TY"), DongTien(V, 450_000, "CONG_TY")],
        False,
        TIEN_CONG,
        (0, 0, 0, 0, 0),
    ),
    ("không có dòng nào", [], True, TIEN_CONG, (0, 0, 0, 0, 0)),
]


@pytest.mark.parametrize(
    ("ten", "dong", "la_vip", "pham_vi", "mong_doi"), BANG_VI_DU, ids=[b[0] for b in BANG_VI_DU]
)
def test_bang_vi_du_tinh_tien(ten, dong, la_vip, pham_vi, mong_doi):
    assert tinh_tien(dong, la_vip=la_vip, ty_le_giam=10, pham_vi=pham_vi) == KetQuaTinhTien(*mong_doi)


def test_ty_le_giam_cau_hinh_duoc():
    assert tinh_tien([DongTien(C, 200_000)], la_vip=True, ty_le_giam=15).giam_vip == 30_000


@pytest.mark.parametrize(
    ("vao", "ra"), [(14_500, 15_000), (14_499, 14_000), (0, 0), (999, 1_000), (Decimal("1499.5"), 1_000)]
)
def test_lam_tron_nghin(vao, ra):
    assert lam_tron_nghin(vao) == ra


@pytest.mark.parametrize(
    ("so_luong", "don_gia", "ra"),
    [(1, 150_000, 150_000), ("1.5", 33_333, 50_000), (Decimal("0.25"), 10_002, 2_501), (3, 0, 0)],
)
def test_thanh_tien_lam_tron_den_dong(so_luong, don_gia, ra):
    assert thanh_tien(so_luong, don_gia) == ra


def test_ket_qua_la_so_nguyen_khong_float():
    kq = tinh_tien([DongTien(C, 333_333)], la_vip=True, ty_le_giam=10)
    assert all(type(v) is int for v in kq.__dict__.values())


def test_pham_vi_sai_bao_loi():
    with pytest.raises(ValueError):
        tinh_tien([], pham_vi="TAT_CA")
