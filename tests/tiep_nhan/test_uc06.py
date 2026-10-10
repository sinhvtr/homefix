"""UC06 — Bảng đơn trong ngày (P2 cơ bản)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.models import VaiTro
from tests.conftest import DiaChiFactory, KhachHangFactory, KhuVucFactory, ThoFactory, tao_don, tao_lich

pytestmark = pytest.mark.django_db
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.fixture
def tong_dai_client(client_vai_tro):
    return client_vai_tro(VaiTro.TONG_DAI)


def _cot(phan_hoi, ten):
    return dict(phan_hoi.context["bang"].cot)[ten]


def test_cac_cot_theo_trang_thai_dang_xu_ly(tong_dai_client):
    don = {
        tt: tao_don(tt)
        for tt in ["CHO_XAC_NHAN_LICH", "CHO_CU_THO", "DA_CO_THO", "CHO_DUYET_GIA", "DANG_SUA"]
    }
    tao_don("HOAN_THANH")
    phan_hoi = tong_dai_client.get("/tong-dai/")
    assert _cot(phan_hoi, "Chờ xác nhận lịch") == [don["CHO_XAC_NHAN_LICH"]]
    assert _cot(phan_hoi, "Chờ cử thợ") == [don["CHO_CU_THO"]]
    assert _cot(phan_hoi, "Đã có thợ") == [don["DA_CO_THO"]]
    assert set(_cot(phan_hoi, "Đang thực hiện")) == {don["CHO_DUYET_GIA"], don["DANG_SUA"]}
    assert len(phan_hoi.context["bang"].ket_thuc_hom_nay) == 1


def test_don_vip_nam_dau_cot(tong_dai_client):
    thuong_cu = tao_don("CHO_CU_THO", ngay_tiep_nhan=timezone.now() - timedelta(hours=3))
    vip = tao_don("CHO_CU_THO", uu_tien=True)
    phan_hoi = tong_dai_client.get("/tong-dai/")
    assert _cot(phan_hoi, "Chờ cử thợ") == [vip, thuong_cu]
    assert "border-amber-400" in phan_hoi.content.decode()  # viền vàng


def test_nhan_tren_the_don(tong_dai_client):
    tao_don("CHO_CU_THO", so_lan_giuc=2, canh_bao_chua_cu_duoc=True)
    noi_dung = tong_dai_client.get("/tong-dai/").content.decode()
    assert "Khách giục ×2" in noi_dung and "Chưa cử được thợ" in noi_dung and "Thiếu thông tin" in noi_dung


def test_loc_theo_khu_vuc_trang_thai_tu_khoa_va_tho(tong_dai_client):
    kv = KhuVucFactory(ten="Cầu Giấy")
    tho = ThoFactory()
    a = tao_don("CHO_CU_THO", dia_chi=DiaChiFactory(khu_vuc=kv))
    b = tao_don(
        "DA_CO_THO", dia_chi=DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678")), tho=tho
    )

    def ds(**loc):
        bang = tong_dai_client.get("/tong-dai/", loc).context["bang"]
        return {d for _, cot in bang.cot for d in cot}

    assert ds(khu_vuc=kv.pk) == {a}
    assert ds(trang_thai="DA_CO_THO") == {b}
    assert ds(q="+84 912 345 678") == {b}
    assert ds(q=a.ma_don) == {a}
    assert ds(tho=tho.pk) == {b}


def test_loc_theo_ngay_hen(tong_dai_client):
    co_lich = tao_don("CHO_CU_THO")
    tao_lich(co_lich, ngay_gio=datetime(2099, 5, 1, 8, 0, tzinfo=VN))
    khac_ngay = tao_don("CHO_CU_THO")
    tao_lich(khac_ngay, ngay_gio=datetime(2099, 5, 2, 8, 0, tzinfo=VN))
    bang = tong_dai_client.get("/tong-dai/", {"ngay": "2099-05-01"}).context["bang"]
    assert {d for _, cot in bang.cot for d in cot} == {co_lich}


def test_tu_lam_moi_htmx_chi_tra_phan_bang(tong_dai_client):
    tao_don()
    phan_hoi = tong_dai_client.get("/tong-dai/", HTTP_HX_REQUEST="true")
    noi_dung = phan_hoi.content.decode()
    assert "<html" not in noi_dung and "Chờ xác nhận lịch" in noi_dung
    trang = tong_dai_client.get("/tong-dai/").content.decode()
    assert 'hx-trigger="every 30s"' in trang


def test_nut_khach_giuc_tang_dem_va_ghi_nhat_ky(tong_dai_client):
    don = tao_don("CHO_CU_THO")
    tong_dai_client.post(f"/don/{don.ma_don}/giuc/")
    tong_dai_client.post(f"/don/{don.ma_don}/giuc/")
    assert DonSuaChua.objects.get(pk=don.pk).so_lan_giuc == 2
    assert (
        NhatKyThaoTac.objects.filter(hanh_dong="KHACH_GIUC", nguoi_dung=tong_dai_client.nguoi_dung).count()
        == 2
    )


def test_khong_giuc_don_da_ket_thuc(tong_dai_client):
    don = tao_don("HOAN_THANH")
    tong_dai_client.post(f"/don/{don.ma_don}/giuc/")
    assert DonSuaChua.objects.get(pk=don.pk).so_lan_giuc == 0


def test_giam_doc_xem_chi_doc(client_vai_tro):
    don = tao_don("CHO_CU_THO")
    c = client_vai_tro(VaiTro.GIAM_DOC)
    noi_dung = c.get("/tong-dai/").content.decode()
    assert don.ma_don in noi_dung
    assert "Khách giục</button>" not in noi_dung and "+ Đơn mới" not in noi_dung
    assert c.post(f"/don/{don.ma_don}/giuc/").status_code == 403
