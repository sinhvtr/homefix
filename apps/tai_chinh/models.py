"""ThanhToan (P4), PhieuDoiSoat (P5) — UC09, UC12."""

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.danh_muc.models import Tho
from apps.don_sua_chua.models import DonSuaChua
from apps.he_thong.models import MoHinhCoBan


def duong_dan_chung_tu(_, ten_goc: str) -> str:
    import uuid

    return f"chung_tu/{timezone.localtime():%Y/%m}/{uuid.uuid4().hex}.jpg"


class PhieuDoiSoat(MoHinhCoBan):
    """Phiếu đối soát tiền thợ đã thu (UC12, SPEC 5.2). so_phai_nop âm = công ty phải trả thợ."""

    class TrangThai(models.TextChoices):
        NHAP = "NHAP", "Nháp"
        DA_CHOT = "DA_CHOT", "Đã chốt"
        DA_NOP = "DA_NOP", "Đã nộp"

    ma = models.CharField("mã", max_length=30, unique=True)  # DS-yyMM-<mã thợ>-n
    tho = models.ForeignKey(
        Tho, verbose_name="thợ", on_delete=models.PROTECT, related_name="ds_phieu_doi_soat"
    )
    tu_ngay = models.DateField("từ ngày")
    den_ngay = models.DateField("đến ngày")
    tong_tien_thu = models.BigIntegerField("tổng tiền thu (đ)", default=0)
    tong_vat_tu_ung = models.BigIntegerField("tổng vật tư thợ ứng (đ)", default=0)
    so_phai_nop = models.BigIntegerField("số phải nộp (đ)", default=0)
    trang_thai = models.CharField(
        "trạng thái", max_length=8, choices=TrangThai.choices, default=TrangThai.NHAP
    )
    nguoi_lap = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người lập", on_delete=models.PROTECT, related_name="+"
    )
    xac_nhan_luc = models.DateTimeField("xác nhận nộp lúc", null=True, blank=True)
    ghi_chu = models.TextField("ghi chú", blank=True)

    class Meta:
        db_table = "tblPhieuDoiSoat"
        verbose_name = "phiếu đối soát"
        verbose_name_plural = "phiếu đối soát"
        ordering = ["-tao_luc", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(den_ngay__gte=models.F("tu_ngay")), name="doi_soat_den_sau_tu"
            ),
            models.CheckConstraint(
                condition=models.Q(so_phai_nop=models.F("tong_tien_thu") - models.F("tong_vat_tu_ung")),
                name="doi_soat_so_phai_nop_khop",
            ),
        ]

    def __str__(self):
        return self.ma


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
    # Khóa ngoại → một ThanhToan chỉ nằm ở tối đa MỘT phiếu đối soát (UC12, nghiệm thu P5)
    phieu_doi_soat = models.ForeignKey(
        PhieuDoiSoat,
        verbose_name="phiếu đối soát",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ds_thanh_toan",
    )

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
