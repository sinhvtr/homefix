"""Ảnh hiện trường: nén phía máy chủ, bỏ EXIF, tối đa 5 ảnh, phục vụ qua view có kiểm quyền (NFR04)."""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.don_sua_chua.dao import HienTruongDAO
from apps.don_sua_chua.models import AnhHienTruong
from apps.he_thong.anh import nen_anh
from apps.tai_khoan.models import VaiTro
from tests.conftest import anh_thu, don_tho_da_nhan

pytestmark = pytest.mark.django_db


def test_nen_anh_1600_jpeg_bo_exif():
    noi_dung, rong, cao = nen_anh(anh_thu(4000, 3000))
    anh = Image.open(io.BytesIO(noi_dung.read()))
    assert (anh.format, rong, cao, anh.size) == ("JPEG", 1600, 1200, (1600, 1200))
    assert not dict(anh.getexif())  # không còn EXIF (hãng máy, GPS…)


def test_nen_anh_xoay_dung_chieu_theo_exif():
    _, rong, cao = nen_anh(anh_thu(3000, 2000, xoay_exif=6))  # ảnh dọc chụp xoay 90°
    assert (rong, cao) == (1067, 1600)


def test_anh_nho_va_png_trong_suot_van_nhan():
    _, rong, cao = nen_anh(anh_thu(800, 600, dinh_dang="PNG", ten="a.png"))
    assert (rong, cao) == (800, 600)


@pytest.mark.parametrize("noi_dung", [b"khong phai anh", b"%PDF-1.4 ..."])
def test_tu_choi_tep_khong_phai_anh(noi_dung):
    with pytest.raises(ValidationError, match="không phải ảnh"):
        nen_anh(SimpleUploadedFile("x.jpg", noi_dung))


def test_toi_da_5_anh_hien_truong():
    don, tho, _ = don_tho_da_nhan()
    for _ in range(5):
        HienTruongDAO.luu_anh(tho.nguoi_dung, don, anh_thu(600, 400))
    with pytest.raises(ValidationError, match="Tối đa 5"):
        HienTruongDAO.luu_anh(tho.nguoi_dung, don, anh_thu(600, 400))
    assert AnhHienTruong.objects.filter(don=don).count() == 5


def test_ten_tep_khong_chua_thong_tin_khach():
    don, tho, _ = don_tho_da_nhan()
    anh = HienTruongDAO.luu_anh(
        tho.nguoi_dung, don, anh_thu(600, 400, ten=f"{don.khach_hang.so_dien_thoai}.jpg")
    )
    assert don.khach_hang.so_dien_thoai not in anh.tep.name and anh.tep.name.startswith("anh/")


def test_xem_anh_co_kiem_quyen(client, client_vai_tro):
    don, tho, _ = don_tho_da_nhan()
    anh = HienTruongDAO.luu_anh(tho.nguoi_dung, don, anh_thu(600, 400))
    url = f"/anh/{anh.pk}/"
    assert client.get(url).status_code == 302  # chưa đăng nhập
    client.force_login(tho.nguoi_dung)
    phan_hoi = client.get(url)
    assert phan_hoi.status_code == 200 and phan_hoi["Content-Type"] == "image/jpeg"
    assert "private" in phan_hoi["Cache-Control"]
    _, tho_khac, _ = don_tho_da_nhan()
    client.force_login(tho_khac.nguoi_dung)
    assert client.get(url).status_code == 404  # thợ khác: không lộ sự tồn tại
    for vai_tro in (VaiTro.TONG_DAI, VaiTro.KE_TOAN, VaiTro.GIAM_DOC):
        assert client_vai_tro(vai_tro).get(url).status_code == 200
    assert client_vai_tro(VaiTro.TONG_DAI).get("/anh/999999/").status_code == 404


def test_media_khong_phuc_vu_cong_khai(client):
    don, tho, _ = don_tho_da_nhan()
    anh = HienTruongDAO.luu_anh(tho.nguoi_dung, don, anh_thu(600, 400))
    assert client.get(f"/media/{anh.tep.name}").status_code == 404
