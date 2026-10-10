"""PhieuBaoHanh (UC09 phát hành, UC11 sử dụng) — BR05."""

from django.db import models
from django.utils import timezone

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import MoHinhCoBan


class PhieuBaoHanh(MoHinhCoBan):
    ma = models.CharField("mã", max_length=20, unique=True)  # "BH-" + mã đơn
    don = models.OneToOneField(
        DonSuaChua, verbose_name="đơn", on_delete=models.PROTECT, related_name="phieu_bao_hanh"
    )
    ngay_bat_dau = models.DateField("ngày bắt đầu")
    ngay_het_han = models.DateField("ngày hết hạn")
    dieu_kien = models.TextField("điều kiện bảo hành")

    class Meta:
        db_table = "tblPhieuBaoHanh"
        verbose_name = "phiếu bảo hành"
        verbose_name_plural = "phiếu bảo hành"
        ordering = ["-ngay_bat_dau"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ngay_het_han__gte=models.F("ngay_bat_dau")),
                name="bao_hanh_het_han_sau_bat_dau",
            ),
        ]

    def __str__(self):
        return self.ma

    @property
    def con_han(self) -> bool:
        """Còn hạn = hôm nay (giờ Việt Nam) ≤ ngày hết hạn."""
        return timezone.localdate() <= self.ngay_het_han
