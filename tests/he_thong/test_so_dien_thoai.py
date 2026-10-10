import pytest
from django.core.exceptions import ValidationError

from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


@pytest.mark.parametrize(
    ("dau_vao", "ket_qua"),
    [
        ("0912345678", "0912345678"),
        ("0912 345 678", "0912345678"),
        ("0912.345.678", "0912345678"),
        ("+84 912 345 678", "0912345678"),
        ("+84912345678", "0912345678"),
        ("84912345678", "0912345678"),
        ("0084912345678", "0912345678"),
        ("(091) 234-5678", "0912345678"),
    ],
)
def test_chuan_hoa_sdt_hop_le(dau_vao, ket_qua):
    assert chuan_hoa_sdt(dau_vao) == ket_qua


@pytest.mark.parametrize(
    "dau_vao", ["", None, "091234567", "09123456789", "1912345678", "09123abc78", "+1 912345678"]
)
def test_chuan_hoa_sdt_khong_hop_le(dau_vao):
    with pytest.raises(ValidationError):
        chuan_hoa_sdt(dau_vao)
