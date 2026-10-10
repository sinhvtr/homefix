"""UC02 — Tiếp nhận và tạo đơn dịch vụ (kịch bản nghiệm thu SPEC mục 9)."""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.danh_muc.models import DiaChi, KhachHang, ThietBi
from apps.don_sua_chua.dao import sinh_ma_don
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.models import VaiTro
from apps.tiep_nhan_dieu_phoi.models import LichHen
from tests.conftest import (
    DiaChiFactory,
    DichVuFactory,
    KhachHangFactory,
    KhuVucFactory,
    ThietBiFactory,
    tao_don,
)

pytestmark = pytest.mark.django_db
VN = ZoneInfo("Asia/Ho_Chi_Minh")


@pytest.fixture
def tong_dai_client(client_vai_tro):
    return client_vai_tro(VaiTro.TONG_DAI)


@pytest.fixture
def dich_vu():
    return DichVuFactory(ten_dich_vu="Vệ sinh điều hòa treo tường", loai_thiet_bi="DIEU_HOA")


def _du_lieu(dich_vu, **them):
    return {
        "so_dien_thoai": "0912 345 678",
        "dich_vu_yeu_cau": dich_vu.pk,
        "kenh_tiep_nhan": "DIEN_THOAI",
        "mo_ta_su_co": "Điều hòa chảy nước",
        **them,
    }


def test_tao_don_khach_moi_thieu_ten(tong_dai_client, dich_vu):
    kv = KhuVucFactory()
    phan_hoi = tong_dai_client.post(
        "/don/moi/",
        _du_lieu(
            dich_vu, dia_chi_chi_tiet="Số 5 ngõ 12 Láng", khu_vuc=kv.pk, khung_gio_mong_muon="Chiều mai"
        ),
    )
    don = DonSuaChua.objects.get()
    assert phan_hoi.status_code == 302 and phan_hoi.url == f"/don/{don.ma_don}/"
    assert don.trang_thai == "CHO_XAC_NHAN_LICH"  # T1
    assert don.khach_hang.so_dien_thoai == "0912345678" and don.khach_hang.ho_ten == ""
    assert don.dia_chi.khu_vuc == kv and don.dia_chi.la_mac_dinh
    assert don.thieu_thong_tin
    assert don.khung_gio_mong_muon == "Chiều mai" and don.nguoi_tao == tong_dai_client.nguoi_dung
    hanh_dong = list(
        NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{don.ma_don}").values_list("hanh_dong", flat=True)
    )
    assert "TAO_DON" in hanh_dong and "DOI_TRANG_THAI" in hanh_dong
    noi_dung = tong_dai_client.get(phan_hoi.url).content.decode()
    assert "Thiếu thông tin" in noi_dung and "Chờ khách xác nhận lịch" in noi_dung


def test_tao_don_khach_cu_chon_dia_chi_cu_va_thiet_bi(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678", ho_ten="Chị Lan"))
    tb = ThietBiFactory(dia_chi=dc)
    tong_dai_client.post(
        "/don/moi/", _du_lieu(dich_vu, ho_ten="Tên khác", dia_chi_id=dc.pk, thiet_bi_ids=[tb.pk])
    )
    don = DonSuaChua.objects.get()
    assert don.dia_chi == dc and list(don.thiet_bi.all()) == [tb]
    assert DiaChi.objects.count() == 1 and KhachHang.objects.count() == 1
    assert don.khach_hang.ho_ten == "Chị Lan"  # giữ tên đã có (người gọi có thể khác chủ nhà)


def test_khach_cu_thieu_ten_duoc_bo_sung_ten(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678", ho_ten=""))
    tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, ho_ten="Anh Minh", dia_chi_id=dc.pk))
    dc.khach_hang.refresh_from_db()
    assert dc.khach_hang.ho_ten == "Anh Minh"


def test_tao_don_kem_thiet_bi_moi(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    tong_dai_client.post(
        "/don/moi/",
        _du_lieu(
            dich_vu,
            dia_chi_id=dc.pk,
            thiet_bi_moi_loai="DIEU_HOA",
            thiet_bi_moi_hang="LG",
            thiet_bi_moi_vi_tri="P. ngủ",
        ),
    )
    tb = ThietBi.objects.get()
    assert (tb.dia_chi, tb.hang_san_xuat) == (dc, "LG")
    assert list(DonSuaChua.objects.get().thiet_bi.all()) == [tb]


def test_tao_don_chot_lich_ngay_t2(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678", ho_ten="Chị Lan"))
    tong_dai_client.post(
        "/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk, ngay_hen="2099-10-12", khung_gio="08:00-10:00")
    )
    don = DonSuaChua.objects.get()
    lich = LichHen.objects.get(don=don)
    assert don.trang_thai == "CHO_CU_THO"  # T2
    assert lich.trang_thai == "HIEU_LUC"
    assert lich.bat_dau == datetime(2099, 10, 12, 8, 0, tzinfo=VN)
    assert lich.ket_thuc == datetime(2099, 10, 12, 10, 0, tzinfo=VN)
    assert not don.thieu_thong_tin
    noi_dung = tong_dai_client.get(f"/don/{don.ma_don}/").content.decode()
    assert f"Đơn {don.ma_don} đã được hẹn lịch 08:00-10:00 ngày 12/10/2099" in noi_dung  # tin nhắn mẫu
    assert "Sao chép" in noi_dung


def test_br07_don_khach_vip_co_uu_tien(tong_dai_client, dich_vu):
    kh = KhachHangFactory(so_dien_thoai="0912345678", loai_khach="VIP", vip_thu_cong=True, ly_do_vip="GĐ")
    dc = DiaChiFactory(khach_hang=kh)
    tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk))
    assert DonSuaChua.objects.get().uu_tien


def test_khach_thuong_khong_uu_tien(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk))
    assert not DonSuaChua.objects.get().uu_tien


def test_ma_don_tang_trong_ngay_va_ve_001_sang_ngay_moi():
    with freeze_time(datetime(2026, 10, 10, 23, 58, tzinfo=VN)) as dong_ho:
        assert [sinh_ma_don() for _ in range(3)] == ["HF261010-001", "HF261010-002", "HF261010-003"]
        dong_ho.tick(timedelta(minutes=3))  # 00:01 ngày 11/10 giờ Việt Nam (UTC vẫn là ngày 10)
        assert sinh_ma_don() == "HF261011-001"
        assert sinh_ma_don() == "HF261011-002"


def test_ma_don_qua_tiep_nhan_lien_tiep(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    for _ in range(3):
        tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk))
    hom_nay = timezone.localdate().strftime("%y%m%d")
    assert sorted(DonSuaChua.objects.values_list("ma_don", flat=True)) == [
        f"HF{hom_nay}-00{i}" for i in (1, 2, 3)
    ]


def test_canh_bao_trung_don_van_cho_luu(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    cu = tao_don("CHO_CU_THO", dia_chi=dc, dich_vu=DichVuFactory(loai_thiet_bi="DIEU_HOA"))
    tao_don("DA_HUY", dia_chi=dc, dich_vu=DichVuFactory(loai_thiet_bi="DIEU_HOA"))  # đã hủy — không tính
    tao_don(
        "CHO_CU_THO", dia_chi=dc, dich_vu=DichVuFactory(loai_thiet_bi="MAY_GIAT")
    )  # khác loại — không tính
    phan_hoi = tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk), follow=True)
    noi_dung = phan_hoi.content.decode()
    assert DonSuaChua.objects.count() == 4
    assert f"Có thể trùng đơn {cu.ma_don}" in noi_dung
    assert noi_dung.count("Có thể trùng đơn") == 1


def test_khong_canh_bao_khi_khac_dia_chi(tong_dai_client, dich_vu):
    kh = KhachHangFactory(so_dien_thoai="0912345678")
    tao_don("CHO_CU_THO", dia_chi=DiaChiFactory(khach_hang=kh, la_mac_dinh=False), dich_vu=dich_vu)
    dc = DiaChiFactory(khach_hang=kh)
    noi_dung = tong_dai_client.post(
        "/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk), follow=True
    ).content.decode()
    assert "Có thể trùng đơn" not in noi_dung


@pytest.mark.parametrize(
    ("them", "o_loi", "thong_diep"),
    [
        ({"so_dien_thoai": "12345"}, "so_dien_thoai", "Số điện thoại không hợp lệ"),
        ({"dich_vu_yeu_cau": ""}, "dich_vu_yeu_cau", ""),
        ({}, "dia_chi_chi_tiet", "Chọn địa chỉ có sẵn hoặc nhập địa chỉ mới"),
        ({"dia_chi_chi_tiet": "Số 1"}, "khu_vuc", "bắt buộc chọn khu vực"),
        ({"dia_chi_chi_tiet": "Số 1", "ngay_hen": "2099-01-01"}, "khung_gio", "cả ngày hẹn và khung giờ"),
    ],
)
def test_thieu_thong_tin_bat_buoc_khong_luu(tong_dai_client, dich_vu, them, o_loi, thong_diep):
    du_lieu = {**_du_lieu(dich_vu), **them}
    if o_loi == "khung_gio":
        du_lieu["khu_vuc"] = KhuVucFactory().pk
    phan_hoi = tong_dai_client.post("/don/moi/", du_lieu)
    assert phan_hoi.status_code == 200
    assert o_loi in phan_hoi.context["form"].errors
    assert thong_diep in phan_hoi.content.decode()
    assert not DonSuaChua.objects.exists()


def test_dia_chi_cua_khach_khac_bi_tu_choi(tong_dai_client, dich_vu):
    KhachHangFactory(so_dien_thoai="0912345678")
    la = DiaChiFactory()
    phan_hoi = tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=la.pk))
    assert "không thuộc khách hàng" in phan_hoi.content.decode() and not DonSuaChua.objects.exists()


def test_thiet_bi_khac_dia_chi_bi_tu_choi(tong_dai_client, dich_vu):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    tb_la = ThietBiFactory()
    phan_hoi = tong_dai_client.post("/don/moi/", _du_lieu(dich_vu, dia_chi_id=dc.pk, thiet_bi_ids=[tb_la.pk]))
    assert "không thuộc địa chỉ" in phan_hoi.content.decode() and not DonSuaChua.objects.exists()


def test_dich_vu_ngung_ap_dung_khong_chon_duoc(tong_dai_client):
    dv = DichVuFactory(dang_ap_dung=False)
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678"))
    tong_dai_client.post("/don/moi/", _du_lieu(dv, dia_chi_id=dc.pk))
    assert not DonSuaChua.objects.exists()


# ------------------------------------------------------------ tra cứu SĐT (HTMX)


def test_tra_cuu_sdt_hien_thong_tin_khach_va_5_don_gan_nhat(tong_dai_client):
    kh = KhachHangFactory(so_dien_thoai="0912345678", ho_ten="Chị Lan", loai_khach="VIP")
    dc = DiaChiFactory(khach_hang=kh, dia_chi_chi_tiet="Số 9 Kim Mã")
    ThietBiFactory(dia_chi=dc, hang_san_xuat="Panasonic")
    don = [tao_don("HOAN_THANH", dia_chi=dc) for _ in range(6)]
    phan_hoi = tong_dai_client.get("/khach-hang/tra-cuu/", {"sdt": "+84 912 345 678"}, HTTP_HX_REQUEST="true")
    noi_dung = phan_hoi.content.decode()
    assert phan_hoi.status_code == 200 and "<html" not in noi_dung
    assert (
        "Chị Lan" in noi_dung and "VIP" in noi_dung and "Số 9 Kim Mã" in noi_dung and "Panasonic" in noi_dung
    )
    assert sum(d.ma_don in noi_dung for d in don) == 5
    assert don[0].ma_don not in noi_dung  # đơn cũ nhất không hiện


def test_tra_cuu_theo_so_phu(tong_dai_client):
    KhachHangFactory(so_dien_thoai="0912345678", so_dien_thoai_phu="0987654321", ho_ten="Anh Hùng")
    assert "Anh Hùng" in tong_dai_client.get("/khach-hang/tra-cuu/", {"sdt": "0987654321"}).content.decode()


def test_tra_cuu_khach_moi_va_sdt_sai(tong_dai_client):
    assert "Khách mới" in tong_dai_client.get("/khach-hang/tra-cuu/", {"sdt": "0911111111"}).content.decode()
    assert "không hợp lệ" in tong_dai_client.get("/khach-hang/tra-cuu/", {"sdt": "123"}).content.decode()


def test_tao_them_don_cho_cuoc_goi_nay_dien_san(tong_dai_client):
    dc = DiaChiFactory(khach_hang=KhachHangFactory(so_dien_thoai="0912345678", ho_ten="Chị Lan"))
    noi_dung = tong_dai_client.get("/don/moi/", {"sdt": "0912345678", "dia_chi": dc.pk}).content.decode()
    assert 'value="0912345678"' in noi_dung and "Chị Lan" in noi_dung
    assert f'value="{dc.pk}" class="mt-1 h-5 w-5"\n                   checked' in noi_dung


def test_khong_xoa_duoc_dich_vu_khach_khu_vuc_da_co_don(client_quan_tri):
    """A-36: từ P2, dịch vụ / khách / địa chỉ đã có đơn bị chặn xóa (khóa ngoại PROTECT)."""
    don = tao_don("CHO_CU_THO")
    client_quan_tri.post(f"/danh-muc/dich-vu/{don.dich_vu_yeu_cau_id}/xoa/")
    client_quan_tri.post(f"/danh-muc/khach-hang/{don.khach_hang_id}/xoa/")
    client_quan_tri.post(f"/danh-muc/dia-chi/{don.dia_chi_id}/xoa/")
    phan_hoi = client_quan_tri.get(f"/danh-muc/khach-hang/{don.khach_hang_id}/")
    assert phan_hoi.status_code == 200
    assert DonSuaChua.objects.filter(pk=don.pk).exists()
    assert DiaChi.objects.filter(pk=don.dia_chi_id).exists()
    from apps.danh_muc.models import DichVu

    assert DichVu.objects.filter(pk=don.dich_vu_yeu_cau_id).exists()


def test_xoa_du_lieu_mau_xoa_ca_don_cua_khach_mau():
    from django.core.management import call_command

    call_command("nap_du_lieu_mau")
    kh = KhachHang.objects.filter(so_dien_thoai__startswith="0900").first()
    goc = tao_don("HOAN_THANH", dia_chi=kh.ds_dia_chi.first())
    tao_don(dia_chi=goc.dia_chi, loai_don="BAO_HANH", don_goc=goc)
    call_command("xoa_du_lieu_mau", "--xac-nhan")
    assert not DonSuaChua.objects.exists() and not KhachHang.objects.exists()
