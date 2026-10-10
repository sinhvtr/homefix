"""UC07 — Thợ nhận / từ chối đơn được giao (PWA). NFR04: không lộ dữ liệu khách; NFR07: ≤ 3 chạm."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.models import VaiTro
from apps.thong_bao.models import ThongBao
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO
from apps.tiep_nhan_dieu_phoi.models import PhanCong
from tests.conftest import (
    DiaChiFactory,
    DichVuFactory,
    KhachHangFactory,
    NguoiDungFactory,
    don_cho_cu_tho,
    tao_don,
    tao_tho_phu_hop,
)

pytestmark = pytest.mark.django_db
HEN = datetime(2099, 6, 1, 8, 0, tzinfo=ZoneInfo("Asia/Ho_Chi_Minh"))
SDT_KHACH = "0911222333"
DIA_CHI = "Số 7 ngõ 99 Trần Duy Hưng"


@pytest.fixture
def tong_dai():
    return NguoiDungFactory(vai_tro=VaiTro.TONG_DAI)


@pytest.fixture
def dv():
    return DichVuFactory(ten_dich_vu="Vệ sinh điều hòa")


@pytest.fixture
def don(dv):
    kh = KhachHangFactory(so_dien_thoai=SDT_KHACH, ho_ten="Chị Mai")
    return don_cho_cu_tho(
        ngay_gio=HEN, dich_vu=dv, dia_chi=DiaChiFactory(khach_hang=kh, dia_chi_chi_tiet=DIA_CHI)
    )


@pytest.fixture
def tho(dv):
    return tao_tho_phu_hop(dv, ho_ten="Thợ Bình")


@pytest.fixture
def pc(don, tho, tong_dai):
    PhanCongDAO.gui_de_nghi(tong_dai, don, [tho.pk])
    return PhanCong.objects.get(don=don, tho=tho)


@pytest.fixture
def c_tho(client, tho):
    client.force_login(tho.nguoi_dung)
    return client


# ------------------------------------------------------------ NFR04


def test_trang_de_nghi_khong_lo_sdt_dia_chi(c_tho, pc):
    noi_dung = c_tho.get(f"/tho/de-nghi/{pc.pk}/").content.decode()
    assert "Vệ sinh điều hòa" in noi_dung and "NHẬN VIỆC" in noi_dung and "150.000 đ" in noi_dung
    assert SDT_KHACH not in noi_dung and DIA_CHI not in noi_dung and "Chị Mai" not in noi_dung


def test_tho_khong_xem_duoc_don_chua_nhan_ke_ca_doan_url(c_tho, pc, don):
    assert c_tho.get(f"/tho/don/{don.ma_don}/").status_code == 404
    don_khac = tao_don("DA_CO_THO", tho=tao_tho_phu_hop(DichVuFactory()))
    assert c_tho.get(f"/tho/don/{don_khac.ma_don}/").status_code == 404


def test_tho_khong_xem_duoc_de_nghi_cua_tho_khac(c_tho, don, dv, tong_dai):
    khac = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [khac.pk])
    pc_khac = PhanCong.objects.get(tho=khac)
    assert c_tho.get(f"/tho/de-nghi/{pc_khac.pk}/").status_code == 404
    assert c_tho.post(f"/tho/de-nghi/{pc_khac.pk}/nhan/").status_code == 404
    assert c_tho.post(f"/tho/de-nghi/{pc_khac.pk}/tu-choi/", {"ly_do": "BAN"}).status_code == 404
    assert PhanCong.objects.get(pk=pc_khac.pk).trang_thai == "CHO_PHAN_HOI"


def test_tho_khong_vao_danh_muc_khach_hang(c_tho):
    assert c_tho.get("/danh-muc/khach-hang/").status_code == 403


# ------------------------------------------------------------ NFR07: nhận việc ≤ 3 chạm


def test_nhan_viec_toi_da_3_cham(c_tho, pc, don):
    # Chạm 1: mở thông báo → trang đề nghị (đường dẫn trong thông báo)
    tb = ThongBao.objects.get(nguoi_nhan=pc.tho.nguoi_dung)
    assert c_tho.get(tb.duong_dan).status_code == 200
    # Chạm 2: NHẬN VIỆC (không có hộp xác nhận thứ hai) → Chạm 3 không cần: kết quả hiện ngay
    phan_hoi = c_tho.post(f"/tho/de-nghi/{pc.pk}/nhan/", follow=True)
    noi_dung = phan_hoi.content.decode()
    assert phan_hoi.redirect_chain[-1][0] == f"/tho/don/{don.ma_don}/"
    assert "Đã nhận việc" in noi_dung
    # Sau khi nhận: đủ tên, SĐT (gọi), địa chỉ, nút mở bản đồ
    assert f'href="tel:{SDT_KHACH}"' in noi_dung and DIA_CHI in noi_dung and "Chị Mai" in noi_dung
    assert "https://www.google.com/maps/search/?api=1&amp;query=" in noi_dung


def test_nhan_muon_sau_qua_han_khi_don_con_cho(c_tho, pc, don):
    with freeze_time(timezone.now() + timedelta(minutes=16)):
        PhanCongDAO.kiem_tra_qua_han()
    assert PhanCong.objects.get(pk=pc.pk).trang_thai == "QUA_HAN"
    assert "vẫn nhận được" in c_tho.get("/tho/").content.decode()
    c_tho.post(f"/tho/de-nghi/{pc.pk}/nhan/")
    assert DonSuaChua.objects.get(pk=don.pk).trang_thai == "DA_CO_THO"
    assert NhatKyThaoTac.objects.get(hanh_dong="NHAN_VIEC").du_lieu_sau["nhan_muon"] is True


def test_nhan_muon_khi_don_da_co_tho_khac_thi_bao_da_co_tho(c_tho, pc, don, dv, tong_dai):
    with freeze_time(timezone.now() + timedelta(minutes=16)):
        PhanCongDAO.kiem_tra_qua_han()
    khac = tao_tho_phu_hop(dv)
    PhanCongDAO.gui_de_nghi(tong_dai, don, [khac.pk])
    PhanCongDAO.nhan_viec(khac.nguoi_dung, PhanCong.objects.get(tho=khac).pk)
    phan_hoi = c_tho.post(f"/tho/de-nghi/{pc.pk}/nhan/", follow=True)
    assert DonSuaChua.objects.get(pk=don.pk).tho_id == khac.pk
    assert phan_hoi.redirect_chain[-1][0] == "/tho/"


def test_tu_choi_mot_cham_chon_ly_do(c_tho, pc, tong_dai, don):
    noi_dung = c_tho.get(f"/tho/de-nghi/{pc.pk}/").content.decode()
    for nhan in ("Đang bận", "Xa quá", "Không đúng chuyên môn", "Lý do khác"):
        assert nhan in noi_dung
    c_tho.post(f"/tho/de-nghi/{pc.pk}/tu-choi/", {"ly_do": "XA"})
    pc.refresh_from_db()
    assert (pc.trang_thai, pc.ly_do_tu_choi) == ("TU_CHOI", "XA")
    assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de__contains="từ chối").exists()
    assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de=f"Cần cử lại {don.ma_don}").exists()


def test_tra_viec_truoc_khi_den_noi(c_tho, pc, don, tong_dai):
    c_tho.post(f"/tho/de-nghi/{pc.pk}/nhan/")
    c_tho.post(f"/tho/don/{don.ma_don}/tra-viec/", {"ly_do": ""})
    assert DonSuaChua.objects.get(pk=don.pk).trang_thai == "DA_CO_THO"  # thiếu lý do
    c_tho.post(f"/tho/don/{don.ma_don}/tra-viec/", {"ly_do": "Xe hỏng"})
    d = DonSuaChua.objects.get(pk=don.pk)
    assert (d.trang_thai, d.tho_id) == ("CHO_CU_THO", None)
    assert ThongBao.objects.filter(nguoi_nhan=tong_dai, tieu_de__contains="trả việc").exists()


# ------------------------------------------------------------ trang chủ thợ, công tắc, cài đặt


def test_trang_chu_tho_ba_khoi_va_dem_nguoc(c_tho, pc, don):
    noi_dung = c_tho.get("/tho/").content.decode()
    for khoi in ("Sẵn sàng nhận việc", "Đề nghị đang chờ (1)", "Việc hôm nay", "Việc sắp tới"):
        assert khoi in noi_dung
    assert f'href="/tho/de-nghi/{pc.pk}/"' in noi_dung and "data-han=" in noi_dung
    c_tho.post(f"/tho/de-nghi/{pc.pk}/nhan/")
    noi_dung = c_tho.get("/tho/").content.decode()
    assert "Việc sắp tới (1)" in noi_dung and don.ma_don in noi_dung


def test_cong_tac_san_sang_nhan_viec(c_tho, tho, don, dv):
    from apps.tiep_nhan_dieu_phoi.dao import ThoDAO

    c_tho.post("/tho/san-sang/")
    tho.refresh_from_db()
    assert not tho.dang_nhan_viec
    assert ThoDAO.goi_y_tho(don)[0].ly_do_loai == ["Tắt nhận việc"]
    c_tho.post("/tho/san-sang/")
    tho.refresh_from_db()
    assert tho.dang_nhan_viec


def test_cai_dat_doi_kenh_va_gui_thu(c_tho, tho):
    c_tho.post("/tho/cai-dat/", {"kenh_thong_bao": "TELEGRAM"})
    tho.refresh_from_db()
    assert tho.kenh_thong_bao == "TELEGRAM"
    c_tho.post("/tho/cai-dat/", {"kenh_thong_bao": "SMS"})
    tho.refresh_from_db()
    assert tho.kenh_thong_bao == "TELEGRAM"
    c_tho.post("/tho/cai-dat/gui-thu/")
    assert ThongBao.objects.filter(nguoi_nhan=tho.nguoi_dung, tieu_de="Thông báo thử").exists()
    noi_dung = c_tho.get("/tho/cai-dat/").content.decode()
    assert "Thêm vào Màn hình chính" in noi_dung


def test_tho_khong_sua_duoc_truong_ngoai_quyen(tho):
    from django.core.exceptions import ValidationError

    from apps.danh_muc.dao import ThoDAO

    with pytest.raises(ValidationError):
        ThoDAO.cap_nhat_cua_toi(tho.nguoi_dung, hinh_thuc="CHINH_THUC")
