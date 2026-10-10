"""ThanhToan (P4), PhieuDoiSoat (P5) — UC09, UC12."""

from django.db import models
from django.utils import timezone

from apps.danh_muc.models import Tho
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import MoHinhCoBan


def duong_dan_chung_tu(_, ten_goc: str) -> str:
    import uuid

    return f"chung_tu/{timezone.localtime():%Y/%m}/{uuid.uuid4().hex}.jpg"


class ThanhToan(MoHinhCoBan):
    """Một khoản tiền thợ ghi nhận đã thu của khách (SPEC 5.2)."""

    class HinhThuc(models.TextChoices):
        TIEN_MAT = "TIEN_MAT", "Tiền mặt"
        CK_TAI_KHOAN_CONG_TY = "CK_TAI_KHOAN_CONG_TY", "Chuyển khoản công ty"
        CK_TAI_KHOAN_THO = "CK_TAI_KHOAN_THO", "Chuyển khoản cho thợ"

    class TrangThai(models.TextChoices):
        CHUA_NOP = "CHUA_NOP", "Chưa nộp"
        DA_NOP = "DA_NOP", "Đã nộp"
        KHONG_CAN_NOP = "KHONG_CAN_NOP", "Không cần nộp"

    don = models.ForeignKey(
        DonSuaChua, verbose_name="đơn", on_delete=models.PROTECT, related_name="ds_thanh_toan"
    )
    tho = models.ForeignKey(Tho, verbose_name="thợ", on_delete=models.PROTECT, related_name="ds_thanh_toan")
    so_tien = models.BigIntegerField("số tiền (đ)")
    hinh_thuc = models.CharField("hình thức", max_length=22, choices=HinhThuc.choices)
    thoi_diem_thu = models.DateTimeField("thời điểm thu", default=timezone.now)
    trang_thai = models.CharField("trạng thái", max_length=14, choices=TrangThai.choices)
    anh_chung_tu = models.ImageField("ảnh chứng từ", upload_to=duong_dan_chung_tu, blank=True)

    class Meta:
        db_table = "tblThanhToan"
        verbose_name = "thanh toán"
        verbose_name_plural = "thanh toán"
        ordering = ["-thoi_diem_thu", "-id"]
        indexes = [models.Index(fields=["tho", "trang_thai"], name="thanh_toan_tho_trang_thai_idx")]
        constraints = [
            models.CheckConstraint(condition=models.Q(so_tien__gte=0), name="thanh_toan_so_tien_khong_am"),
        ]

    def __str__(self):
        return f"{self.don_id}: {self.so_tien} ({self.hinh_thuc})"

    @staticmethod
    def trang_thai_ban_dau(hinh_thuc: str, so_tien: int) -> str:
        """CK vào tài khoản công ty → KHONG_CAN_NOP ngay khi tạo (SPEC 5.2); thu 0 đ cũng không cần nộp (A-70)."""
        if hinh_thuc == ThanhToan.HinhThuc.CK_TAI_KHOAN_CONG_TY or so_tien == 0:
            return ThanhToan.TrangThai.KHONG_CAN_NOP
        return ThanhToan.TrangThai.CHUA_NOP
