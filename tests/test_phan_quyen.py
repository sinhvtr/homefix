"""Kiểm thử phân quyền MỌI URL theo ma trận SPEC 3.1 (tham số hóa: URL × vai trò). NFR04."""

import pytest

from apps.he_thong.models import CauHinh
from apps.tai_khoan.models import VaiTro
from tests.conftest import DichVuFactory, NguoiDungFactory, ThietBiFactory, ThoFactory, tao_don

pytestmark = pytest.mark.django_db

QT, TD, THO, KT, GD = VaiTro.QUAN_TRI, VaiTro.TONG_DAI, VaiTro.THO, VaiTro.KE_TOAN, VaiTro.GIAM_DOC
MOI = {QT, TD, THO, KT, GD}
VAN_PHONG = {QT, TD, KT, GD}

# (phương thức, mẫu URL, vai trò được phép)
MA_TRAN = [
    # Trang đích theo vai trò (UC01)
    ("GET", "/tong-dai/", {QT, TD, GD}),
    ("GET", "/tho/", {THO}),
    ("GET", "/ke-toan/doi-soat/", {QT, KT, GD}),
    ("GET", "/bao-cao/", {QT, KT, GD}),
    ("GET", "/doi-mat-khau/", MOI),
    # Người dùng, cấu hình hệ thống: QT CRUD, GĐ R
    ("GET", "/quan-tri/nguoi-dung/", {QT, GD}),
    ("GET", "/quan-tri/nguoi-dung/moi/", {QT}),
    ("GET", "/quan-tri/nguoi-dung/{nd}/sua/", {QT}),
    ("POST", "/quan-tri/nguoi-dung/{nd}/khoa/", {QT}),
    ("POST", "/quan-tri/nguoi-dung/{nd}/dat-lai-mat-khau/", {QT}),
    ("GET", "/quan-tri/cau-hinh/", {QT, GD}),
    ("GET", "/quan-tri/cau-hinh/{ch}/sua/", {QT}),
    # Danh mục khu vực: QT CRUD; TĐ, KT, GĐ R
    ("GET", "/danh-muc/khu-vuc/", VAN_PHONG),
    ("GET", "/danh-muc/khu-vuc/moi/", {QT}),
    ("GET", "/danh-muc/khu-vuc/{kv}/sua/", {QT}),
    ("POST", "/danh-muc/khu-vuc/{kv}/xoa/", {QT}),
    # Dịch vụ, bảng giá: QT CRUD; mọi vai trò khác R (thợ xem dịch vụ)
    ("GET", "/danh-muc/dich-vu/", MOI),
    ("GET", "/danh-muc/dich-vu/moi/", {QT}),
    ("GET", "/danh-muc/dich-vu/{dv}/sua/", {QT}),
    ("POST", "/danh-muc/dich-vu/{dv}/xoa/", {QT}),
    ("GET", "/danh-muc/dich-vu/nhap/", {QT}),
    ("GET", "/danh-muc/dich-vu/mau.xlsx", {QT}),
    # Hồ sơ thợ: QT CRUD; TĐ, KT, GĐ R
    ("GET", "/danh-muc/tho/", VAN_PHONG),
    ("GET", "/danh-muc/tho/{tho}/", VAN_PHONG),
    ("GET", "/danh-muc/tho/moi/", {QT}),
    ("GET", "/danh-muc/tho/{tho}/sua/", {QT}),
    ("POST", "/danh-muc/tho/{tho}/cap-pin/", {QT}),
    ("POST", "/danh-muc/tho/{tho}/khoa/", {QT}),
    ("GET", "/danh-muc/tho/nhap/", {QT}),
    ("GET", "/danh-muc/tho/mau.xlsx", {QT}),
    # Khách hàng, địa chỉ, thiết bị: QT CRUD; TĐ CRU; KT, GĐ R; thợ — (chỉ khách của đơn đã nhận, P3)
    ("GET", "/danh-muc/khach-hang/", VAN_PHONG),
    ("GET", "/danh-muc/khach-hang/{kh}/", VAN_PHONG),
    ("GET", "/danh-muc/khach-hang/moi/", {QT, TD}),
    ("GET", "/danh-muc/khach-hang/{kh}/sua/", {QT, TD}),
    ("POST", "/danh-muc/khach-hang/{kh}/xoa/", {QT}),
    ("GET", "/danh-muc/khach-hang/{kh}/dia-chi/moi/", {QT, TD}),
    ("GET", "/danh-muc/dia-chi/{dc}/sua/", {QT, TD}),
    ("POST", "/danh-muc/dia-chi/{dc}/xoa/", {QT}),
    ("GET", "/danh-muc/dia-chi/{dc}/thiet-bi/moi/", {QT, TD}),
    ("GET", "/danh-muc/thiet-bi/{tb}/sua/", {QT, TD}),
    ("POST", "/danh-muc/thiet-bi/{tb}/xoa/", {QT}),
    # Đơn sửa chữa (P2): QT, TĐ CRU + hủy; KT, GĐ R; thợ chỉ đơn được giao (trang thợ riêng, P3)
    ("GET", "/don/moi/", {QT, TD}),
    ("GET", "/khach-hang/tra-cuu/?sdt=0912345678", {QT, TD}),
    ("GET", "/don/{ma}/", VAN_PHONG),
    ("POST", "/don/{ma}/chot-lich/", {QT, TD}),
    ("POST", "/don/{ma}/doi-hen/", {QT, TD}),
    ("POST", "/don/{ma}/khach-chua-tra-loi/", {QT, TD}),
    ("POST", "/don/{ma}/giuc/", {QT, TD}),
    ("GET", "/don/{ma}/huy/", {QT, TD}),
    # Phân công, cử thợ (P3): QT, TĐ CRU; GĐ R; KT —; thợ chỉ nhận/từ chối đề nghị của mình (kiểm thử riêng)
    ("GET", "/don/{ma}/cu-tho/", {QT, TD, GD}),
    ("POST", "/don/{ma}/cu-tho/", {QT, TD}),
    ("GET", "/tho-lich/", {QT, TD, GD}),
    # Báo giá (P4): tổng đài xác nhận giá vượt ngưỡng (T12). Trang báo giá/hoàn thành của thợ: kiểm thử riêng (404)
    ("POST", "/don/{ma}/xac-nhan-gia/", {QT, TD}),
    # Màn hình thợ (PWA)
    ("GET", "/tho/cai-dat/", {THO}),
    ("POST", "/tho/san-sang/", {THO}),
    ("POST", "/tho/cai-dat/gui-thu/", {THO}),
    # Thông báo của chính mình
    ("GET", "/thong-bao/", MOI),
]

CHU_THE = [None, QT, TD, THO, KT, GD]  # None = chưa đăng nhập


@pytest.fixture
def doi_tuong():
    tb = ThietBiFactory()
    return {
        "nd": NguoiDungFactory(vai_tro=KT).pk,
        "ch": CauHinh.objects.get(khoa="DEM_DI_CHUYEN_PHUT").pk,
        "kv": tb.dia_chi.khu_vuc.pk,
        "dv": DichVuFactory().pk,
        "tho": ThoFactory().pk,
        "kh": tb.dia_chi.khach_hang.pk,
        "dc": tb.dia_chi.pk,
        "tb": tb.pk,
        "ma": tao_don(dia_chi=tb.dia_chi).ma_don,
    }


def _ten(tham_so):
    if isinstance(tham_so, tuple):
        return f"{tham_so[0]} {tham_so[1]}"
    return tham_so or "an_danh"


@pytest.mark.parametrize("chu_the", CHU_THE, ids=_ten)
@pytest.mark.parametrize(
    ("phuong_thuc", "mau_url", "duoc_phep"), MA_TRAN, ids=[f"{m} {u}" for m, u, _ in MA_TRAN]
)
def test_phan_quyen_moi_url(client_vai_tro, client, doi_tuong, chu_the, phuong_thuc, mau_url, duoc_phep):
    url = mau_url.format(**doi_tuong)
    c = client_vai_tro(chu_the) if chu_the else client
    phan_hoi = c.get(url) if phuong_thuc == "GET" else c.post(url)
    if chu_the is None:
        assert phan_hoi.status_code == 302
        assert phan_hoi.url.startswith("/dang-nhap/")
    elif chu_the in duoc_phep:
        assert phan_hoi.status_code == (200 if phuong_thuc == "GET" else 302), phan_hoi.content[:300]
    else:
        assert phan_hoi.status_code == 403


def test_trang_403_tieng_viet(client_vai_tro, settings):
    settings.DEBUG = False
    phan_hoi = client_vai_tro(THO).get("/tong-dai/")
    assert phan_hoi.status_code == 403
    assert "Không có quyền truy cập" in phan_hoi.content.decode()


def test_menu_chi_hien_muc_duoc_xem(client_vai_tro):
    noi_dung = client_vai_tro(KT).get("/ke-toan/doi-soat/").content.decode()
    assert "/danh-muc/khach-hang/" in noi_dung
    assert "/quan-tri/nguoi-dung/" not in noi_dung
    assert "/don/moi/" not in noi_dung


def test_tai_khoan_bi_khoa_mat_quyen_ngay(client_vai_tro):
    c = client_vai_tro(TD)
    c.nguoi_dung.is_active = False
    c.nguoi_dung.save()
    assert c.get("/danh-muc/khach-hang/").status_code == 302  # phiên hết hiệu lực → về đăng nhập
