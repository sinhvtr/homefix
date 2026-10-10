import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.tai_khoan.models import NguoiDung, VaiTro

pytestmark = pytest.mark.django_db


def test_so_dien_thoai_chuan_hoa_khi_luu(tao_nguoi_dung):
    nguoi = tao_nguoi_dung(so_dien_thoai="+84 912.345.678", username="thu")
    nguoi.refresh_from_db()
    assert nguoi.so_dien_thoai == "0912345678"


def test_so_dien_thoai_khong_hop_le_bi_tu_choi(tao_nguoi_dung):
    with pytest.raises(ValidationError):
        tao_nguoi_dung(so_dien_thoai="12345")


def test_so_dien_thoai_duy_nhat(tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678", username="a")
    with pytest.raises(IntegrityError), transaction.atomic():
        tao_nguoi_dung(so_dien_thoai="+84912345678", username="b")


def test_vai_tro_ngoai_danh_sach_bi_csdl_chan(tao_nguoi_dung):
    with pytest.raises(IntegrityError), transaction.atomic():
        tao_nguoi_dung(vai_tro="KHACH")


def test_quan_tri_co_quyen_tong_dai(tao_nguoi_dung):
    quan_tri = tao_nguoi_dung(vai_tro=VaiTro.QUAN_TRI)
    tho = tao_nguoi_dung(vai_tro=VaiTro.THO)
    assert quan_tri.la_vai_tro(VaiTro.TONG_DAI)
    assert not quan_tri.la_vai_tro(VaiTro.KE_TOAN)
    assert not tho.la_vai_tro(VaiTro.TONG_DAI)


def test_khoa_tai_khoan_bang_is_active(tao_nguoi_dung):
    nguoi = tao_nguoi_dung(is_active=False)
    assert nguoi.dang_hoat_dong is False


def test_tao_superuser_ky_thuat():
    nguoi = NguoiDung.objects.create_superuser(
        username="kythuat",
        password="Mat-khau-thu-123",
        ho_ten="Kỹ thuật",
        so_dien_thoai="0988 000 111",
        vai_tro=VaiTro.QUAN_TRI,
    )
    assert nguoi.is_superuser and nguoi.so_dien_thoai == "0988000111"
