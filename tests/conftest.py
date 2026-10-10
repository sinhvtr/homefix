import factory
import pytest
from django.core.cache import cache

from apps.tai_khoan.models import NguoiDung, VaiTro

MAT_KHAU_THU = "Mat-khau-thu-123"


class NguoiDungFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = NguoiDung
        skip_postgeneration_save = True

    so_dien_thoai = factory.Sequence(lambda n: f"09{n:08d}")
    username = factory.LazyAttribute(lambda o: o.so_dien_thoai)
    ho_ten = factory.Sequence(lambda n: f"Người dùng {n}")
    vai_tro = VaiTro.TONG_DAI
    password = factory.django.Password(MAT_KHAU_THU)


@pytest.fixture(autouse=True)
def xoa_bo_dem():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def tao_nguoi_dung(db):
    return NguoiDungFactory
