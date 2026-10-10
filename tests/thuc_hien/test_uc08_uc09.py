"""UC08 báo giá, UC09 hoàn thành, UC10 vật tư; BR05, BR06, BR07 (giảm VIP), NFR06 — kịch bản qua màn hình thợ."""

from datetime import timedelta

import pytest
from django.utils import timezone
from freezegun import freeze_time

from apps.bao_hanh.models import PhieuBaoHanh
from apps.danh_muc.models import KhachHang
from apps.don_sua_chua.dao import HienTruongDAO
from apps.don_sua_chua.models import AnhHienTruong, DonSuaChua, HangMucSuaChua
from apps.don_sua_chua.trang_thai import ChuyenTrangThaiKhongHopLe
from apps.he_thong.models import CauHinh, NhatKyThaoTac
from apps.tai_chinh.models import ThanhToan
from apps.tai_khoan.models import VaiTro
from apps.thong_bao.models import ThongBao
from tests.conftest import DichVuFactory, KhachHangFactory, anh_thu, don_tho_da_nhan, tao_don

pytestmark = pytest.mark.django_db
VS, SC = "VE_SINH_BAO_DUONG", "SUA_CHUA_THAY_VAT_TU"


def _don(don):
    return DonSuaChua.objects.get(pk=don.pk)


@pytest.fixture
def ve_sinh(client):
    don, tho, tong_dai = don_tho_da_nhan(VS, don_gia=150_000)
    client.force_login(tho.nguoi_dung)
    client.tho, client.tong_dai = tho, tong_dai
    return don, client


@pytest.fixture
def sua_chua(client):
    don, tho, tong_dai = don_tho_da_nhan(SC, don_gia=350_000)
    client.force_login(tho.nguoi_dung)
    client.tho, client.tong_dai = tho, tong_dai
    return don, client


def _den_noi(c, don):
    return c.post(f"/tho/don/{don.ma_don}/den-noi/")


# ============================================================== Đã đến nơi — BR06 (T9 / T10)


def test_br06_ve_sinh_den_noi_tinh_theo_bang_gia(ve_sinh):
    don, c = ve_sinh
    phan_hoi = _den_noi(c, don)
    assert phan_hoi.url == f"/tho/don/{don.ma_don}/hoan-thanh/"
    d = _don(don)
    assert d.trang_thai == "DANG_SUA"
    hm = d.ds_hang_muc.get()
    assert (hm.loai, hm.don_gia_thuc_te, hm.dich_vu_id) == ("CONG", 150_000, d.dich_vu_yeu_cau_id)


def test_br06_sua_chua_den_noi_phai_bao_gia(sua_chua):
    don, c = sua_chua
    assert _den_noi(c, don).url == f"/tho/don/{don.ma_don}/bao-gia/"
    assert _don(don).trang_thai == "CHO_DUYET_GIA" and not _don(don).ds_hang_muc.exists()
    # chưa có báo giá được duyệt thì không vào được trang hoàn thành
    assert c.get(f"/tho/don/{don.ma_don}/hoan-thanh/").url == f"/tho/don/{don.ma_don}/"


def test_br06_khach_duyet_gia_tren_don_ve_sinh_bi_loi(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        HienTruongDAO.khach_duyet_gia(c.tho.nguoi_dung, _don(don), "A")


# ============================================================== UC08 — báo giá


def _them_cong(c, don, dv=None, so_luong="1", don_gia=""):
    return c.post(
        f"/tho/don/{don.ma_don}/bao-gia/",
        {
            "hanh_dong": "them_dich_vu",
            "dich_vu": (dv or don.dich_vu_yeu_cau).pk,
            "so_luong": so_luong,
            "don_gia": don_gia,
        },
    )


def _them_vat_tu(c, don, trang="bao-gia", **kw):
    du_lieu = {
        "hanh_dong": "them_vat_tu",
        "mo_ta": "Gas R32",
        "so_luong": "1",
        "don_gia": "200.000",
        "gia_mua": "120000",
    }
    du_lieu.update(kw)
    return c.post(f"/tho/don/{don.ma_don}/{trang}/", du_lieu)


def test_uc08_tinh_tong_dung_va_dong_y_duoi_nguong(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don)  # đơn giá để trống → lấy bảng giá 350.000
    _them_vat_tu(c, don)
    noi_dung = c.get(f"/tho/don/{don.ma_don}/bao-gia/").content.decode()
    assert 'data-tong="550000"' in noi_dung and "550.000 đ" in noi_dung
    phan_hoi = c.post(
        f"/tho/don/{don.ma_don}/bao-gia/", {"hanh_dong": "dong_y", "nguoi_xac_nhan": "Anh Hải (con trai)"}
    )
    assert phan_hoi.url == f"/tho/don/{don.ma_don}/hoan-thanh/"
    d = _don(don)
    assert d.trang_thai == "DANG_SUA"  # T11
    assert (d.bao_gia_tong, d.bao_gia_nguoi_xac_nhan) == (550_000, "Anh Hải (con trai)")
    assert all(hm.la_bao_gia for hm in d.ds_hang_muc.all())


def test_uc08_vip_giam_tien_cong_tren_bao_gia(client):
    kh = KhachHangFactory(loai_khach="VIP", vip_thu_cong=True, ly_do_vip="GĐ")
    don, tho, _ = don_tho_da_nhan(SC, khach=kh, don_gia=350_000)
    client.force_login(tho.nguoi_dung)
    _den_noi(client, don)
    _them_cong(client, don)
    _them_vat_tu(client, don)
    noi_dung = client.get(f"/tho/don/{don.ma_don}/bao-gia/").content.decode()
    assert "Giảm giá VIP" in noi_dung and "−35.000 đ" in noi_dung and 'data-tong="515000"' in noi_dung


def test_uc08_bao_gia_vuot_nguong_cho_tong_dai_xac_nhan(sua_chua, client_vai_tro):
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don, don_gia="2500000")
    c.post(f"/tho/don/{don.ma_don}/bao-gia/", {"hanh_dong": "dong_y", "nguoi_xac_nhan": "Chị Lan"})
    d = _don(don)
    assert d.trang_thai == "CHO_DUYET_GIA" and d.cho_tong_dai_xac_nhan_gia
    assert ThongBao.objects.filter(
        nguoi_nhan=c.tong_dai, tieu_de=f"Báo giá {don.ma_don} cần gọi xác nhận"
    ).exists()
    assert "chờ tổng đài gọi xác nhận" in c.get(f"/tho/don/{don.ma_don}/bao-gia/").content.decode()
    # Tổng đài thấy việc cần làm + nút xác nhận (T12)
    td = client_vai_tro(VaiTro.TONG_DAI)
    assert "Báo giá chờ xác nhận" in td.get("/tong-dai/").content.decode()
    assert "Đã xác nhận với khách" in td.get(f"/don/{don.ma_don}/").content.decode()
    td.post(f"/don/{don.ma_don}/xac-nhan-gia/")
    d = _don(don)
    assert d.trang_thai == "DANG_SUA" and not d.cho_tong_dai_xac_nhan_gia
    assert ThongBao.objects.filter(
        nguoi_nhan=c.tho.nguoi_dung, tieu_de=f"Báo giá {don.ma_don} đã được xác nhận"
    ).exists()


def test_uc08_khach_tu_choi_gia_co_phi_kiem_tra(sua_chua):
    CauHinh.objects.filter(khoa="PHI_KIEM_TRA_KHI_TU_CHOI").update(gia_tri="100000")
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don)
    c.post(f"/tho/don/{don.ma_don}/bao-gia/", {"hanh_dong": "tu_choi", "ly_do": "Giá cao"})
    d = _don(don)
    assert (d.trang_thai, d.ly_do_huy) == ("DA_HUY", "Giá cao")  # T13
    assert d.ds_hang_muc.get(loai="PHI_KHAC").thanh_tien == 100_000
    assert ThongBao.objects.filter(
        nguoi_nhan=c.tong_dai, tieu_de__startswith="Khách từ chối báo giá"
    ).exists()


def test_uc08_anh_bao_gia_tuy_chon(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don)
    c.post(
        f"/tho/don/{don.ma_don}/bao-gia/",
        {"hanh_dong": "dong_y", "nguoi_xac_nhan": "A", "anh_bao_gia": anh_thu()},
    )
    assert AnhHienTruong.objects.filter(don=don, loai="BAO_GIA").count() == 1


# ============================================================== UC10 — vật tư


def test_uc10_vat_tu_tho_ung_mac_dinh_va_goi_y_ten(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_vat_tu(c, don, mo_ta="Tụ điều hòa 35uF", co_hoa_don="on")
    hm = HangMucSuaChua.objects.get(loai="VAT_TU")
    assert (hm.nguoi_ung, hm.gia_mua, hm.co_hoa_don, hm.don_gia_thuc_te) == ("THO", 120_000, True, 200_000)
    assert '<option value="Tụ điều hòa 35uF">' in c.get(f"/tho/don/{don.ma_don}/bao-gia/").content.decode()
    _them_vat_tu(c, don, mo_ta="Ống đồng", nguoi_ung="CONG_TY")
    assert HangMucSuaChua.objects.get(mo_ta="Ống đồng").nguoi_ung == "CONG_TY"


def test_uc10_vat_tu_thieu_ten_hoac_so_luong_sai(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_vat_tu(c, don, mo_ta="")
    _them_vat_tu(c, don, so_luong="0")
    assert not HangMucSuaChua.objects.exists()


# ============================================================== UC09 — hoàn thành


def _hoan_thanh(c, don, **kw):
    du_lieu = {"hanh_dong": "hoan_thanh", "so_tien": str(_don(don).tong_tien), "hinh_thuc": "TIEN_MAT"}
    du_lieu.update(kw)
    return c.post(f"/tho/don/{don.ma_don}/hoan-thanh/", du_lieu, follow=True)


def _tai_anh(c, don, so=1):
    return c.post(
        f"/tho/don/{don.ma_don}/hoan-thanh/", {"hanh_dong": "tai_anh", "anh": [anh_thu() for _ in range(so)]}
    )


def test_uc09_thieu_anh_khong_hoan_thanh_duoc(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    noi_dung = _hoan_thanh(c, don).content.decode()
    assert _don(don).trang_thai == "DANG_SUA"
    assert "Chưa đủ ảnh hiện trường" in noi_dung
    assert not ThanhToan.objects.exists() and not PhieuBaoHanh.objects.exists()


def test_uc09_hoan_thanh_ck_cong_ty_khong_can_nop_va_phat_hanh_bao_hanh(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    _tai_anh(c, don)
    with freeze_time(timezone.now()):
        hom_nay = timezone.localdate()
        phan_hoi = _hoan_thanh(c, don, hinh_thuc="CK_TAI_KHOAN_CONG_TY")
    d = _don(don)
    assert (d.trang_thai, d.tong_tien_phai_thu) == ("HOAN_THANH", 150_000)  # T15
    tt = ThanhToan.objects.get(don=don)
    assert (tt.so_tien, tt.hinh_thuc, tt.trang_thai, tt.tho) == (
        150_000,
        "CK_TAI_KHOAN_CONG_TY",
        "KHONG_CAN_NOP",
        c.tho,
    )
    phieu = PhieuBaoHanh.objects.get(don=don)
    assert (phieu.ma, phieu.ngay_bat_dau, phieu.ngay_het_han) == (
        f"BH-{don.ma_don}",
        hom_nay,
        hom_nay + timedelta(days=7),
    )
    assert "7 ngày" in phieu.dieu_kien
    noi_dung = phan_hoi.content.decode()
    assert phan_hoi.redirect_chain[-1][0] == f"/tho/don/{don.ma_don}/da-xong/"
    assert f"mã BH-{don.ma_don}" in noi_dung and "Sao chép" in noi_dung  # tin nhắn cảm ơn + bảo hành
    assert ThongBao.objects.filter(
        nguoi_nhan=c.tong_dai, tieu_de__contains=f"đã hoàn thành {don.ma_don}"
    ).exists()
    hanh_dong = set(
        NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{don.ma_don}").values_list("hanh_dong", flat=True)
    )
    assert {"GHI_TIEN", "HOAN_THANH", "PHAT_HANH_BAO_HANH", "DOI_TRANG_THAI"} <= hanh_dong


@pytest.mark.parametrize(
    ("hinh_thuc", "trang_thai"), [("TIEN_MAT", "CHUA_NOP"), ("CK_TAI_KHOAN_THO", "CHUA_NOP")]
)
def test_uc09_tien_tho_giu_phai_nop(ve_sinh, hinh_thuc, trang_thai):
    don, c = ve_sinh
    _den_noi(c, don)
    _tai_anh(c, don)
    _hoan_thanh(c, don, hinh_thuc=hinh_thuc)
    assert ThanhToan.objects.get(don=don).trang_thai == trang_thai


def test_uc09_so_thu_lech_bat_buoc_ly_do(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    _tai_anh(c, don)
    noi_dung = _hoan_thanh(c, don, so_tien="100.000").content.decode()
    assert _don(don).trang_thai == "DANG_SUA" and "ghi lý do" in noi_dung
    _hoan_thanh(c, don, so_tien="100.000", ly_do_lech="Khách thiếu, hẹn chuyển khoản sau")
    assert _don(don).trang_thai == "HOAN_THANH"
    assert ThanhToan.objects.get(don=don).so_tien == 100_000
    nk = NhatKyThaoTac.objects.get(hanh_dong="GHI_TIEN")
    assert nk.du_lieu_sau["ly_do_lech"] == "Khách thiếu, hẹn chuyển khoản sau"
    assert nk.du_lieu_sau["tong_tien_phai_thu"] == 150_000


def test_uc09_chung_tu_chuyen_khoan_tuy_chon(ve_sinh, client_vai_tro):
    don, c = ve_sinh
    _den_noi(c, don)
    _tai_anh(c, don)
    _hoan_thanh(c, don, hinh_thuc="CK_TAI_KHOAN_THO", anh_chung_tu=anh_thu())
    tt = ThanhToan.objects.get(don=don)
    assert tt.anh_chung_tu
    assert client_vai_tro(VaiTro.KE_TOAN).get(f"/anh/thanh-toan/{tt.pk}/").status_code == 200


def test_nfr06_sua_hang_muc_sau_khi_duyet_gia_ghi_truoc_sau_va_canh_bao_vuot_10(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don, don_gia="500000")
    c.post(f"/tho/don/{don.ma_don}/bao-gia/", {"hanh_dong": "dong_y", "nguoi_xac_nhan": "A"})
    hm = _don(don).ds_hang_muc.get()
    phan_hoi = c.post(
        f"/tho/don/{don.ma_don}/hoan-thanh/",
        {"hanh_dong": "sua", "hang_muc": hm.pk, "so_luong": "1", "don_gia": "600000"},
        follow=True,
    )
    assert "vượt báo giá đã duyệt hơn 10%" in phan_hoi.content.decode()
    nk = NhatKyThaoTac.objects.get(hanh_dong="SUA_HANG_MUC")
    assert nk.nguoi_dung == c.tho.nguoi_dung
    assert nk.du_lieu_truoc["don_gia_thuc_te"] == 500_000 and nk.du_lieu_truoc["sau_bao_gia_da_duyet"] is True
    assert nk.du_lieu_sau["don_gia_thuc_te"] == 600_000


def test_tang_duoi_10_phan_tram_khong_canh_bao(sua_chua):
    don, c = sua_chua
    _den_noi(c, don)
    _them_cong(c, don, don_gia="500000")
    c.post(f"/tho/don/{don.ma_don}/bao-gia/", {"hanh_dong": "dong_y", "nguoi_xac_nhan": "A"})
    hm = _don(don).ds_hang_muc.get()
    phan_hoi = c.post(
        f"/tho/don/{don.ma_don}/hoan-thanh/",
        {"hanh_dong": "sua", "hang_muc": hm.pk, "so_luong": "1", "don_gia": "550000"},
        follow=True,
    )
    assert "vượt báo giá" not in phan_hoi.content.decode()


# ============================================================== BR05 — bảo hành


def test_br05_bao_hanh_het_han_dung_ngay(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    _tai_anh(c, don)
    _hoan_thanh(c, don)
    phieu = PhieuBaoHanh.objects.get(don=don)
    assert phieu.ngay_bat_dau == timezone.localdate()
    assert phieu.ngay_het_han == phieu.ngay_bat_dau + timedelta(days=7)
    het_han = phieu.ngay_het_han
    with freeze_time(f"{het_han:%Y-%m-%d} 23:59:00+07:00"):
        assert phieu.con_han and _don(don).con_han_bao_hanh
    with freeze_time(
        f"{het_han + timedelta(days=1):%Y-%m-%d} 00:00:30+07:00"
    ):  # UTC vẫn là ngày cũ — tính giờ VN
        assert not phieu.con_han and not _don(don).con_han_bao_hanh


def test_br05_thoi_han_lay_lon_nhat_cac_dich_vu_trong_don(ve_sinh):
    don, c = ve_sinh
    _den_noi(c, don)
    sua = DichVuFactory(nhom_dich_vu=SC, thoi_han_bao_hanh_ngay=90)
    c.post(
        f"/tho/don/{don.ma_don}/hoan-thanh/",
        {"hanh_dong": "them_dich_vu", "dich_vu": sua.pk, "so_luong": "1"},
    )
    _tai_anh(c, don)
    _hoan_thanh(c, don)
    phieu = PhieuBaoHanh.objects.get(don=don)
    assert (phieu.ngay_het_han - phieu.ngay_bat_dau).days == 90 and "90 ngày" in phieu.dieu_kien


def test_br05_don_bao_hanh_tong_phai_thu_bang_0(client):
    goc = tao_don("HOAN_THANH")
    don, tho, _ = don_tho_da_nhan(VS, loai_don="BAO_HANH", don_goc=goc, nguyen_nhan_bao_hanh="TAY_NGHE")
    client.force_login(tho.nguoi_dung)
    _den_noi(client, don)
    _them_vat_tu(client, don, trang="hoan-thanh", mo_ta="Ống thoát nước")
    assert dict(HangMucSuaChua.objects.filter(don=don).values_list("loai", "ben_chiu_chi_phi")) == {
        "CONG": "THO",  # lỗi tay nghề: thợ chịu công
        "VAT_TU": "CONG_TY",
    }
    _tai_anh(client, don)
    _hoan_thanh(client, don, so_tien="0")
    d = _don(don)
    assert (d.trang_thai, d.tong_tien_phai_thu) == ("HOAN_THANH", 0)
    assert ThanhToan.objects.get(don=don).trang_thai == "KHONG_CAN_NOP"
    assert not PhieuBaoHanh.objects.filter(don=don).exists()  # không gia hạn bảo hành (A-25)


# ============================================================== quyền thao tác hiện trường


def test_tho_khac_khong_thao_tac_duoc(ve_sinh, client):
    don, c = ve_sinh
    _den_noi(c, don)
    khac, tho_khac, _ = don_tho_da_nhan(VS)
    client.force_login(tho_khac.nguoi_dung)
    for url in ("den-noi/", "bao-gia/", "hoan-thanh/"):
        assert client.post(f"/tho/don/{don.ma_don}/{url}", {"hanh_dong": "hoan_thanh"}).status_code == 404
    assert _don(don).trang_thai == "DANG_SUA"


def test_tong_dai_khong_hoan_thanh_thay_tho(ve_sinh, client_vai_tro):
    from django.core.exceptions import PermissionDenied

    from apps.thuc_hien.dao import DonSuaChuaDAO

    don, c = ve_sinh
    _den_noi(c, don)
    td = client_vai_tro(VaiTro.TONG_DAI)
    assert td.post(f"/tho/don/{don.ma_don}/hoan-thanh/", {"hanh_dong": "hoan_thanh"}).status_code == 403
    with pytest.raises(PermissionDenied):
        DonSuaChuaDAO.hoan_thanh(td.nguoi_dung, _don(don), 150_000, "TIEN_MAT")


def test_quan_tri_duoc_sua_bao_gia(sua_chua, quan_tri):
    don, c = sua_chua
    _den_noi(c, don)
    HienTruongDAO.them_hang_muc(
        quan_tri, _don(don), {"loai": "PHI_KHAC", "mo_ta": "Phí đi lại", "don_gia_thuc_te": 30000}
    )
    assert HangMucSuaChua.objects.filter(don=don, loai="PHI_KHAC").exists()


# ============================================================== BR07 — khách VIP


def test_br07_khach_3_don_hoan_thanh_trong_365_ngay_thanh_vip():
    from apps.don_sua_chua.tac_vu import cap_nhat_khach_vip

    kh = KhachHangFactory()
    from tests.conftest import DiaChiFactory

    dc = DiaChiFactory(khach_hang=kh)
    for tt in ("HOAN_THANH", "DA_DONG"):
        tao_don(tt, dia_chi=dc)
    tao_don("DA_HUY", dia_chi=dc)  # đơn hủy không tính
    cu = tao_don("HOAN_THANH", dia_chi=dc)
    DonSuaChua.objects.filter(pk=cu.pk).update(
        ngay_tiep_nhan=timezone.now() - timedelta(days=400)
    )  # quá 365 ngày
    assert kh.so_lan_su_dung_trong_nam == 2
    assert cap_nhat_khach_vip() == {"len_vip": 0, "ve_thuong": 0}
    tao_don("DANG_BAO_HANH", dia_chi=dc)
    assert cap_nhat_khach_vip() == {"len_vip": 1, "ve_thuong": 0}
    kh.refresh_from_db()
    assert kh.la_vip
    assert NhatKyThaoTac.objects.filter(hanh_dong="CAP_NHAT_VIP", nguoi_dung=None).exists()
    assert cap_nhat_khach_vip() == {"len_vip": 0, "ve_thuong": 0}  # lũy đẳng
    # một năm sau không còn đủ đơn → về thường; khách VIP thủ công giữ nguyên
    thu_cong = KhachHangFactory(vip_thu_cong=True, ly_do_vip="GĐ", loai_khach="THUONG")
    with freeze_time(timezone.now() + timedelta(days=366)):
        assert cap_nhat_khach_vip() == {"len_vip": 1, "ve_thuong": 1}
    kh.refresh_from_db()
    thu_cong.refresh_from_db()
    assert not kh.la_vip and thu_cong.la_vip


@pytest.mark.parametrize(("pham_vi", "tong"), [("TIEN_CONG", 470_000), ("CONG_VA_VAT_TU", 450_000)])
def test_br07_giam_vip_dung_pham_vi_cau_hinh(pham_vi, tong):
    CauHinh.objects.filter(khoa="VIP_PHAM_VI_GIAM").update(gia_tri=pham_vi)
    kh = KhachHang.objects.create(
        so_dien_thoai="0933000111", loai_khach="VIP", vip_thu_cong=True, ly_do_vip="GĐ"
    )
    from tests.conftest import DiaChiFactory

    don = tao_don("DANG_SUA", dia_chi=DiaChiFactory(khach_hang=kh))
    HangMucSuaChua.objects.create(don=don, loai="CONG", mo_ta="Công", so_luong=1, don_gia_thuc_te=300_000)
    HangMucSuaChua.objects.create(don=don, loai="VAT_TU", mo_ta="Vật tư", so_luong=1, don_gia_thuc_te=200_000)
    assert _don(don).tong_tien == tong


def test_br07_lich_tac_vu_hang_ngay():
    from django_q.models import Schedule

    lich = Schedule.objects.get(name="cap_nhat_khach_vip")
    assert (
        lich.schedule_type == Schedule.DAILY
        and timezone.localtime(lich.next_run).strftime("%H:%M") == "01:00"
    )
