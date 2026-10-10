"""ThongBao (chuông trong ứng dụng), DangKyPush (Web Push) — SPEC 5.2, mục 11."""

from django.conf import settings
from django.db import models

from apps.he_thong.models import MoHinhCoBan


class ThongBao(MoHinhCoBan):
    nguoi_nhan = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="người nhận",
        on_delete=models.CASCADE,
        related_name="ds_thong_bao",
    )
    tieu_de = models.CharField("tiêu đề", max_length=200)
    noi_dung = models.TextField("nội dung", blank=True)
    duong_dan = models.CharField("đường dẫn", max_length=255, blank=True)
    da_doc = models.BooleanField("đã đọc", default=False)

    class Meta:
        db_table = "tblThongBao"
        verbose_name = "thông báo"
        verbose_name_plural = "thông báo"
        ordering = ["-tao_luc", "-id"]
        indexes = [models.Index(fields=["nguoi_nhan", "da_doc"], name="thong_bao_nguoi_nhan_idx")]

    def __str__(self):
        return self.tieu_de


class DangKyPush(MoHinhCoBan):
    nguoi_dung = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="người dùng",
        on_delete=models.CASCADE,
        related_name="ds_dang_ky_push",
    )
    endpoint = models.URLField("endpoint", max_length=500, unique=True)
    p256dh = models.CharField("p256dh", max_length=200)
    auth = models.CharField("auth", max_length=100)
    user_agent = models.CharField("trình duyệt", max_length=300, blank=True)

    class Meta:
        db_table = "tblDangKyPush"
        verbose_name = "đăng ký Web Push"
        verbose_name_plural = "đăng ký Web Push"

    def __str__(self):
        return f"{self.nguoi_dung_id}: {self.endpoint[:40]}…"
