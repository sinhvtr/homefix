"""KhachHang, DiaChi, ThietBi, DichVu, Tho, KhuVuc (SPEC 5.2, UC13)."""

from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.he_thong.models import MoHinhCoBan
from apps.he_thong.so_dien_thoai import chuan_hoa_sdt


class LoaiThietBi(models.TextChoices):
    DIEU_HOA = "DIEU_HOA", "Điều hòa"
    MAY_GIAT = "MAY_GIAT", "Máy giặt"
    TU_LANH = "TU_LANH", "Tủ lạnh"
    BINH_NONG_LANH = "BINH_NONG_LANH", "Bình nóng lạnh"
    DIEN_NUOC = "DIEN_NUOC", "Điện nước"
    KHAC = "KHAC", "Khác"


# Trạng thái đơn được tính là "đã sử dụng dịch vụ" cho BR07 (mã trạng thái của DonSuaChua)
TRANG_THAI_DA_LAM_XONG = ("HOAN_THANH", "DANG_BAO_HANH", "DA_DONG")


class KhuVuc(MoHinhCoBan):
    ma = models.CharField("mã", max_length=20, unique=True)
    ten = models.CharField("tên", max_length=100)
    ghi_chu = models.TextField("ghi chú", blank=True)

    class Meta:
        db_table = "tblKhuVuc"
        verbose_name = "khu vực"
        verbose_name_plural = "khu vực"
        ordering = ["ten"]

    def __str__(self):
        return self.ten


class KhachHang(MoHinhCoBan):
    class LoaiKhach(models.TextChoices):
        THUONG = "THUONG", "Thường"
        VIP = "VIP", "VIP"

    ho_ten = models.CharField("họ tên", max_length=100, blank=True)  # UC02: được lưu khi thiếu tên
    so_dien_thoai = models.CharField("số điện thoại", max_length=10, unique=True)
    so_dien_thoai_phu = models.CharField("số điện thoại phụ", max_length=10, blank=True)
    loai_khach = models.CharField(
        "loại khách", max_length=6, choices=LoaiKhach.choices, default=LoaiKhach.THUONG
    )
    vip_thu_cong = models.BooleanField("VIP thủ công", default=False)
    ly_do_vip = models.CharField("lý do VIP", max_length=200, blank=True)
    ghi_chu = models.TextField("ghi chú", blank=True)

    class Meta:
        db_table = "tblKhachHang"
        verbose_name = "khách hàng"
        verbose_name_plural = "khách hàng"
        ordering = ["-tao_luc"]

    def __str__(self):
        return self.ho_ten or self.so_dien_thoai

    def save(self, *args, **kwargs):
        self.so_dien_thoai = chuan_hoa_sdt(self.so_dien_thoai)
        if self.so_dien_thoai_phu:
            self.so_dien_thoai_phu = chuan_hoa_sdt(self.so_dien_thoai_phu)
        super().save(*args, **kwargs)

    @property
    def la_vip(self) -> bool:
        return self.loai_khach == self.LoaiKhach.VIP

    @property
    def so_lan_su_dung_trong_nam(self) -> int:
        """Số đơn đã làm xong (HOAN_THANH, DANG_BAO_HANH, DA_DONG) tiếp nhận trong 365 ngày gần nhất (BR07, A-71).
        DonSuaChua thuộc gói lõi (tầng trên) — đếm qua quan hệ ngược, không import."""
        return self.ds_don.filter(
            trang_thai__in=TRANG_THAI_DA_LAM_XONG, ngay_tiep_nhan__gte=timezone.now() - timedelta(days=365)
        ).count()


class DiaChi(MoHinhCoBan):
    khach_hang = models.ForeignKey(
        KhachHang, verbose_name="khách hàng", on_delete=models.CASCADE, related_name="ds_dia_chi"
    )
    dia_chi_chi_tiet = models.CharField("địa chỉ chi tiết", max_length=255)
    khu_vuc = models.ForeignKey(
        KhuVuc, verbose_name="khu vực", on_delete=models.PROTECT, related_name="ds_dia_chi"
    )
    ghi_chu_duong_di = models.TextField("ghi chú đường đi", blank=True)
    la_mac_dinh = models.BooleanField("mặc định", default=False)

    class Meta:
        db_table = "tblDiaChi"
        verbose_name = "địa chỉ"
        verbose_name_plural = "địa chỉ"
        ordering = ["-la_mac_dinh", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["khach_hang"], condition=models.Q(la_mac_dinh=True), name="mot_dia_chi_mac_dinh"
            ),
        ]

    def __str__(self):
        return f"{self.dia_chi_chi_tiet} ({self.khu_vuc})"


class ThietBi(MoHinhCoBan):
    dia_chi = models.ForeignKey(
        DiaChi, verbose_name="địa chỉ", on_delete=models.CASCADE, related_name="ds_thiet_bi"
    )
    loai_thiet_bi = models.CharField("loại thiết bị", max_length=20, choices=LoaiThietBi.choices)
    hang_san_xuat = models.CharField("hãng sản xuất", max_length=50, blank=True)
    model = models.CharField("model", max_length=50, blank=True)
    vi_tri_lap = models.CharField("vị trí lắp", max_length=100, blank=True)
    ghi_chu = models.TextField("ghi chú", blank=True)

    class Meta:
        db_table = "tblThietBi"
        verbose_name = "thiết bị"
        verbose_name_plural = "thiết bị"
        ordering = ["id"]

    def __str__(self):
        phan = [self.get_loai_thiet_bi_display(), self.hang_san_xuat, self.model, self.vi_tri_lap]
        return " · ".join(p for p in phan if p)


class DichVu(MoHinhCoBan):
    class NhomDichVu(models.TextChoices):
        VE_SINH_BAO_DUONG = "VE_SINH_BAO_DUONG", "Vệ sinh, bảo dưỡng"
        SUA_CHUA_THAY_VAT_TU = "SUA_CHUA_THAY_VAT_TU", "Sửa chữa, thay vật tư"

    ma = models.CharField("mã", max_length=20, unique=True)
    ten_dich_vu = models.CharField("tên dịch vụ", max_length=150)
    nhom_dich_vu = models.CharField("nhóm dịch vụ", max_length=25, choices=NhomDichVu.choices)
    loai_thiet_bi = models.CharField("loại thiết bị", max_length=20, choices=LoaiThietBi.choices)
    don_gia_tham_khao = models.BigIntegerField("đơn giá tham khảo (đ)")
    don_vi_tinh = models.CharField("đơn vị tính", max_length=20)
    thoi_han_bao_hanh_ngay = models.PositiveIntegerField("thời hạn bảo hành (ngày)")
    dang_ap_dung = models.BooleanField("đang áp dụng", default=True)

    class Meta:
        db_table = "tblDichVu"
        verbose_name = "dịch vụ"
        verbose_name_plural = "dịch vụ"
        ordering = ["loai_thiet_bi", "nhom_dich_vu", "ten_dich_vu"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(don_gia_tham_khao__gte=0), name="dich_vu_don_gia_khong_am"
            ),
        ]

    def __str__(self):
        return f"{self.ten_dich_vu} ({self.ma})"


class Tho(MoHinhCoBan):
    class HinhThuc(models.TextChoices):
        CONG_TAC_VIEN = "CONG_TAC_VIEN", "Cộng tác viên"
        CHINH_THUC = "CHINH_THUC", "Chính thức"

    class KenhThongBao(models.TextChoices):
        WEB_PUSH = "WEB_PUSH", "Web Push"
        TELEGRAM = "TELEGRAM", "Telegram"

    nguoi_dung = models.OneToOneField(
        settings.AUTH_USER_MODEL, verbose_name="người dùng", on_delete=models.PROTECT, related_name="tho"
    )
    ho_ten = models.CharField("họ tên", max_length=100)  # sao chép từ người dùng để tra cứu nhanh
    so_dien_thoai = models.CharField("số điện thoại", max_length=10, unique=True)
    hinh_thuc = models.CharField("hình thức", max_length=15, choices=HinhThuc.choices)
    ky_nang = models.ManyToManyField(DichVu, verbose_name="kỹ năng", blank=True, related_name="ds_tho")
    khu_vuc_phu_trach = models.ManyToManyField(
        KhuVuc, verbose_name="khu vực phụ trách", blank=True, related_name="ds_tho"
    )
    dang_nhan_viec = models.BooleanField("sẵn sàng nhận việc", default=True)
    nghi_den = models.DateTimeField("nghỉ đến", null=True, blank=True)
    kenh_thong_bao = models.CharField(
        "kênh thông báo", max_length=10, choices=KenhThongBao.choices, default=KenhThongBao.WEB_PUSH
    )
    telegram_chat_id = models.CharField(  # noqa: DJ001 — SPEC 5.2: Char null (chưa gắn bot)
        "Telegram chat id", max_length=50, null=True, blank=True
    )
    ghi_chu = models.TextField("ghi chú", blank=True)

    class Meta:
        db_table = "tblTho"
        verbose_name = "thợ"
        verbose_name_plural = "thợ"
        ordering = ["ho_ten"]

    def __str__(self):
        return self.ho_ten

    @property
    def ma_tho(self) -> str:
        """Mã thợ dùng trong phiếu đối soát, xuất MISA (A-31)."""
        return f"T{self.pk:03d}"

    @property
    def dang_hoat_dong(self) -> bool:
        return self.nguoi_dung.is_active
