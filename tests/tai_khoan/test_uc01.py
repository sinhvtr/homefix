"""UC01 — đăng nhập và phân quyền: khóa sau 5 lần sai, PIN thợ, đổi lần đầu, ghi nhớ 30 ngày, quản lý tài khoản."""

from datetime import timedelta

import pytest
from django.contrib.messages import get_messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from freezegun import freeze_time

from apps.danh_muc.dao import ThoDAO
from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.dao import NguoiDungDAO
from apps.tai_khoan.mat_khau import kiem_tra_pin, sinh_pin
from apps.tai_khoan.models import NguoiDung, VaiTro
from tests.conftest import MAT_KHAU_THU

pytestmark = pytest.mark.django_db


def _dang_nhap(client, ten, mat_khau):
    return client.post("/dang-nhap/", {"username": ten, "password": mat_khau})


def _da_dang_nhap(client) -> bool:
    return "_auth_user_id" in client.session


# ------------------------------------------------------------ Khóa 15 phút sau 5 lần sai liên tiếp


def test_khoa_sau_5_lan_sai_lien_tiep(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    for _ in range(5):
        _dang_nhap(client, "0912345678", "sai")
    phan_hoi = _dang_nhap(client, "0912345678", MAT_KHAU_THU)  # đúng mật khẩu nhưng đang bị khóa
    assert phan_hoi.status_code == 429
    assert "Tạm khóa đăng nhập" in phan_hoi.content.decode()
    assert not _da_dang_nhap(client)


def test_4_lan_sai_chua_khoa(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    for _ in range(4):
        _dang_nhap(client, "0912345678", "sai")
    _dang_nhap(client, "0912345678", MAT_KHAU_THU)
    assert _da_dang_nhap(client)


def test_het_khoa_sau_15_phut(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    with freeze_time(timezone.now()) as dong_ho:
        for _ in range(5):
            _dang_nhap(client, "0912345678", "sai")
        dong_ho.tick(timedelta(minutes=15, seconds=1))
        _dang_nhap(client, "0912345678", MAT_KHAU_THU)
        assert _da_dang_nhap(client)


def test_thu_lai_khi_dang_khoa_tinh_lai_15_phut(client, tao_nguoi_dung):
    """A-34: thời gian khóa tính từ lần thử cuối — thử lại khi đang khóa thì chờ thêm 15 phút."""
    tao_nguoi_dung(so_dien_thoai="0912345678")
    with freeze_time(timezone.now()) as dong_ho:
        for _ in range(5):
            _dang_nhap(client, "0912345678", "sai")
        dong_ho.tick(timedelta(minutes=14))
        assert _dang_nhap(client, "0912345678", MAT_KHAU_THU).status_code == 429
        dong_ho.tick(timedelta(minutes=2))
        assert _dang_nhap(client, "0912345678", MAT_KHAU_THU).status_code == 429
        dong_ho.tick(timedelta(minutes=15, seconds=1))
        _dang_nhap(client, "0912345678", MAT_KHAU_THU)
        assert _da_dang_nhap(client)


def test_cac_cach_go_sdt_tinh_chung_mot_bo_dem(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    for ten in ["0912345678", "+84912345678", "0912.345.678", "+84 912 345 678", "84912345678"]:
        _dang_nhap(client, ten, "sai")
    assert _dang_nhap(client, "0912345678", MAT_KHAU_THU).status_code == 429


def test_dang_nhap_dung_dat_lai_bo_dem(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    for _ in range(4):
        _dang_nhap(client, "0912345678", "sai")
    _dang_nhap(client, "0912345678", MAT_KHAU_THU)
    client.post("/dang-xuat/")
    for _ in range(4):
        _dang_nhap(client, "0912345678", "sai")
    _dang_nhap(client, "0912345678", MAT_KHAU_THU)
    assert _da_dang_nhap(client)


def test_khoa_mot_tai_khoan_khong_anh_huong_tai_khoan_khac(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    tao_nguoi_dung(so_dien_thoai="0987654321")
    for _ in range(5):
        _dang_nhap(client, "0912345678", "sai")
    _dang_nhap(client, "0987654321", MAT_KHAU_THU)
    assert _da_dang_nhap(client)


# ------------------------------------------------------------ PIN thợ, bắt buộc đổi lần đầu


@pytest.mark.parametrize("pin", ["12345", "1234567", "12a456", "111111", "123456", "654321", "345678", ""])
def test_pin_khong_hop_le(pin):
    with pytest.raises(ValidationError):
        kiem_tra_pin(pin)


def test_sinh_pin_luon_hop_le():
    for _ in range(300):
        kiem_tra_pin(sinh_pin())


@pytest.fixture
def tho_moi(quan_tri):
    tho, pin = ThoDAO.tao(
        quan_tri, {"ho_ten": "Thợ Mới", "so_dien_thoai": "0977 111 222", "hinh_thuc": "CONG_TAC_VIEN"}
    )
    return tho, pin


def test_tho_dang_nhap_bang_sdt_va_pin_phai_doi_pin_lan_dau(client, tho_moi):
    tho, pin = tho_moi
    assert tho.nguoi_dung.username == "0977111222" and tho.nguoi_dung.phai_doi_mat_khau
    _dang_nhap(client, "+84 977 111 222", pin)
    assert _da_dang_nhap(client)
    # Mọi trang đều bị đưa về đổi PIN
    for url in ["/tho/", "/danh-muc/dich-vu/", "/"]:
        phan_hoi = client.get(url)
        assert phan_hoi.status_code == 302 and phan_hoi.url == "/doi-mat-khau/"
    assert "Đổi mã PIN" in client.get("/doi-mat-khau/").content.decode()


@pytest.mark.parametrize("pin_moi", ["12345", "111111", "123456", "abcdef"])
def test_tho_doi_pin_yeu_bi_tu_choi(client, tho_moi, pin_moi):
    tho, pin = tho_moi
    _dang_nhap(client, "0977111222", pin)
    phan_hoi = client.post(
        "/doi-mat-khau/", {"mat_khau_cu": pin, "mat_khau_moi": pin_moi, "nhap_lai": pin_moi}
    )
    assert phan_hoi.status_code == 200
    tho.nguoi_dung.refresh_from_db()
    assert tho.nguoi_dung.phai_doi_mat_khau


def test_tho_doi_pin_thanh_cong(client, tho_moi):
    tho, pin = tho_moi
    _dang_nhap(client, "0977111222", pin)
    phan_hoi = client.post(
        "/doi-mat-khau/", {"mat_khau_cu": pin, "mat_khau_moi": "482915", "nhap_lai": "482915"}
    )
    assert phan_hoi.status_code == 302
    assert _da_dang_nhap(client)  # vẫn giữ phiên sau khi đổi
    assert client.get("/tho/").status_code == 200
    tho.nguoi_dung.refresh_from_db()
    assert not tho.nguoi_dung.phai_doi_mat_khau
    assert tho.nguoi_dung.check_password("482915")
    assert NhatKyThaoTac.objects.filter(hanh_dong="DOI_MAT_KHAU", nguoi_dung=tho.nguoi_dung).exists()


def test_doi_mat_khau_sai_mat_khau_cu(client, tho_moi):
    tho, pin = tho_moi
    _dang_nhap(client, "0977111222", pin)
    phan_hoi = client.post(
        "/doi-mat-khau/", {"mat_khau_cu": "000001", "mat_khau_moi": "482915", "nhap_lai": "482915"}
    )
    assert "không đúng" in phan_hoi.content.decode()


def test_tho_duoc_ghi_nho_dang_nhap_30_ngay(client, tho_moi):
    _, pin = tho_moi
    _dang_nhap(client, "0977111222", pin)
    assert client.session.get_expiry_age() == 30 * 24 * 3600


def test_van_phong_khong_ghi_nho_30_ngay(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678", vai_tro=VaiTro.TONG_DAI)
    _dang_nhap(client, "0912345678", MAT_KHAU_THU)
    assert client.session.get_expiry_age() < 30 * 24 * 3600


def test_tho_khong_vao_duoc_trang_tong_dai(client_vai_tro):
    assert client_vai_tro(VaiTro.THO).get("/tong-dai/").status_code == 403


# ------------------------------------------------------------ Quản lý người dùng (quản trị)


def test_quan_tri_tao_nguoi_dung_mat_khau_tam_hien_mot_lan(client_quan_tri, client):
    phan_hoi = client_quan_tri.post(
        "/quan-tri/nguoi-dung/moi/",
        {"ho_ten": "Kế Toán Mới", "so_dien_thoai": "0966 000 111", "vai_tro": VaiTro.KE_TOAN},
        follow=True,
    )
    thong_diep = [str(m) for m in get_messages(phan_hoi.wsgi_request)] or [phan_hoi.content.decode()]
    nguoi = NguoiDung.objects.get(so_dien_thoai="0966000111")
    assert nguoi.vai_tro == VaiTro.KE_TOAN and nguoi.phai_doi_mat_khau
    noi_dung = phan_hoi.content.decode()
    assert "chỉ hiện một lần" in noi_dung or any("chỉ hiện một lần" in t for t in thong_diep)
    assert NhatKyThaoTac.objects.filter(
        hanh_dong="TAO_NGUOI_DUNG", doi_tuong=f"NguoiDung:{nguoi.pk}"
    ).exists()


def test_khong_tao_tho_o_man_hinh_nguoi_dung(client_quan_tri):
    phan_hoi = client_quan_tri.post(
        "/quan-tri/nguoi-dung/moi/", {"ho_ten": "A", "so_dien_thoai": "0966000111", "vai_tro": VaiTro.THO}
    )
    assert phan_hoi.status_code == 200
    assert not NguoiDung.objects.filter(so_dien_thoai="0966000111").exists()


def test_tao_nguoi_dung_trung_sdt_bao_loi_duoi_o(client_quan_tri, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0966000111")
    phan_hoi = client_quan_tri.post(
        "/quan-tri/nguoi-dung/moi/",
        {"ho_ten": "B", "so_dien_thoai": "+84966000111", "vai_tro": VaiTro.TONG_DAI},
    )
    assert phan_hoi.status_code == 200
    assert "đã có tài khoản" in phan_hoi.content.decode()


def test_sua_nguoi_dung_ghi_nhat_ky(client_quan_tri, tao_nguoi_dung):
    nguoi = tao_nguoi_dung(vai_tro=VaiTro.TONG_DAI)
    client_quan_tri.post(
        f"/quan-tri/nguoi-dung/{nguoi.pk}/sua/",
        {"ho_ten": "Tên Mới", "so_dien_thoai": nguoi.so_dien_thoai, "vai_tro": VaiTro.KE_TOAN},
    )
    nguoi.refresh_from_db()
    assert (nguoi.ho_ten, nguoi.vai_tro) == ("Tên Mới", VaiTro.KE_TOAN)
    nk = NhatKyThaoTac.objects.get(hanh_dong="SUA_NGUOI_DUNG")
    assert nk.du_lieu_truoc["vai_tro"] == VaiTro.TONG_DAI and nk.du_lieu_sau["vai_tro"] == VaiTro.KE_TOAN


def test_khoa_va_mo_khoa_tai_khoan(client_quan_tri, client, tao_nguoi_dung):
    nguoi = tao_nguoi_dung(so_dien_thoai="0966000222")
    client_quan_tri.post(f"/quan-tri/nguoi-dung/{nguoi.pk}/khoa/")
    nguoi.refresh_from_db()
    assert not nguoi.is_active
    client_quan_tri.post(f"/quan-tri/nguoi-dung/{nguoi.pk}/khoa/")
    nguoi.refresh_from_db()
    assert nguoi.is_active
    assert NhatKyThaoTac.objects.filter(hanh_dong="KHOA_TAI_KHOAN").count() == 1


def test_khong_tu_khoa_chinh_minh(quan_tri):
    with pytest.raises(ValidationError):
        NguoiDungDAO.dat_khoa(quan_tri, quan_tri, khoa=True)


def test_dat_lai_mat_khau_bat_doi_lai(quan_tri, tao_nguoi_dung):
    nguoi = tao_nguoi_dung(vai_tro=VaiTro.KE_TOAN)
    mat_khau = NguoiDungDAO.dat_lai_mat_khau(quan_tri, nguoi)
    nguoi.refresh_from_db()
    assert nguoi.phai_doi_mat_khau and nguoi.check_password(mat_khau)


def test_dao_tu_choi_vai_tro_khong_du_quyen(tong_dai, tao_nguoi_dung):
    """Kiểm tra quyền ở DAO, không chỉ ở view (SPEC 3.1)."""
    with pytest.raises(PermissionDenied):
        NguoiDungDAO.tao_nguoi_dung(tong_dai, "X", "0966000333", VaiTro.TONG_DAI)
    with pytest.raises(PermissionDenied):
        NguoiDungDAO.dat_lai_mat_khau(tong_dai, tao_nguoi_dung())


# ------------------------------------------------------------ Cấu hình


def test_sua_cau_hinh_ghi_nhat_ky_va_co_hieu_luc(client_quan_tri):
    from apps.he_thong.cau_hinh import cau_hinh
    from apps.he_thong.models import CauHinh

    ch = CauHinh.objects.get(khoa="THOI_HAN_PHAN_HOI_PHUT")
    client_quan_tri.post(f"/quan-tri/cau-hinh/{ch.pk}/sua/", {"gia_tri": "20"})
    assert cau_hinh("THOI_HAN_PHAN_HOI_PHUT") == 20
    nk = NhatKyThaoTac.objects.get(hanh_dong="SUA_CAU_HINH")
    assert nk.du_lieu_truoc == {"gia_tri": "15"} and nk.du_lieu_sau == {"gia_tri": "20"}


def test_sua_cau_hinh_sai_kieu_bao_loi(client_quan_tri):
    from apps.he_thong.models import CauHinh

    ch = CauHinh.objects.get(khoa="THOI_HAN_PHAN_HOI_PHUT")
    phan_hoi = client_quan_tri.post(f"/quan-tri/cau-hinh/{ch.pk}/sua/", {"gia_tri": "mười lăm"})
    assert phan_hoi.status_code == 200 and "không đúng kiểu" in phan_hoi.content.decode()
    ch.refresh_from_db()
    assert ch.gia_tri == "15"
