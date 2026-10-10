import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.danh_muc.models import DiaChi, DichVu, KhachHang, KhuVuc, Tho
from apps.he_thong.templatetags.dinh_dang import an_sdt, tien
from apps.tai_khoan.models import NguoiDung, VaiTro

pytestmark = pytest.mark.django_db


def test_nap_du_lieu_mau_phan_danh_muc(capsys):
    call_command("nap_du_lieu_mau")
    assert KhuVuc.objects.count() == 12
    assert DichVu.objects.count() == 20
    assert set(DichVu.objects.values_list("nhom_dich_vu", flat=True)) == {
        "VE_SINH_BAO_DUONG",
        "SUA_CHUA_THAY_VAT_TU",
    }
    dem = {v: NguoiDung.objects.filter(vai_tro=v).count() for v in VaiTro.values}
    assert dem == {"QUAN_TRI": 1, "TONG_DAI": 3, "KE_TOAN": 1, "GIAM_DOC": 1, "THO": 12}
    assert Tho.objects.filter(nghi_den__gt=timezone.now()).count() == 2
    assert all(t.ky_nang.exists() and t.khu_vuc_phu_trach.exists() for t in Tho.objects.all())
    assert KhachHang.objects.count() == 40
    assert KhachHang.objects.filter(loai_khach="VIP").count() == 3
    assert all(kh.ds_dia_chi.filter(la_mac_dinh=True).count() == 1 for kh in KhachHang.objects.all())
    ra = capsys.readouterr().out
    assert "chỉ in MỘT lần" in ra and ra.count("\n0900") == 0  # bảng có cột họ tên trước tên đăng nhập
    assert sum(1 for dong in ra.splitlines() if " 0900" in dong) == 18


def test_mat_khau_mau_dang_nhap_duoc(client, capsys):
    call_command("nap_du_lieu_mau")
    dong = next(d for d in capsys.readouterr().out.splitlines() if d.startswith("Thợ"))
    ten, pin = dong.split()[-2:]
    client.post("/dang-nhap/", {"username": ten, "password": pin})
    assert client.get("/tho/").status_code == 200


def test_khong_nap_hai_lan():
    call_command("nap_du_lieu_mau")
    with pytest.raises(CommandError, match="Đã có dữ liệu mẫu"):
        call_command("nap_du_lieu_mau")


def test_xoa_du_lieu_mau_can_xac_nhan_va_xoa_sach():
    call_command("nap_du_lieu_mau")
    with pytest.raises(CommandError):
        call_command("xoa_du_lieu_mau")
    call_command("xoa_du_lieu_mau", "--xac-nhan")
    assert not (KhachHang.objects.exists() or DiaChi.objects.exists() or Tho.objects.exists())
    assert not DichVu.objects.exists() and not KhuVuc.objects.exists()
    assert not NguoiDung.objects.filter(is_active=True, so_dien_thoai__startswith="0900").exists()


def test_xoa_du_lieu_mau_giu_du_lieu_that(tao_nguoi_dung):
    that = tao_nguoi_dung(so_dien_thoai="0988123456", vai_tro=VaiTro.QUAN_TRI)
    call_command("nap_du_lieu_mau")
    call_command("xoa_du_lieu_mau", "--xac-nhan")
    that.refresh_from_db()
    assert that.is_active


@pytest.mark.parametrize(
    ("vao", "ra"), [(1_250_000, "1.250.000 đ"), (0, "0 đ"), (None, ""), (-50_000, "-50.000 đ")]
)
def test_bo_loc_tien(vao, ra):
    assert tien(vao) == ra


def test_bo_loc_an_sdt():
    assert an_sdt("0901234123") == "090****123"
    assert an_sdt("") == ""
