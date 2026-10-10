from datetime import datetime

import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from apps.he_thong.models import CauHinh, NhatKyChiDuocThem, NhatKyThaoTac
from apps.he_thong.nhat_ky import ghi_nhat_ky, lay_dia_chi_ip, ten_doi_tuong

pytestmark = pytest.mark.django_db


def test_ghi_nhat_ky_luu_day_du(tao_nguoi_dung):
    nguoi = tao_nguoi_dung()
    ban_ghi = ghi_nhat_ky(
        nguoi,
        "SUA_GIA",
        "DichVu:VS-DH-01",
        du_lieu_truoc={"don_gia": 150000},
        du_lieu_sau={"don_gia": 170000, "luc": datetime(2026, 10, 10, 8, 0)},
        dia_chi_ip="192.168.1.10",
    )
    ban_ghi.refresh_from_db()
    assert ban_ghi.nguoi_dung == nguoi
    assert ban_ghi.hanh_dong == "SUA_GIA"
    assert ban_ghi.doi_tuong == "DichVu:VS-DH-01"
    assert ban_ghi.du_lieu_truoc == {"don_gia": 150000}
    assert ban_ghi.du_lieu_sau["don_gia"] == 170000
    assert ban_ghi.dia_chi_ip == "192.168.1.10"
    assert ban_ghi.thoi_diem is not None


def test_ten_doi_tuong():
    ban_ghi = CauHinh.objects.get(khoa="VIP_TY_LE_GIAM")
    assert ten_doi_tuong(ban_ghi) == f"CauHinh:{ban_ghi.pk}"
    assert ten_doi_tuong("DonSuaChua:HF261010-007") == "DonSuaChua:HF261010-007"


def test_nguoi_dung_an_danh_ghi_null():
    assert ghi_nhat_ky(AnonymousUser(), "THU", "X:1").nguoi_dung is None


def test_khong_duoc_sua_nhat_ky():
    ban_ghi = ghi_nhat_ky(None, "THU", "X:1")
    ban_ghi.hanh_dong = "DOI"
    with pytest.raises(NhatKyChiDuocThem):
        ban_ghi.save()
    with pytest.raises(NhatKyChiDuocThem):
        NhatKyThaoTac.objects.filter(pk=ban_ghi.pk).update(hanh_dong="DOI")


def test_khong_duoc_xoa_nhat_ky():
    ban_ghi = ghi_nhat_ky(None, "THU", "X:1")
    with pytest.raises(NhatKyChiDuocThem):
        ban_ghi.delete()
    with pytest.raises(NhatKyChiDuocThem):
        NhatKyThaoTac.objects.all().delete()
    assert NhatKyThaoTac.objects.filter(pk=ban_ghi.pk).exists()


def test_lay_dia_chi_ip():
    rf = RequestFactory()
    assert lay_dia_chi_ip(rf.get("/", REMOTE_ADDR="10.0.0.2")) == "10.0.0.2"
    assert lay_dia_chi_ip(rf.get("/", HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1")) == "1.2.3.4"
    assert lay_dia_chi_ip(None) is None
