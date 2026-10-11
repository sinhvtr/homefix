"""BR05 — tác vụ hằng ngày dong_don_het_bao_hanh (T18): đúng ngày theo giờ Việt Nam, lũy đẳng, lịch 00:15."""

from datetime import timedelta

import pytest
from django_q.models import Schedule
from freezegun import freeze_time

from apps.bao_hanh.dao import BaoHanhDAO
from apps.bao_hanh.models import PhieuBaoHanh
from apps.bao_hanh.tac_vu import dong_don_het_bao_hanh
from apps.don_sua_chua.dao import DonSuaChuaDAO
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from tests.conftest import don_hoan_thanh

pytestmark = pytest.mark.django_db
VS = "VE_SINH_BAO_DUONG"


def _trang_thai(don):
    return DonSuaChua.objects.values_list("trang_thai", flat=True).get(pk=don.pk)


@pytest.fixture
def ve_sinh_xong():
    don, _, tong_dai = don_hoan_thanh(VS)
    don.tong_dai = tong_dai
    return don, PhieuBaoHanh.objects.get(don=don).ngay_het_han


def test_br05_dong_don_dung_ngay_het_han(ve_sinh_xong):
    don, het_han = ve_sinh_xong
    with freeze_time(f"{het_han:%Y-%m-%d} 23:59:00+07:00"):  # ngày hết hạn vẫn còn hạn
        assert dong_don_het_bao_hanh() == {"da_dong": 0}
    assert _trang_thai(don) == "HOAN_THANH"
    with freeze_time(f"{het_han + timedelta(days=1):%Y-%m-%d} 00:15:00+07:00"):  # UTC vẫn là ngày hôm trước
        assert dong_don_het_bao_hanh() == {"da_dong": 1}
        assert dong_don_het_bao_hanh() == {"da_dong": 0}  # lũy đẳng
    assert _trang_thai(don) == "DA_DONG"
    nk = NhatKyThaoTac.objects.get(doi_tuong=f"DonSuaChua:{don.ma_don}", du_lieu_sau__chuyen="T18")
    assert nk.nguoi_dung is None and nk.du_lieu_sau["ly_do"] == "Hết hạn bảo hành"


def test_br05_don_dang_bao_hanh_chua_dong_den_khi_don_con_ket_thuc(ve_sinh_xong):
    don, het_han = ve_sinh_xong
    bh = BaoHanhDAO.tao_don_bao_hanh(don.tong_dai, don, mo_ta_su_co="Lại chảy nước")
    with freeze_time(f"{het_han + timedelta(days=3):%Y-%m-%d} 00:15:00+07:00"):
        assert dong_don_het_bao_hanh() == {"da_dong": 0}
        assert _trang_thai(don) == "DANG_BAO_HANH"
        DonSuaChuaDAO.huy(don.tong_dai, bh, "Khách hủy")  # T17
        assert _trang_thai(don) == "HOAN_THANH"
        assert dong_don_het_bao_hanh() == {"da_dong": 1}
    assert _trang_thai(don) == "DA_DONG"


def test_br05_don_bao_hanh_con_dong_theo_phieu_don_goc(ve_sinh_xong):
    goc, het_han = ve_sinh_xong
    bh, _, _ = don_hoan_thanh(VS, loai_don="BAO_HANH", don_goc=goc, nguyen_nhan_bao_hanh="TAY_NGHE")
    assert not PhieuBaoHanh.objects.filter(don=bh).exists()
    with freeze_time(f"{het_han:%Y-%m-%d} 12:00:00+07:00"):
        assert dong_don_het_bao_hanh() == {"da_dong": 0}
    with freeze_time(f"{het_han + timedelta(days=1):%Y-%m-%d} 00:15:00+07:00"):
        assert dong_don_het_bao_hanh() == {"da_dong": 2}
    assert (_trang_thai(goc), _trang_thai(bh)) == ("DA_DONG", "DA_DONG")


def test_br05_khong_dong_don_chua_hoan_thanh_hoac_da_huy():
    from tests.conftest import tao_don

    dang_sua, huy = tao_don("DANG_SUA"), tao_don("DA_HUY")
    with freeze_time("2099-12-31 00:15:00+07:00"):
        assert dong_don_het_bao_hanh() == {"da_dong": 0}
    assert (_trang_thai(dang_sua), _trang_thai(huy)) == ("DANG_SUA", "DA_HUY")


def test_lich_tac_vu_dong_don_00_15():
    lich = Schedule.objects.get(name="dong_don_het_bao_hanh")
    assert lich.func == "apps.bao_hanh.tac_vu.dong_don_het_bao_hanh" and lich.schedule_type == Schedule.DAILY
    from django.utils import timezone

    gio = timezone.localtime(lich.next_run)
    assert (gio.hour, gio.minute) == (0, 15)
