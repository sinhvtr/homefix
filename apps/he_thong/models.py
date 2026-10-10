from django.conf import settings
from django.core.cache import cache
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone

from .cau_hinh import chuyen_doi, khoa_bo_dem


class MoHinhCoBan(models.Model):
    """Lớp cha trừu tượng: mọi bảng có tao_luc, cap_nhat_luc (SPEC 5)."""

    tao_luc = models.DateTimeField("tạo lúc", auto_now_add=True)
    cap_nhat_luc = models.DateTimeField("cập nhật lúc", auto_now=True)

    class Meta:
        abstract = True


class CauHinh(MoHinhCoBan):
    class Kieu(models.TextChoices):
        INT = "INT", "Số nguyên"
        BOOL = "BOOL", "Đúng/sai"
        STR = "STR", "Chuỗi"
        JSON = "JSON", "JSON"

    khoa = models.CharField("khóa", max_length=60, unique=True)
    gia_tri = models.CharField("giá trị", max_length=1000)
    kieu = models.CharField("kiểu", max_length=4, choices=Kieu.choices, default=Kieu.STR)
    mo_ta = models.CharField("mô tả", max_length=255, blank=True)

    class Meta:
        db_table = "tblCauHinh"
        verbose_name = "cấu hình"
        verbose_name_plural = "cấu hình"
        ordering = ["khoa"]

    def __str__(self):
        return f"{self.khoa} = {self.gia_tri}"

    def save(self, *args, **kwargs):
        chuyen_doi(self.gia_tri, self.kieu)
        super().save(*args, **kwargs)
        cache.delete(khoa_bo_dem(self.khoa))

    def clean(self):
        chuyen_doi(self.gia_tri, self.kieu)


class NhatKyChiDuocThem(Exception):
    """Nhật ký thao tác chỉ được thêm, không sửa, không xóa (NFR06)."""


class NhatKyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise NhatKyChiDuocThem("Không được sửa nhật ký thao tác.")

    def delete(self):
        raise NhatKyChiDuocThem("Không được xóa nhật ký thao tác.")


class NhatKyThaoTac(MoHinhCoBan):
    nguoi_dung = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="người dùng",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    thoi_diem = models.DateTimeField("thời điểm", default=timezone.now, db_index=True)
    hanh_dong = models.CharField("hành động", max_length=50, db_index=True)
    doi_tuong = models.CharField("đối tượng", max_length=100, db_index=True)
    du_lieu_truoc = models.JSONField("dữ liệu trước", null=True, blank=True, encoder=DjangoJSONEncoder)
    du_lieu_sau = models.JSONField("dữ liệu sau", null=True, blank=True, encoder=DjangoJSONEncoder)
    dia_chi_ip = models.GenericIPAddressField("địa chỉ IP", null=True, blank=True)

    objects = NhatKyQuerySet.as_manager()

    class Meta:
        db_table = "tblNhatKy"
        verbose_name = "nhật ký thao tác"
        verbose_name_plural = "nhật ký thao tác"
        ordering = ["-thoi_diem", "-id"]

    def __str__(self):
        return f"{self.thoi_diem:%d/%m/%Y %H:%M} {self.hanh_dong} {self.doi_tuong}"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise NhatKyChiDuocThem("Không được sửa nhật ký thao tác.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise NhatKyChiDuocThem("Không được xóa nhật ký thao tác.")


class BoDemMaDon(MoHinhCoBan):
    """Bộ đếm số thứ tự đơn trong ngày để sinh mã HFyyMMdd-nnn (SPEC 5.2)."""

    ngay = models.DateField("ngày", unique=True)
    so_cuoi = models.PositiveIntegerField("số cuối", default=0)

    class Meta:
        db_table = "tblBoDemMaDon"
        verbose_name = "bộ đếm mã đơn"
        verbose_name_plural = "bộ đếm mã đơn"

    def __str__(self):
        return f"{self.ngay:%d/%m/%Y}: {self.so_cuoi}"
