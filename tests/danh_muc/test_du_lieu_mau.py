import pytest
from django.core.management import CommandError, call_command
from django.utils import timezone

from apps.danh_muc.models import DiaChi, DichVu, KhachHang, KhuVuc, Tho
from apps.he_thong.models import NhatKyThaoTac
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


def test_nap_du_lieu_mau_phan_don_moi_trang_thai_bao_hanh_doi_soat(capsys):
    """SPEC 14.4: ~60 đơn trải đều mọi trạng thái trong 30 ngày qua và hôm nay, có đơn bảo hành, phiếu đối soát."""
    from apps.bao_hanh.models import PhieuBaoHanh
    from apps.don_sua_chua.models import DonSuaChua
    from apps.don_sua_chua.trang_thai import TrangThaiDon
    from apps.tai_chinh.models import PhieuDoiSoat, ThanhToan

    call_command("nap_du_lieu_mau")
    don = DonSuaChua.objects.all()
    assert 55 <= don.count() <= 70
    assert set(don.values_list("trang_thai", flat=True)) == set(TrangThaiDon.values)
    hom_nay = timezone.localdate()
    ngay = {timezone.localdate(d) for d in don.values_list("ngay_tiep_nhan", flat=True)}
    assert hom_nay in ngay and min(ngay) >= hom_nay - timezone.timedelta(days=30) and len(ngay) >= 15
    assert all(
        d.ma_don[2:8] == f"{timezone.localdate(d.ngay_tiep_nhan):%y%m%d}" for d in don
    )  # mã theo ngày nhận
    bh = don.filter(loai_don="BAO_HANH")
    assert bh.count() >= 2 and don.filter(trang_thai="DANG_BAO_HANH").exists()
    assert {"T16", "T17"} <= set(
        NhatKyThaoTac.objects.filter(du_lieu_sau__chuyen__in=["T16", "T17"]).values_list(
            "du_lieu_sau__chuyen", flat=True
        )
    )
    assert set(PhieuDoiSoat.objects.values_list("trang_thai", flat=True)) == {"NHAP", "DA_CHOT", "DA_NOP"}
    assert (
        ThanhToan.objects.filter(trang_thai="DA_NOP").exists()
        and ThanhToan.objects.filter(trang_thai="CHUA_NOP").exists()
    )
    xong = don.filter(trang_thai__in=["HOAN_THANH", "DANG_BAO_HANH", "DA_DONG"], loai_don="THUONG")
    assert PhieuBaoHanh.objects.filter(don__in=xong).count() == xong.count()
    assert not PhieuBaoHanh.objects.filter(don__trang_thai="HOAN_THANH", ngay_het_han__lt=hom_nay).exists()
    assert don.filter(uu_tien=True).exists() and don.filter(canh_bao_chua_cu_duoc=True).exists()
    assert don.filter(cho_tong_dai_xac_nhan_gia=True).exists()
    from apps.tiep_nhan_dieu_phoi.models import PhanCong

    assert {"TU_CHOI", "QUA_HAN", "DA_NHAN"} <= set(PhanCong.objects.values_list("trang_thai", flat=True))
    # mốc đề nghị dời về ngày tiếp nhận: báo cáo "tiếp nhận → có thợ" không tính bằng ngày
    for pc in PhanCong.objects.filter(trang_thai="DA_NHAN").select_related("don"):
        assert (
            timezone.timedelta(0)
            <= pc.thoi_diem_phan_hoi - pc.don.ngay_tiep_nhan
            <= timezone.timedelta(hours=1)
        )
    assert "Đơn mẫu:" in capsys.readouterr().out


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
    from apps.don_sua_chua.models import AnhHienTruong, DonSuaChua
    from apps.tai_chinh.models import PhieuDoiSoat

    assert not (
        DonSuaChua.objects.exists() or PhieuDoiSoat.objects.exists() or AnhHienTruong.objects.exists()
    )
    assert not NguoiDung.objects.filter(is_active=True, so_dien_thoai__startswith="0900").exists()


def test_nap_lai_sau_khi_xoa_dung_lai_tai_khoan_mau_bi_khoa(client, capsys):
    """Người dùng mẫu có nhật ký bị khóa khi xóa (A-33) — lần nạp sau mở khóa, cấp mật khẩu mới, không trùng SĐT."""
    call_command("nap_du_lieu_mau")
    call_command("xoa_du_lieu_mau", "--xac-nhan")
    assert NguoiDung.objects.filter(so_dien_thoai__startswith="0900", is_active=False).exists()
    capsys.readouterr()
    call_command("nap_du_lieu_mau")
    assert NguoiDung.objects.filter(so_dien_thoai__startswith="0900").count() == 18
    assert not NguoiDung.objects.filter(so_dien_thoai__startswith="0900", is_active=False).exists()
    dong = next(d for d in capsys.readouterr().out.splitlines() if d.startswith("Thợ"))
    ten, pin = dong.split()[-2:]
    client.post("/dang-nhap/", {"username": ten, "password": pin})
    assert client.get("/tho/").status_code == 200


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
