import pytest
from django.apps import apps
from django.core.management import call_command

pytestmark = pytest.mark.django_db


def test_suc_khoe_khong_can_dang_nhap(client):
    phan_hoi = client.get("/suc-khoe/")
    assert phan_hoi.status_code == 200
    assert phan_hoi.json() == {"trang_thai": "ok", "csdl": "ok"}


@pytest.mark.parametrize(
    ("mo_hinh", "bang"),
    [
        ("tai_khoan.NguoiDung", "tblNhanVien"),
        ("he_thong.CauHinh", "tblCauHinh"),
        ("he_thong.NhatKyThaoTac", "tblNhatKy"),
    ],
)
def test_ten_bang_dung_spec_va_co_moc_thoi_gian(mo_hinh, bang):
    model = apps.get_model(mo_hinh)
    assert model._meta.db_table == bang
    ten_truong = {f.name for f in model._meta.get_fields()}
    assert {"tao_luc", "cap_nhat_luc"} <= ten_truong


def test_tao_khoa_vapid(capsys):
    call_command("tao_khoa_vapid")
    dong = dict(d.split("=", 1) for d in capsys.readouterr().out.splitlines() if d.startswith("VAPID_"))
    assert len(dong["VAPID_PUBLIC_KEY"]) == 87  # 65 byte điểm không nén, base64url bỏ dấu =
    assert len(dong["VAPID_PRIVATE_KEY"]) == 43  # 32 byte


def test_trang_404_tieng_viet(client, settings):
    settings.DEBUG = False
    phan_hoi = client.get("/khong-co-trang-nay/")
    assert phan_hoi.status_code == 404
    assert "Không tìm thấy trang" in phan_hoi.content.decode()
