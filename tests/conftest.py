import factory
import pytest
from django.core.cache import cache

from apps.danh_muc.models import DiaChi, DichVu, KhachHang, KhuVuc, LoaiThietBi, ThietBi, Tho
from apps.tai_khoan.models import NguoiDung, VaiTro

MAT_KHAU_THU = "Mat-khau-thu-123"


class NguoiDungFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NguoiDung
        skip_postgeneration_save = True

    so_dien_thoai = factory.Sequence(lambda n: f"097{n:07d}")  # tránh dải 0900… của dữ liệu mẫu
    username = factory.LazyAttribute(lambda o: o.so_dien_thoai)
    ho_ten = factory.Sequence(lambda n: f"Người dùng {n}")
    vai_tro = VaiTro.TONG_DAI
    password = factory.django.Password(MAT_KHAU_THU)


class KhuVucFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KhuVuc
        django_get_or_create = ("ma",)

    ma = factory.Sequence(lambda n: f"KV{n:02d}")
    ten = factory.Sequence(lambda n: f"Khu vực {n}")


class DichVuFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DichVu

    ma = factory.Sequence(lambda n: f"DV{n:03d}")
    ten_dich_vu = factory.Sequence(lambda n: f"Dịch vụ {n}")
    nhom_dich_vu = DichVu.NhomDichVu.VE_SINH_BAO_DUONG
    loai_thiet_bi = LoaiThietBi.DIEU_HOA
    don_gia_tham_khao = 150_000
    don_vi_tinh = "máy"
    thoi_han_bao_hanh_ngay = 7


class ThoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tho

    nguoi_dung = factory.SubFactory(NguoiDungFactory, vai_tro=VaiTro.THO)
    ho_ten = factory.LazyAttribute(lambda o: o.nguoi_dung.ho_ten)
    so_dien_thoai = factory.LazyAttribute(lambda o: o.nguoi_dung.so_dien_thoai)
    hinh_thuc = Tho.HinhThuc.CHINH_THUC


class KhachHangFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = KhachHang

    ho_ten = factory.Sequence(lambda n: f"Khách {n}")
    so_dien_thoai = factory.Sequence(lambda n: f"08{n:08d}")


class DiaChiFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DiaChi

    khach_hang = factory.SubFactory(KhachHangFactory)
    dia_chi_chi_tiet = factory.Sequence(lambda n: f"Số {n} ngõ thử")
    khu_vuc = factory.SubFactory(KhuVucFactory)
    la_mac_dinh = True


class ThietBiFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ThietBi

    dia_chi = factory.SubFactory(DiaChiFactory)
    loai_thiet_bi = LoaiThietBi.DIEU_HOA
    hang_san_xuat = "Daikin"


@pytest.fixture(autouse=True)
def bam_mat_khau_nhanh(settings):
    """Chỉ trong kiểm thử: bộ băm nhanh để bộ kiểm thử không mất vài phút vì PBKDF2."""
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]


@pytest.fixture(autouse=True)
def thong_bao_dong_bo(settings):
    """Kiểm thử: thông báo gửi đồng bộ ngay sau commit qua ConsoleKenh (không gọi mạng, không cần worker)."""
    settings.THONG_BAO_DONG_BO = True
    settings.THONG_BAO_CHI_CONSOLE = True


@pytest.fixture(autouse=True)
def xoa_bo_dem():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def tao_nguoi_dung(db):
    return NguoiDungFactory


@pytest.fixture
def quan_tri(db):
    return NguoiDungFactory(vai_tro=VaiTro.QUAN_TRI, ho_ten="Quản trị thử")


@pytest.fixture
def tong_dai(db):
    return NguoiDungFactory(vai_tro=VaiTro.TONG_DAI)


@pytest.fixture
def client_quan_tri(client, quan_tri):
    client.force_login(quan_tri)
    return client


@pytest.fixture
def client_vai_tro(client, db):
    """client_vai_tro("THO") → client đã đăng nhập bằng một người dùng mới có vai trò đó."""

    def tao(vai_tro):
        nguoi = ThoFactory().nguoi_dung if vai_tro == VaiTro.THO else NguoiDungFactory(vai_tro=vai_tro)
        client.force_login(nguoi)
        client.nguoi_dung = nguoi
        return client

    return tao


def tao_don(
    trang_thai="CHO_XAC_NHAN_LICH",
    *,
    nhom="VE_SINH_BAO_DUONG",
    dia_chi=None,
    dich_vu=None,
    nguoi_tao=None,
    loai_don="THUONG",
    don_goc=None,
    **kw,
):
    """Tạo đơn qua khoi_tao (T1) rồi — CHỈ để dựng dữ liệu kiểm thử — đặt thẳng trạng thái bằng QuerySet.update."""
    from apps.don_sua_chua.dao import sinh_ma_don
    from apps.don_sua_chua.models import DonSuaChua

    dc = dia_chi or DiaChiFactory()
    don = DonSuaChua(
        ma_don=sinh_ma_don(),
        khach_hang=dc.khach_hang,
        dia_chi=dc,
        dich_vu_yeu_cau=dich_vu or DichVuFactory(nhom_dich_vu=nhom),
        kenh_tiep_nhan="DIEN_THOAI",
        nguoi_tao=nguoi_tao or NguoiDungFactory(),
        loai_don=loai_don,
        don_goc=don_goc,
        **kw,
    )
    don.khoi_tao(da_chot_lich=False)
    if trang_thai != "CHO_XAC_NHAN_LICH":
        DonSuaChua.objects.filter(pk=don.pk).update(trang_thai=trang_thai)
        don.refresh_from_db()
    return don


def tao_lich(don, ngay_gio=None, gio=2, trang_thai="HIEU_LUC"):
    from datetime import timedelta

    from django.utils import timezone

    from apps.tiep_nhan_dieu_phoi.models import LichHen

    bd = ngay_gio or timezone.now() + timedelta(days=1)
    return LichHen.objects.create(
        don=don,
        bat_dau=bd,
        ket_thuc=bd + timedelta(hours=gio),
        trang_thai=trang_thai,
        nguoi_tao=don.nguoi_tao,
    )


def tao_tho_phu_hop(dich_vu, khu_vuc=None, **kw):
    """Thợ đang hoạt động, có kỹ năng đúng dịch vụ (và phụ trách khu vực nếu truyền vào)."""
    tho = ThoFactory(**kw)
    tho.ky_nang.add(dich_vu)
    if khu_vuc is not None:
        tho.khu_vuc_phu_trach.add(khu_vuc)
    return tho


def don_cho_cu_tho(ngay_gio=None, **kw):
    """Đơn CHO_CU_THO có lịch hiệu lực (tiền điều kiện UC04)."""
    don = tao_don("CHO_CU_THO", **kw)
    don.lich = tao_lich(don, ngay_gio=ngay_gio)
    return don
