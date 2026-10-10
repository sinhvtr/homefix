"""LichHen (P2), PhanCong (P3) — UC02–UC06."""

from django.conf import settings
from django.db import models

from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import MoHinhCoBan


class LichHen(MoHinhCoBan):
    class TrangThai(models.TextChoices):
        HIEU_LUC = "HIEU_LUC", "Hiệu lực"
        DA_THAY_THE = "DA_THAY_THE", "Đã thay thế"
        DA_HUY = "DA_HUY", "Đã hủy"

    don = models.ForeignKey(
        DonSuaChua, verbose_name="đơn", on_delete=models.CASCADE, related_name="ds_lich_hen"
    )
    bat_dau = models.DateTimeField("bắt đầu")
    ket_thuc = models.DateTimeField("kết thúc")
    trang_thai = models.CharField(
        "trạng thái", max_length=12, choices=TrangThai.choices, default=TrangThai.HIEU_LUC
    )
    ly_do_doi_hen = models.TextField("lý do đổi hẹn", blank=True)
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người tạo", on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "tblLichHen"
        verbose_name = "lịch hẹn"
        verbose_name_plural = "lịch hẹn"
        ordering = ["-tao_luc", "-id"]
        indexes = [models.Index(fields=["don", "trang_thai"], name="lich_hen_don_trang_thai_idx")]
        constraints = [
            # Một đơn chỉ một lịch hiệu lực (SPEC 5.2, UC03) — chặn ở mức CSDL
            models.UniqueConstraint(
                fields=["don"], condition=models.Q(trang_thai="HIEU_LUC"), name="mot_lich_hieu_luc_moi_don"
            ),
            models.CheckConstraint(
                condition=models.Q(ket_thuc__gt=models.F("bat_dau")), name="lich_ket_thuc_sau_bat_dau"
            ),
        ]

    def __str__(self):
        return f"{self.don_id}: {self.khung_gio}"

    @property
    def khung_gio(self) -> str:
        """'08:00-10:00 ngày 12/10/2026' theo giờ Việt Nam."""
        from django.utils import timezone

        bd, kt = timezone.localtime(self.bat_dau), timezone.localtime(self.ket_thuc)
        return f"{bd:%H:%M}-{kt:%H:%M} ngày {bd:%d/%m/%Y}"
