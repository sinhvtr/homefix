"""LichHen, PhanCong — UC02–UC07."""

from django.conf import settings
from django.db import models

from apps.danh_muc.models import Tho
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


class PhanCong(MoHinhCoBan):
    """Một lượt đề nghị nhận việc gửi một thợ (SPEC 5.2). Máy trạng thái mục 6.2."""

    class TrangThai(models.TextChoices):
        CHO_PHAN_HOI = "CHO_PHAN_HOI", "Chờ phản hồi"
        DA_NHAN = "DA_NHAN", "Đã nhận"
        TU_CHOI = "TU_CHOI", "Từ chối"
        QUA_HAN = "QUA_HAN", "Quá hạn"
        DA_HUY = "DA_HUY", "Đã hủy"

    class LyDoTuChoi(models.TextChoices):
        BAN = "BAN", "Đang bận"
        XA = "XA", "Xa quá"
        KHONG_DUNG_CHUYEN_MON = "KHONG_DUNG_CHUYEN_MON", "Không đúng chuyên môn"
        KHAC = "KHAC", "Lý do khác"

    don = models.ForeignKey(
        DonSuaChua, verbose_name="đơn", on_delete=models.CASCADE, related_name="ds_phan_cong"
    )
    tho = models.ForeignKey(Tho, verbose_name="thợ", on_delete=models.PROTECT, related_name="ds_phan_cong")
    # BR01: mọi phân công đều do một người (tổng đài/quản trị) giao — NOT NULL ở CSDL
    nguoi_giao = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người giao", on_delete=models.PROTECT, related_name="+"
    )
    thoi_diem_giao = models.DateTimeField("thời điểm giao")
    han_phan_hoi = models.DateTimeField("hạn phản hồi")
    trang_thai = models.CharField(
        "trạng thái", max_length=12, choices=TrangThai.choices, default=TrangThai.CHO_PHAN_HOI
    )
    thoi_diem_phan_hoi = models.DateTimeField("thời điểm phản hồi", null=True, blank=True)
    ly_do_tu_choi = models.CharField(  # noqa: DJ001 — SPEC 5.2: chỉ có khi từ chối
        "lý do từ chối", max_length=25, choices=LyDoTuChoi.choices, null=True, blank=True
    )
    ghi_chu = models.TextField("ghi chú", blank=True)
    tien_cong_du_kien = models.BigIntegerField("tiền công dự kiến (đ)")
    giao_qua_dien_thoai = models.BooleanField("thợ đồng ý qua điện thoại", default=False)

    class Meta:
        db_table = "tblPhanCong"
        verbose_name = "phân công"
        verbose_name_plural = "phân công"
        ordering = ["-thoi_diem_giao", "-id"]
        indexes = [
            models.Index(fields=["trang_thai"], name="phan_cong_trang_thai_idx"),
            models.Index(fields=["tho", "trang_thai"], name="phan_cong_tho_trang_thai_idx"),
        ]
        constraints = [
            # BR03: một đơn tối đa một phân công đã nhận — lưới an toàn ở CSDL
            models.UniqueConstraint(
                fields=["don"], condition=models.Q(trang_thai="DA_NHAN"), name="mot_phan_cong_da_nhan_moi_don"
            ),
        ]

    def __str__(self):
        return f"{self.don_id} → {self.tho_id} ({self.trang_thai})"
