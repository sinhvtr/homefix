"""UC03 — Lập lịch hẹn và xác nhận với khách; BR08 — nhắc sau 24 giờ, 3 lần không phản hồi thì hủy."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from freezegun import freeze_time

from apps.don_sua_chua.models import LY_DO_HET_LUOT_NHAC, DonSuaChua
from apps.don_sua_chua.tac_vu import nhac_xac_nhan_lich
from apps.he_thong.models import CauHinh, NhatKyThaoTac
from apps.tai_khoan.models import VaiTro
from apps.tiep_nhan_dieu_phoi.dao import LichHenDAO
from apps.tiep_nhan_dieu_phoi.models import LichHen
from tests.conftest import tao_don, tao_lich

pytestmark = pytest.mark.django_db


@pytest.fixture
def tong_dai_client(client_vai_tro):
    return client_vai_tro(VaiTro.TONG_DAI)


def _don(don):
    return DonSuaChua.objects.get(pk=don.pk)


# ============================================================== UC03


def test_khong_the_co_hai_lich_hieu_luc():
    don = tao_don("CHO_CU_THO")
    tao_lich(don)
    with pytest.raises(IntegrityError), transaction.atomic():
        tao_lich(don)  # ràng buộc duy nhất có điều kiện ở CSDL
    with pytest.raises(ValidationError, match="Đổi hẹn"):
        LichHenDAO._tao(don.nguoi_tao, don, timezone.now(), timezone.now() + timedelta(hours=1))
    assert LichHen.objects.filter(don=don, trang_thai="HIEU_LUC").count() == 1


def test_csdl_chan_lich_ket_thuc_truoc_bat_dau():
    don = tao_don()
    with pytest.raises(IntegrityError), transaction.atomic():
        tao_lich(don, gio=-1)


def test_chot_lich_cho_xac_nhan_lich_sang_cho_cu_tho(tong_dai_client):
    don = tao_don()
    phan_hoi = tong_dai_client.post(
        f"/don/{don.ma_don}/chot-lich/",
        {"chot-ngay": "2099-03-02", "chot-khung_gio": "13:00-15:00"},
        follow=True,
    )
    assert _don(don).trang_thai == "CHO_CU_THO"  # T3
    lich = LichHen.objects.get(don=don)
    assert lich.khung_gio == "13:00-15:00 ngày 02/03/2099"
    assert "Chờ cử thợ" in phan_hoi.content.decode()
    nk = NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{don.ma_don}", hanh_dong="DOI_TRANG_THAI").get()
    assert nk.du_lieu_sau == {"trang_thai": "CHO_CU_THO", "chuyen": "T3"}
    assert nk.nguoi_dung == tong_dai_client.nguoi_dung


def test_chot_lich_sai_trang_thai_bao_loi(tong_dai_client):
    don = tao_don("CHO_CU_THO")
    tao_lich(don)
    phan_hoi = tong_dai_client.post(
        f"/don/{don.ma_don}/chot-lich/",
        {"chot-ngay": "2099-03-02", "chot-khung_gio": "13:00-15:00"},
        follow=True,
    )
    assert "không chốt lịch được" in phan_hoi.content.decode()


def test_khung_gio_ngoai_cau_hinh_bi_tu_choi(tong_dai_client):
    don = tao_don()
    tong_dai_client.post(
        f"/don/{don.ma_don}/chot-lich/", {"chot-ngay": "2099-03-02", "chot-khung_gio": "02:00-03:00"}
    )
    assert _don(don).trang_thai == "CHO_XAC_NHAN_LICH"


def test_doi_hen_sinh_lich_moi_lich_cu_thay_the(tong_dai_client):
    don = tao_don("DA_CO_THO")
    cu = tao_lich(don)
    tong_dai_client.post(
        f"/don/{don.ma_don}/doi-hen/",
        {"doi-ngay": "2099-03-05", "doi-khung_gio": "15:00-17:00", "doi-ly_do": "Khách bận"},
    )
    cu.refresh_from_db()
    moi = LichHen.objects.get(don=don, trang_thai="HIEU_LUC")
    assert cu.trang_thai == "DA_THAY_THE"
    assert moi.pk != cu.pk and moi.ly_do_doi_hen == "Khách bận"
    assert moi.khung_gio == "15:00-17:00 ngày 05/03/2099"
    assert _don(don).trang_thai == "DA_CO_THO"  # đổi hẹn không đổi trạng thái
    nk = NhatKyThaoTac.objects.get(hanh_dong="DOI_HEN")
    assert nk.du_lieu_truoc["lich_hen"] == cu.pk and nk.du_lieu_sau["lich_hen"] == moi.pk


def test_doi_hen_bat_buoc_ly_do():
    don = tao_don("CHO_CU_THO")
    tao_lich(don)
    with pytest.raises(ValidationError):
        LichHenDAO.doi_hen(don.nguoi_tao, don, date(2099, 1, 1), "08:00-10:00", "")


def test_khach_chua_tra_loi_tang_dem_chung_voi_br08(tong_dai_client):
    don = tao_don()
    for _ in range(3):
        tong_dai_client.post(f"/don/{don.ma_don}/khach-chua-tra-loi/")
    assert _don(don).so_lan_nhac_xac_nhan == 3
    tong_dai_client.post(f"/don/{don.ma_don}/khach-chua-tra-loi/")
    d = _don(don)
    assert d.trang_thai == "DA_HUY" and d.ly_do_huy == LY_DO_HET_LUOT_NHAC


def test_huy_don_can_ly_do_va_huy_lich(tong_dai_client):
    don = tao_don("CHO_CU_THO")
    lich = tao_lich(don)
    phan_hoi = tong_dai_client.post(f"/don/{don.ma_don}/huy/", {"ly_do": ""})
    assert phan_hoi.status_code == 200 and _don(don).trang_thai == "CHO_CU_THO"
    tong_dai_client.post(f"/don/{don.ma_don}/huy/", {"ly_do": "Khách tự sửa được"})
    lich.refresh_from_db()
    assert _don(don).trang_thai == "DA_HUY" and lich.trang_thai == "DA_HUY"


def test_ke_toan_xem_duoc_don_nhung_khong_thay_nut_va_sdt_bi_an(client_vai_tro):
    don = tao_don()
    noi_dung = client_vai_tro(VaiTro.KE_TOAN).get(f"/don/{don.ma_don}/").content.decode()
    assert don.ma_don in noi_dung
    assert "Chốt lịch" not in noi_dung and "Hủy đơn" not in noi_dung
    assert don.khach_hang.so_dien_thoai not in noi_dung


def test_don_khong_ton_tai_404(tong_dai_client):
    assert tong_dai_client.get("/don/HF000101-001/").status_code == 404


# ============================================================== BR08


def _tao_don_luc(luc):
    with freeze_time(luc):
        return tao_don()


def test_br08_chuoi_24_48_72_96_gio():
    t0 = timezone.now()
    don = _tao_don_luc(t0)
    assert nhac_xac_nhan_lich(t0 + timedelta(hours=23, minutes=59)) == {"da_nhac": 0, "da_huy": 0}
    for gio, so_lan in [(24, 1), (48, 2), (72, 3)]:
        assert nhac_xac_nhan_lich(t0 + timedelta(hours=gio)) == {"da_nhac": 1, "da_huy": 0}
        d = _don(don)
        assert (d.trang_thai, d.so_lan_nhac_xac_nhan, d.lan_nhac_cuoi) == (
            "CHO_XAC_NHAN_LICH",
            so_lan,
            t0 + timedelta(hours=gio),
        )
    assert nhac_xac_nhan_lich(t0 + timedelta(hours=95)) == {"da_nhac": 0, "da_huy": 0}
    assert nhac_xac_nhan_lich(t0 + timedelta(hours=96)) == {"da_nhac": 0, "da_huy": 1}
    d = _don(don)
    assert d.trang_thai == "DA_HUY" and d.ly_do_huy == "Khách không phản hồi sau 3 lần nhắc"
    nk = NhatKyThaoTac.objects.filter(hanh_dong="DOI_TRANG_THAI", doi_tuong=f"DonSuaChua:{d.ma_don}").first()
    assert nk.nguoi_dung is None and nk.du_lieu_sau["chuyen"] == "T5"


def test_br08_luy_dang_chay_lai_khong_nhac_hai_lan():
    t0 = timezone.now()
    don = _tao_don_luc(t0)
    luc = t0 + timedelta(hours=25)
    nhac_xac_nhan_lich(luc)
    assert nhac_xac_nhan_lich(luc) == {"da_nhac": 0, "da_huy": 0}
    assert nhac_xac_nhan_lich(luc + timedelta(minutes=59)) == {"da_nhac": 0, "da_huy": 0}
    assert _don(don).so_lan_nhac_xac_nhan == 1


def test_br08_chi_ap_dung_don_cho_xac_nhan_lich():
    t0 = timezone.now()
    with freeze_time(t0):
        da_chot = tao_don("CHO_CU_THO")
    nhac_xac_nhan_lich(t0 + timedelta(days=10))
    assert _don(da_chot).so_lan_nhac_xac_nhan == 0 and _don(da_chot).trang_thai == "CHO_CU_THO"


def test_br08_nut_khach_chua_tra_loi_dem_lai_moc_24_gio(tong_dai_client):
    t0 = timezone.now()
    don = _tao_don_luc(t0)
    with freeze_time(t0 + timedelta(hours=10)):
        tong_dai_client.post(f"/don/{don.ma_don}/khach-chua-tra-loi/")
    assert nhac_xac_nhan_lich(t0 + timedelta(hours=24)) == {"da_nhac": 0, "da_huy": 0}  # mới nhắc lúc 10h
    assert nhac_xac_nhan_lich(t0 + timedelta(hours=34)) == {"da_nhac": 1, "da_huy": 0}
    assert _don(don).so_lan_nhac_xac_nhan == 2


def test_br08_doc_tham_so_tu_cau_hinh():
    CauHinh.objects.filter(khoa="NHAC_XAC_NHAN_SAU_GIO").update(gia_tri="12")
    CauHinh.objects.filter(khoa="SO_LAN_NHAC_TOI_DA").update(gia_tri="1")
    t0 = timezone.now()
    don = _tao_don_luc(t0)
    nhac_xac_nhan_lich(t0 + timedelta(hours=12))
    nhac_xac_nhan_lich(t0 + timedelta(hours=24))
    assert _don(don).trang_thai == "DA_HUY"


def test_br08_viec_can_lam_goi_lai_khach_tren_bang_don(tong_dai_client):
    t0 = timezone.now() - timedelta(hours=30)
    don = _tao_don_luc(t0)
    nhac_xac_nhan_lich()
    noi_dung = tong_dai_client.get("/tong-dai/").content.decode()
    assert "Gọi lại khách" in noi_dung and don.ma_don in noi_dung
    assert "đang chờ chốt giờ hẹn" in noi_dung  # tin nhắn mẫu kèm việc cần làm


def test_br08_lich_tac_vu_hang_gio_trong_django_q():
    from django_q.models import Schedule

    lich = Schedule.objects.get(name="nhac_xac_nhan_lich")
    assert lich.func == "apps.don_sua_chua.tac_vu.nhac_xac_nhan_lich"
    assert lich.schedule_type == Schedule.HOURLY
