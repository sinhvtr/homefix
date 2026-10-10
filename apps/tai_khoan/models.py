from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.he_thong.models import MoHinhCoBan
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


class VaiTro(models.TextChoices):
    QUAN_TRI = "QUAN_TRI", "Quản trị"
    TONG_DAI = "TONG_DAI", "Tổng đài"
    THO = "THO", "Thợ"
    KE_TOAN = "KE_TOAN", "Kế toán"
    GIAM_DOC = "GIAM_DOC", "Giám đốc"


class NguoiDung(AbstractUser, MoHinhCoBan):
    """Người dùng hệ thống [SRS: NhanVien]. Mỗi người đúng một vai trò; khóa tài khoản bằng is_active."""

    ho_ten = models.CharField("họ tên", max_length=100)
    so_dien_thoai = models.CharField("số điện thoại", max_length=10, unique=True)
    vai_tro = models.CharField("vai trò", max_length=10, choices=VaiTro.choices)

    REQUIRED_FIELDS = ["ho_ten", "so_dien_thoai", "vai_tro"]

    class Meta:
        db_table = "tblNhanVien"
        verbose_name = "người dùng"
        verbose_name_plural = "người dùng"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(vai_tro__in=VaiTro.values), name="nguoi_dung_vai_tro_hop_le"
            ),
        ]

    def __str__(self):
        return self.ho_ten or self.username

    @property
    def dang_hoat_dong(self) -> bool:
        return self.is_active

    def clean(self):
        super().clean()
        self.so_dien_thoai = chuan_hoa_sdt(self.so_dien_thoai)

    def save(self, *args, **kwargs):
        self.so_dien_thoai = chuan_hoa_sdt(self.so_dien_thoai)
        super().save(*args, **kwargs)

    def la_vai_tro(self, *vai_tro: str) -> bool:
        """QUAN_TRI có mọi quyền của TONG_DAI (SPEC 3)."""
        if self.vai_tro in vai_tro:
            return True
        return self.vai_tro == VaiTro.QUAN_TRI and VaiTro.TONG_DAI in vai_tro
