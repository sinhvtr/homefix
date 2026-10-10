import pytest

from apps.tai_khoan.models import VaiTro
from tests.conftest import MAT_KHAU_THU

pytestmark = pytest.mark.django_db


def test_trang_dang_nhap_hien_thi(client):
    phan_hoi = client.get("/dang-nhap/")
    assert phan_hoi.status_code == 200
    noi_dung = phan_hoi.content.decode()
    assert "Số điện thoại hoặc tên đăng nhập" in noi_dung
    assert "Mật khẩu / mã PIN" in noi_dung


@pytest.mark.parametrize("ten_dang_nhap", ["0912345678", "+84 912 345 678", "0912.345.678", "tongdai1"])
def test_dang_nhap_bang_sdt_hoac_ten(client, tao_nguoi_dung, ten_dang_nhap):
    tao_nguoi_dung(username="tongdai1", so_dien_thoai="0912345678")
    phan_hoi = client.post("/dang-nhap/", {"username": ten_dang_nhap, "password": MAT_KHAU_THU})
    assert phan_hoi.status_code == 302
    assert "_auth_user_id" in client.session


def test_dang_nhap_sai_mat_khau(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678")
    phan_hoi = client.post("/dang-nhap/", {"username": "0912345678", "password": "sai"})
    assert phan_hoi.status_code == 200
    assert "không đúng" in phan_hoi.content.decode()
    assert "_auth_user_id" not in client.session


def test_dang_nhap_tai_khoan_khong_ton_tai(client):
    phan_hoi = client.post("/dang-nhap/", {"username": "0900000000", "password": "x"})
    assert phan_hoi.status_code == 200
    assert "_auth_user_id" not in client.session


def test_tai_khoan_bi_khoa_khong_dang_nhap_duoc(client, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0912345678", is_active=False)
    client.post("/dang-nhap/", {"username": "0912345678", "password": MAT_KHAU_THU})
    assert "_auth_user_id" not in client.session


@pytest.mark.parametrize(
    ("vai_tro", "trang_dich"),
    [
        (VaiTro.QUAN_TRI, "/tong-dai/"),
        (VaiTro.TONG_DAI, "/tong-dai/"),
        (VaiTro.THO, "/tho/"),
        (VaiTro.KE_TOAN, "/ke-toan/doi-soat/"),
        (VaiTro.GIAM_DOC, "/bao-cao/"),
    ],
)
def test_chuyen_huong_sau_dang_nhap_theo_vai_tro(client, tao_nguoi_dung, vai_tro, trang_dich):
    tao_nguoi_dung(so_dien_thoai="0912345678", vai_tro=vai_tro)
    phan_hoi = client.post("/dang-nhap/", {"username": "0912345678", "password": MAT_KHAU_THU}, follow=True)
    assert phan_hoi.redirect_chain[-1][0] == trang_dich
    assert phan_hoi.status_code == 200


def test_bo_cuc_tho_va_van_phong(client, tao_nguoi_dung):
    tho = tao_nguoi_dung(vai_tro=VaiTro.THO)
    client.force_login(tho)
    noi_dung = client.get("/tho/").content.decode()
    assert "HomeFix Thợ" in noi_dung and "Điều hướng thợ" in noi_dung

    tong_dai = tao_nguoi_dung(vai_tro=VaiTro.TONG_DAI)
    client.force_login(tong_dai)
    noi_dung = client.get("/tong-dai/").content.decode()
    assert 'aria-label="Chức năng"' in noi_dung and "Tạo đơn mới" in noi_dung


def test_chua_dang_nhap_bi_chuyen_ve_dang_nhap(client):
    phan_hoi = client.get("/tong-dai/")
    assert phan_hoi.status_code == 302
    assert phan_hoi.url.startswith("/dang-nhap/")


def test_dang_xuat(client, tao_nguoi_dung):
    client.force_login(tao_nguoi_dung())
    phan_hoi = client.post("/dang-xuat/")
    assert phan_hoi.status_code == 302
    assert "_auth_user_id" not in client.session
