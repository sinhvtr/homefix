import pytest
from django.core.management import CommandError, call_command

from apps.he_thong.models import NhatKyThaoTac
from apps.tai_khoan.models import NguoiDung, VaiTro

pytestmark = pytest.mark.django_db

MAT_KHAU = "Quan-tri-an-toan-2026"


def test_tao_quan_tri_khong_hoi(monkeypatch, client):
    monkeypatch.setenv("HOMEFIX_MAT_KHAU_QUAN_TRI", MAT_KHAU)
    call_command("tao_quan_tri", "--no-input", "--ho-ten", "Trần Thị Tổ Trưởng", "--sdt", "+84 988 111 222")
    nguoi = NguoiDung.objects.get(so_dien_thoai="0988111222")
    assert nguoi.vai_tro == VaiTro.QUAN_TRI
    assert nguoi.username == "0988111222"
    assert not nguoi.is_superuser
    assert NhatKyThaoTac.objects.filter(
        hanh_dong="TAO_NGUOI_DUNG", doi_tuong=f"NguoiDung:{nguoi.pk}"
    ).exists()
    phan_hoi = client.post("/dang-nhap/", {"username": "0988111222", "password": MAT_KHAU}, follow=True)
    assert phan_hoi.redirect_chain[-1][0] == "/tong-dai/"


def test_tao_quan_tri_hoi_tuong_tac(monkeypatch):
    tra_loi = iter(["Nguyễn Văn A", "0988111333"])
    monkeypatch.setattr("builtins.input", lambda _: next(tra_loi))
    monkeypatch.setattr("getpass.getpass", lambda _: MAT_KHAU)
    call_command("tao_quan_tri")
    assert NguoiDung.objects.filter(so_dien_thoai="0988111333", vai_tro=VaiTro.QUAN_TRI).exists()


def test_tao_quan_tri_trung_sdt(monkeypatch, tao_nguoi_dung):
    tao_nguoi_dung(so_dien_thoai="0988111222")
    monkeypatch.setenv("HOMEFIX_MAT_KHAU_QUAN_TRI", MAT_KHAU)
    with pytest.raises(CommandError, match="đã có tài khoản"):
        call_command("tao_quan_tri", "--no-input", "--ho-ten", "B", "--sdt", "0988111222")


@pytest.mark.parametrize(
    ("ho_ten", "sdt", "mat_khau"),
    [("A", "0988111222", "123"), ("A", "12345", MAT_KHAU), ("  ", "0988111222", MAT_KHAU)],
)
def test_tao_quan_tri_du_lieu_sai(monkeypatch, ho_ten, sdt, mat_khau):
    monkeypatch.setenv("HOMEFIX_MAT_KHAU_QUAN_TRI", mat_khau)
    with pytest.raises(CommandError):
        call_command("tao_quan_tri", "--no-input", "--ho-ten", ho_ten, "--sdt", sdt)
    assert not NguoiDung.objects.exists()


def test_tao_quan_tri_thieu_mat_khau(monkeypatch):
    monkeypatch.delenv("HOMEFIX_MAT_KHAU_QUAN_TRI", raising=False)
    with pytest.raises(CommandError):
        call_command("tao_quan_tri", "--no-input", "--ho-ten", "A", "--sdt", "0988111222")
