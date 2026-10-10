from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from freezegun import freeze_time

from apps.he_thong.cau_hinh import MAC_DINH, cau_hinh
from apps.he_thong.models import CauHinh

pytestmark = pytest.mark.django_db


def test_migration_nap_du_tham_so_muc_8_2():
    assert set(CauHinh.objects.values_list("khoa", flat=True)) == set(MAC_DINH)


@pytest.mark.parametrize(
    ("khoa", "gia_tri"),
    [
        ("THOI_HAN_PHAN_HOI_PHUT", 15),
        ("NHAC_XAC_NHAN_SAU_GIO", 24),
        ("SO_LAN_NHAC_TOI_DA", 3),
        ("BAO_HANH_VE_SINH_NGAY", 7),
        ("BAO_HANH_SUA_CHUA_NGAY", 90),
        ("VIP_SO_DON_TOI_THIEU", 3),
        ("VIP_TY_LE_GIAM", 10),
        ("VIP_PHAM_VI_GIAM", "TIEN_CONG"),
        ("NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN", 2_000_000),
        ("PHI_KIEM_TRA_KHI_TU_CHOI", 0),
        ("CANH_BAO_CHO_CU_THO_PHUT", 30),
        ("DEM_DI_CHUYEN_PHUT", 30),
        ("SO_ANH_TOI_THIEU_KHI_HOAN_THANH", 1),
    ],
)
def test_gia_tri_mac_dinh_dung_kieu(khoa, gia_tri):
    assert cau_hinh(khoa) == gia_tri


def test_khung_gio_la_danh_sach_json():
    assert cau_hinh("KHUNG_GIO") == [
        "08:00-10:00",
        "10:00-12:00",
        "13:00-15:00",
        "15:00-17:00",
        "17:00-19:00",
    ]


def test_mau_tin_nhan_co_du_bien():
    mau = cau_hinh("MAU_TIN_NHAN_XAC_NHAN_LICH")
    tin = mau.format(ten_khach="anh Nam", ma_don="HF261010-007", khung_gio="08:00-10:00")
    assert "HF261010-007" in tin and "anh Nam" in tin and "08:00-10:00" in tin


def test_khong_co_ban_ghi_thi_dung_mac_dinh():
    CauHinh.objects.filter(khoa="VIP_TY_LE_GIAM").delete()
    assert cau_hinh("VIP_TY_LE_GIAM") == 10


def test_khoa_khong_ton_tai():
    with pytest.raises(KeyError):
        cau_hinh("KHONG_CO")


def test_bo_dem_60_giay():
    with freeze_time(timezone.now()) as dong_ho:
        assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 15
        # Sửa thẳng CSDL (bỏ qua save) → vẫn đọc giá trị trong bộ đệm cho tới khi hết 60 giây.
        CauHinh.objects.filter(khoa="THOI_HAN_PHAN_HOI_PHUT").update(gia_tri="20")
        dong_ho.tick(timedelta(seconds=59))
        assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 15
        dong_ho.tick(timedelta(seconds=2))
        assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 20


def test_luu_cau_hinh_xoa_bo_dem_ngay():
    assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 15
    ban_ghi = CauHinh.objects.get(khoa="THOI_HAN_PHAN_HOI_PHUT")
    ban_ghi.gia_tri = "25"
    ban_ghi.save()
    assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 25


@pytest.mark.parametrize(("gia_tri", "kieu"), [("muoi", "INT"), ("[1,", "JSON"), ("co le", "BOOL")])
def test_tu_choi_gia_tri_sai_kieu(gia_tri, kieu):
    with pytest.raises(ValidationError):
        CauHinh(khoa="THU", gia_tri=gia_tri, kieu=kieu).save()


def test_kieu_bool():
    CauHinh.objects.create(khoa="CO_BAT", gia_tri="có", kieu="BOOL")
    assert cau_hinh("CO_BAT") is True
