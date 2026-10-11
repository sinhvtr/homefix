"""UC11 — đơn bảo hành / làm lại: chặn khi hết hạn; T16/T17; nguyên nhân → bên chịu; khách trả 0 đ; BR05."""

from datetime import date, timedelta

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from freezegun import freeze_time

from apps.bao_hanh.dao import BaoHanhDAO
from apps.bao_hanh.models import PhieuBaoHanh
from apps.don_sua_chua.dao import DonSuaChuaDAO
from apps.don_sua_chua.models import DonSuaChua, HangMucSuaChua
from apps.don_sua_chua.trang_thai import ChuyenTrangThaiKhongHopLe
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_chinh.models import ThanhToan
from apps.tai_khoan.models import VaiTro
from apps.tiep_nhan_dieu_phoi.dao import PhanCongDAO, ThoDAO
from apps.tiep_nhan_dieu_phoi.models import LichHen
from tests.conftest import NguoiDungFactory, ThoFactory, don_hoan_thanh, tao_tho_phu_hop

pytestmark = pytest.mark.django_db
VS, SC = "VE_SINH_BAO_DUONG", "SUA_CHUA_THAY_VAT_TU"
NGAY_HEN = date(2099, 7, 1)


def _lay(don):
    return DonSuaChua.objects.get(pk=don.pk)


@pytest.fixture
def goc():
    """Đơn sửa chữa đã hoàn thành (phiếu 90 ngày), có vật tư — làm đơn gốc."""
    don, tho, tong_dai = don_hoan_thanh(SC, don_gia=400_000)
    don.tong_dai, don.tho_lam = tong_dai, tho
    return don


def _tao_bh(goc, nguoi=None, **kw):
    return BaoHanhDAO.tao_don_bao_hanh(
        nguoi or goc.tong_dai, goc, mo_ta_su_co=kw.pop("mo_ta", "Máy lại chảy nước"), **kw
    )


# ============================================================== tạo đơn bảo hành — T16


def test_uc11_tao_don_bao_hanh_cung_khach_dia_chi_dich_vu_va_t16(goc):
    bh = _tao_bh(goc, ngay_hen=NGAY_HEN, khung_gio="08:00-10:00")
    bh = _lay(bh)
    assert (bh.loai_don, bh.don_goc_id, bh.nguyen_nhan_bao_hanh) == ("BAO_HANH", goc.pk, "CHUA_XAC_DINH")
    assert (bh.khach_hang_id, bh.dia_chi_id, bh.dich_vu_yeu_cau_id) == (
        goc.khach_hang_id,
        goc.dia_chi_id,
        goc.dich_vu_yeu_cau_id,
    )
    assert set(bh.thiet_bi.all()) == set(goc.thiet_bi.all())
    assert bh.trang_thai == "CHO_CU_THO" and bh.lich_hieu_luc is not None  # chốt lịch ngay (T2)
    assert _lay(goc).trang_thai == "DANG_BAO_HANH"  # T16
    nk = NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{goc.ma_don}")
    assert nk.filter(hanh_dong="TAO_DON_BAO_HANH", du_lieu_sau__don_bao_hanh=bh.ma_don).exists()
    assert nk.filter(hanh_dong="DOI_TRANG_THAI", du_lieu_sau__chuyen="T16").exists()


def test_uc11_chua_chot_lich_thi_cho_xac_nhan_lich(goc):
    bh = _tao_bh(goc)
    assert _lay(bh).trang_thai == "CHO_XAC_NHAN_LICH"
    assert _lay(goc).trang_thai == "DANG_BAO_HANH"


def test_uc11_chan_khi_phieu_het_han_va_goi_y_don_thuong(goc, client):
    phieu = PhieuBaoHanh.objects.get(don=goc)
    with freeze_time(f"{phieu.ngay_het_han + timedelta(days=1):%Y-%m-%d} 09:00:00+07:00"):
        with pytest.raises(ValidationError, match="hết hạn") as loi:
            _tao_bh(goc)
        assert loi.value.code == "het_han"
        assert not DonSuaChua.objects.filter(don_goc=goc).exists()
        assert _lay(goc).trang_thai == "HOAN_THANH"
        client.force_login(goc.tong_dai)
        noi_dung = client.get(f"/bao-hanh/moi/?don_goc={goc.ma_don}").content.decode()
        assert (
            "đã hết hạn" in noi_dung
            and "Tạo đơn thường" in noi_dung
            and "Tạo đơn bảo hành</button>" not in noi_dung
        )
    # ngày hết hạn vẫn còn hạn cả ngày (giờ Việt Nam)
    with freeze_time(f"{phieu.ngay_het_han:%Y-%m-%d} 23:50:00+07:00"):
        _tao_bh(goc)


def test_uc11_khong_tao_hai_don_bao_hanh_cung_luc(goc):
    bh = _tao_bh(goc)
    with pytest.raises(ValidationError, match=f"đang có đơn bảo hành {bh.ma_don}"):
        _tao_bh(goc)


@pytest.mark.parametrize("trang_thai", ["DA_HUY", "DANG_SUA"])
def test_uc11_don_goc_phai_hoan_thanh(trang_thai):
    from tests.conftest import tao_don

    don = tao_don(trang_thai)
    with pytest.raises(ValidationError):
        BaoHanhDAO.tao_don_bao_hanh(NguoiDungFactory(), don, mo_ta_su_co="x")


def test_uc11_chi_tong_dai_quan_tri_tao_duoc(goc):
    for nguoi in (
        NguoiDungFactory(vai_tro=VaiTro.KE_TOAN),
        NguoiDungFactory(vai_tro=VaiTro.GIAM_DOC),
        ThoFactory().nguoi_dung,
    ):
        with pytest.raises(PermissionDenied):
            _tao_bh(goc, nguoi=nguoi)
    assert _tao_bh(goc, nguoi=NguoiDungFactory(vai_tro=VaiTro.QUAN_TRI)).loai_don == "BAO_HANH"


def test_uc11_bat_buoc_mo_ta(goc):
    with pytest.raises(ValidationError, match="Mô tả"):
        _tao_bh(goc, mo_ta=" ")


# ============================================================== nguyên nhân → bên chịu chi phí (BR05)


def test_br05_nguyen_nhan_quyet_dinh_ben_chiu_va_bat_buoc_truoc_khi_hoan_thanh(goc):
    bh = _tao_bh(goc, ngay_hen=NGAY_HEN, khung_gio="08:00-10:00")
    tho = tao_tho_phu_hop(bh.dich_vu_yeu_cau)
    PhanCongDAO.gui_de_nghi(goc.tong_dai, bh, [tho.pk])
    PhanCongDAO.nhan_viec(tho.nguoi_dung, bh.ds_phan_cong.get().pk)
    from apps.don_sua_chua.dao import HienTruongDAO
    from apps.thuc_hien.dao import DonSuaChuaDAO as HoanThanhDAO
    from tests.conftest import anh_thu

    nd = tho.nguoi_dung
    HienTruongDAO.tho_den_noi(nd, _lay(bh))
    HienTruongDAO.them_hang_muc(nd, bh, {"loai": "CONG", "dich_vu": bh.dich_vu_yeu_cau})
    HienTruongDAO.them_hang_muc(
        nd,
        bh,
        {"loai": "VAT_TU", "mo_ta": "Van", "so_luong": 1, "don_gia_thuc_te": 90_000, "gia_mua": 60_000},
    )
    assert set(bh.ds_hang_muc.values_list("ben_chiu_chi_phi", flat=True)) == {"CONG_TY"}  # chưa xác định
    HienTruongDAO.khach_duyet_gia(nd, _lay(bh), "Chủ nhà")  # tổng 0 đ → T11
    HienTruongDAO.luu_anh(nd, _lay(bh), anh_thu(400, 300))
    with pytest.raises(ChuyenTrangThaiKhongHopLe, match="nguyên nhân"):
        HoanThanhDAO.hoan_thanh(nd, _lay(bh), 0, "TIEN_MAT")
    DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(nd, _lay(bh), "TAY_NGHE")
    assert dict(bh.ds_hang_muc.values_list("loai", "ben_chiu_chi_phi")) == {
        "CONG": "THO",
        "VAT_TU": "CONG_TY",
    }
    DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(goc.tong_dai, _lay(bh), "VAT_TU")  # tổng đài đổi lại
    assert set(bh.ds_hang_muc.values_list("ben_chiu_chi_phi", flat=True)) == {"CONG_TY"}
    assert (
        NhatKyThaoTac.objects.filter(
            hanh_dong="NGUYEN_NHAN_BAO_HANH", doi_tuong=f"DonSuaChua:{bh.ma_don}"
        ).count()
        == 2
    )
    kq = HoanThanhDAO.hoan_thanh(nd, _lay(bh), 0, "TIEN_MAT")
    assert (kq.don.trang_thai, kq.don.tong_tien_phai_thu, kq.thanh_toan.trang_thai) == (
        "HOAN_THANH",
        0,
        "KHONG_CAN_NOP",
    )
    assert kq.phieu_bao_hanh is None  # không gia hạn (A-25)
    assert _lay(goc).trang_thai == "HOAN_THANH"  # T17


def test_br05_nguyen_nhan_chi_cho_don_bao_hanh_va_tho_phu_trach(goc):
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(goc.tong_dai, goc, "TAY_NGHE")
    bh = _tao_bh(goc)
    with pytest.raises(PermissionDenied):  # thợ không phụ trách
        DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(ThoFactory().nguoi_dung, bh, "TAY_NGHE")
    with pytest.raises(ChuyenTrangThaiKhongHopLe):
        DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(goc.tong_dai, bh, "CHUA_XAC_DINH")


# ============================================================== T17 — đơn con kết thúc


def test_uc11_t17_don_bao_hanh_hoan_thanh_tra_don_goc_ve_hoan_thanh(goc):
    bh = _tao_bh(goc, ngay_hen=NGAY_HEN, khung_gio="08:00-10:00")
    assert _lay(goc).trang_thai == "DANG_BAO_HANH"
    tho = tao_tho_phu_hop(bh.dich_vu_yeu_cau)
    PhanCongDAO.gui_de_nghi(goc.tong_dai, bh, [tho.pk])
    PhanCongDAO.nhan_viec(tho.nguoi_dung, bh.ds_phan_cong.get().pk)
    from apps.don_sua_chua.dao import HienTruongDAO
    from apps.thuc_hien.dao import DonSuaChuaDAO as HoanThanhDAO
    from tests.conftest import anh_thu

    nd = tho.nguoi_dung
    HienTruongDAO.tho_den_noi(nd, _lay(bh))
    HienTruongDAO.them_hang_muc(nd, bh, {"loai": "CONG", "dich_vu": bh.dich_vu_yeu_cau})
    HienTruongDAO.khach_duyet_gia(nd, _lay(bh), "")
    DonSuaChuaDAO.xac_dinh_nguyen_nhan_bao_hanh(nd, _lay(bh), "VAT_TU")
    HienTruongDAO.luu_anh(nd, _lay(bh), anh_thu(400, 300))
    HoanThanhDAO.hoan_thanh(nd, _lay(bh), 0, "TIEN_MAT")
    assert _lay(goc).trang_thai == "HOAN_THANH"
    nk = NhatKyThaoTac.objects.get(doi_tuong=f"DonSuaChua:{goc.ma_don}", du_lieu_sau__chuyen="T17")
    assert nk.du_lieu_truoc == {"trang_thai": "DANG_BAO_HANH"} and bh.ma_don in nk.du_lieu_sau["ly_do"]


def test_uc11_t17_khi_huy_don_bao_hanh(goc):
    bh = _tao_bh(goc)
    DonSuaChuaDAO.huy(goc.tong_dai, bh, "Khách tự xử lý được")
    g = _lay(goc)
    assert g.trang_thai == "HOAN_THANH"
    assert NhatKyThaoTac.objects.filter(
        doi_tuong=f"DonSuaChua:{goc.ma_don}", du_lieu_sau__chuyen="T17"
    ).exists()
    # phiếu còn hạn → tạo được đơn bảo hành mới; thời hạn không đổi
    phieu = PhieuBaoHanh.objects.get(don=goc)
    _tao_bh(goc)
    assert PhieuBaoHanh.objects.get(don=goc).ngay_het_han == phieu.ngay_het_han


def test_uc11_t17_khi_tu_dong_huy_br08(goc):
    bh = _tao_bh(goc)
    from apps.don_sua_chua.tac_vu import nhac_xac_nhan_lich

    bay_gio = timezone.now()
    for gio in (25, 50, 75, 100):
        nhac_xac_nhan_lich(bay_gio + timedelta(hours=gio))
    assert _lay(bh).trang_thai == "DA_HUY"
    assert _lay(goc).trang_thai == "HOAN_THANH"


# ============================================================== gợi ý thợ làm đơn gốc, khách trả 0 đ


def test_uc11_goi_y_danh_dau_tho_lam_don_goc(goc):
    bh = _tao_bh(goc, ngay_hen=NGAY_HEN, khung_gio="13:00-15:00")
    ds = ThoDAO.goi_y_tho(_lay(bh))
    assert [g.tho for g in ds if g.la_tho_don_goc] == [goc.tho_lam]


def test_uc11_don_bao_hanh_thu_khach_0_dong(goc):
    bh, tho, _ = don_hoan_thanh(
        VS,
        loai_don="BAO_HANH",
        don_goc=goc,
        nguyen_nhan_bao_hanh="CHUA_XAC_DINH",
        vat_tu=[("Gioăng", 1, 50_000, 30_000, "THO")],
    )
    assert bh.tong_tien_phai_thu == 0
    assert not HangMucSuaChua.objects.filter(don=bh, ben_chiu_chi_phi="KHACH").exists()
    assert ThanhToan.objects.get(don=bh).so_tien == 0


# ============================================================== màn hình


def test_man_hinh_uc11_tu_chi_tiet_don_va_tra_cuu(goc, client):
    client.force_login(goc.tong_dai)
    chi_tiet = client.get(f"/don/{goc.ma_don}/").content.decode()
    assert f"/bao-hanh/moi/?don_goc={goc.ma_don}" in chi_tiet
    tra_cuu = client.get(f"/khach-hang/tra-cuu/?sdt={goc.khach_hang.so_dien_thoai}").content.decode()
    assert f"/bao-hanh/moi/?don_goc={goc.ma_don}" in tra_cuu and "BH đến" in tra_cuu
    phan_hoi = client.post(
        f"/bao-hanh/moi/?don_goc={goc.ma_don}",
        {
            "mo_ta_su_co": "Lại kêu to",
            "kenh_tiep_nhan": "DIEN_THOAI",
            "ngay_hen": "2099-07-02",
            "khung_gio": "10:00-12:00",
        },
    )
    bh = DonSuaChua.objects.get(don_goc=goc)
    assert phan_hoi.status_code == 302 and phan_hoi.url == f"/don/{bh.ma_don}/"
    assert bh.trang_thai == "CHO_CU_THO" and LichHen.objects.filter(don=bh, trang_thai="HIEU_LUC").exists()
    chi_tiet_bh = client.get(f"/don/{bh.ma_don}/").content.decode()
    assert goc.ma_don in chi_tiet_bh and "Xác định nguyên nhân" in chi_tiet_bh
    client.post(f"/don/{bh.ma_don}/nguyen-nhan/", {"nguyen_nhan": "VAT_TU"})
    assert _lay(bh).nguyen_nhan_bao_hanh == "VAT_TU"
    assert "Tạo đơn bảo hành</a>" not in client.get(f"/don/{goc.ma_don}/").content.decode()  # đang bảo hành


def test_man_hinh_uc11_don_goc_khong_ton_tai_404(client):
    client.force_login(NguoiDungFactory(vai_tro=VaiTro.TONG_DAI))
    assert client.get("/bao-hanh/moi/?don_goc=HF990101-001").status_code == 404
    assert client.get("/bao-hanh/moi/").status_code == 404


def test_man_hinh_tho_chon_nguyen_nhan(goc, client):
    bh = _tao_bh(goc, ngay_hen=NGAY_HEN, khung_gio="15:00-17:00")
    tho = tao_tho_phu_hop(bh.dich_vu_yeu_cau)
    PhanCongDAO.gui_de_nghi(goc.tong_dai, bh, [tho.pk])
    PhanCongDAO.nhan_viec(tho.nguoi_dung, bh.ds_phan_cong.get().pk)
    client.force_login(tho.nguoi_dung)
    assert "Lỗi tay nghề" in client.get(f"/tho/don/{bh.ma_don}/").content.decode()
    client.post(f"/tho/don/{bh.ma_don}/nguyen-nhan/", {"nguyen_nhan": "TAY_NGHE"})
    assert _lay(bh).nguyen_nhan_bao_hanh == "TAY_NGHE"
    client.force_login(ThoFactory().nguoi_dung)
    assert client.post(f"/tho/don/{bh.ma_don}/nguyen-nhan/", {"nguyen_nhan": "VAT_TU"}).status_code == 404
