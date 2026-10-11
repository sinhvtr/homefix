"""Gói lõi: DonSuaChua, HangMucSuaChua (SPEC 5.2). Trạng thái chỉ đổi qua phương thức nghiệp vụ (bảng CHUYEN_TRANG_THAI)."""

import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.danh_muc.models import DiaChi, DichVu, KhachHang, ThietBi, Tho
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.models import MoHinhCoBan

from .tinh_tien import DongTien, KetQuaTinhTien, tinh_tien
from .tinh_tien import thanh_tien as tinh_thanh_tien
from .trang_thai import DANG_XU_LY, DAU, ChuyenTrangThaiKhongHopLe, SuKien, TrangThaiDon, tim_chuyen

LY_DO_HET_LUOT_NHAC = "Khách không phản hồi sau 3 lần nhắc"


class DonSuaChua(MoHinhCoBan):
    TrangThai = TrangThaiDon

    class KenhTiepNhan(models.TextChoices):
        DIEN_THOAI = "DIEN_THOAI", "Điện thoại"
        ZALO = "ZALO", "Zalo"
        GIAM_DOC_CHUYEN = "GIAM_DOC_CHUYEN", "Giám đốc chuyển"
        KHAC = "KHAC", "Khác"

    class LoaiDon(models.TextChoices):
        THUONG = "THUONG", "Thường"
        BAO_HANH = "BAO_HANH", "Bảo hành"

    class NguyenNhanBaoHanh(models.TextChoices):
        CHUA_XAC_DINH = "CHUA_XAC_DINH", "Chưa xác định"
        TAY_NGHE = "TAY_NGHE", "Tay nghề"
        VAT_TU = "VAT_TU", "Vật tư"

    ma_don = models.CharField("mã đơn", max_length=16, unique=True)
    khach_hang = models.ForeignKey(
        KhachHang, verbose_name="khách hàng", on_delete=models.PROTECT, related_name="ds_don"
    )
    dia_chi = models.ForeignKey(
        DiaChi, verbose_name="địa chỉ", on_delete=models.PROTECT, related_name="ds_don"
    )
    dich_vu_yeu_cau = models.ForeignKey(
        DichVu, verbose_name="dịch vụ yêu cầu", on_delete=models.PROTECT, related_name="ds_don"
    )
    thiet_bi = models.ManyToManyField(ThietBi, verbose_name="thiết bị", blank=True, related_name="ds_don")
    kenh_tiep_nhan = models.CharField("kênh tiếp nhận", max_length=16, choices=KenhTiepNhan.choices)
    mo_ta_su_co = models.TextField("mô tả sự cố", blank=True)
    khung_gio_mong_muon = models.CharField("khung giờ mong muốn", max_length=100, blank=True)
    trang_thai = models.CharField("trạng thái", max_length=20, choices=TrangThaiDon.choices, editable=False)
    loai_don = models.CharField("loại đơn", max_length=10, choices=LoaiDon.choices, default=LoaiDon.THUONG)
    don_goc = models.ForeignKey(
        "self",
        verbose_name="đơn gốc",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ds_don_bao_hanh",
    )
    nguyen_nhan_bao_hanh = models.CharField(  # noqa: DJ001 — SPEC 5.2: null với đơn thường
        "nguyên nhân bảo hành", max_length=15, choices=NguyenNhanBaoHanh.choices, null=True, blank=True
    )
    tho = models.ForeignKey(
        Tho,
        verbose_name="thợ phụ trách",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ds_don",
    )
    uu_tien = models.BooleanField("ưu tiên", default=False)
    so_lan_giuc = models.PositiveSmallIntegerField("số lần khách giục", default=0)
    so_lan_nhac_xac_nhan = models.PositiveSmallIntegerField("số lần nhắc xác nhận", default=0)
    lan_nhac_cuoi = models.DateTimeField("lần nhắc cuối", null=True, blank=True)
    bao_gia_tong = models.BigIntegerField("tổng báo giá", null=True, blank=True)
    bao_gia_nguoi_xac_nhan = models.CharField("người xác nhận báo giá", max_length=100, blank=True)
    bao_gia_xac_nhan_luc = models.DateTimeField("báo giá xác nhận lúc", null=True, blank=True)
    cho_tong_dai_xac_nhan_gia = models.BooleanField("chờ tổng đài xác nhận giá", default=False)
    tong_tien_phai_thu = models.BigIntegerField("tổng tiền phải thu", null=True, blank=True)
    ly_do_huy = models.TextField("lý do hủy", blank=True)
    nguoi_tao = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người tạo", on_delete=models.PROTECT, related_name="+"
    )
    ngay_tiep_nhan = models.DateTimeField("ngày tiếp nhận", default=timezone.now, db_index=True)
    canh_bao_chua_cu_duoc = models.BooleanField("chưa cử được thợ", default=False)
    ly_do_chua_cu_duoc = models.TextField("lý do chưa cử được", blank=True)

    class Meta:
        db_table = "tblDonSuaChua"
        verbose_name = "đơn sửa chữa"
        verbose_name_plural = "đơn sửa chữa"
        ordering = ["-uu_tien", "ngay_tiep_nhan"]
        indexes = [models.Index(fields=["trang_thai"], name="don_trang_thai_idx")]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(trang_thai__in=TrangThaiDon.values), name="don_trang_thai_hop_le"
            ),
            models.CheckConstraint(
                condition=models.Q(loai_don="THUONG", don_goc__isnull=True)
                | models.Q(loai_don="BAO_HANH", don_goc__isnull=False),
                name="don_bao_hanh_co_don_goc",
            ),
        ]

    _trang_thai_da_luu = None  # trạng thái đang có trong CSDL — để chặn gán trang_thai trực tiếp
    _chuyen_gan_nhat = None  # (mã chuyển, từ, đến) — DAO dùng để ghi nhật ký

    def __str__(self):
        return self.ma_don

    # ------------------------------------------------------------ chặn gán trang_thai trực tiếp

    @classmethod
    def from_db(cls, db, field_names, values):
        don = super().from_db(db, field_names, values)
        if "trang_thai" in don.__dict__:
            don._trang_thai_da_luu = don.trang_thai
        return don

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        if fields is None or "trang_thai" in fields:
            self._trang_thai_da_luu = self.trang_thai

    def save(self, *args, **kwargs):
        if self.trang_thai != self._trang_thai_da_luu and not getattr(self, "_dang_chuyen", False):
            raise ChuyenTrangThaiKhongHopLe(
                "Không gán trang_thai trực tiếp — dùng phương thức nghiệp vụ (bảng CHUYEN_TRANG_THAI)."
            )
        super().save(*args, **kwargs)
        self._trang_thai_da_luu = self.trang_thai

    def _chuyen(self, su_kien: str) -> None:
        dong = tim_chuyen(self.trang_thai or DAU, su_kien)
        truoc = self.trang_thai or None
        if dong.den is not None:
            self.trang_thai = dong.den
        self._chuyen_gan_nhat = (dong.ma, truoc, self.trang_thai)

    def _luu(self, update_fields=None) -> None:
        self._dang_chuyen = True
        try:
            if update_fields is not None:
                update_fields = {*update_fields, "trang_thai", "cap_nhat_luc"}
            self.save(update_fields=update_fields)
        finally:
            self._dang_chuyen = False

    # ------------------------------------------------------------ thuộc tính dẫn xuất

    @property
    def nhom_dich_vu(self) -> str:
        return self.dich_vu_yeu_cau.nhom_dich_vu

    @property
    def lich_hieu_luc(self):
        """Lịch hẹn HIEU_LUC (LichHen thuộc app tiep_nhan_dieu_phoi — truy cập qua quan hệ ngược)."""
        if hasattr(self, "ds_lich_hieu_luc"):  # đã prefetch riêng lịch hiệu lực
            return self.ds_lich_hieu_luc[0] if self.ds_lich_hieu_luc else None
        bo_dem = getattr(self, "_prefetched_objects_cache", {})
        if "ds_lich_hen" in bo_dem:  # đã prefetch toàn bộ lịch
            return next((lh for lh in bo_dem["ds_lich_hen"] if lh.trang_thai == "HIEU_LUC"), None)
        return self.ds_lich_hen.filter(trang_thai="HIEU_LUC").first()

    @property
    def thieu_thong_tin(self) -> bool:
        """Thiếu tên khách hoặc chưa có lịch hiệu lực (UC02 — nhãn cam trên bảng đơn)."""
        return not (self.khach_hang.ho_ten or "").strip() or self.lich_hieu_luc is None

    @property
    def dang_xu_ly(self) -> bool:
        return self.trang_thai in DANG_XU_LY

    @property
    def con_han_bao_hanh(self) -> bool:
        """Phiếu bảo hành còn hạn (PhieuBaoHanh thuộc app bao_hanh — P4/P5; chưa có phiếu → False)."""
        phieu = getattr(self, "phieu_bao_hanh", None)
        return bool(phieu is not None and phieu.con_han)

    def bang_tinh_tien(self, ds_hang_muc=None) -> KetQuaTinhTien:
        """Tính theo SPEC 7.2 từ hạng mục hiện có (hoặc danh sách truyền vào), giảm VIP theo cấu hình."""
        ds = self.ds_hang_muc.all() if ds_hang_muc is None else ds_hang_muc
        return tinh_tien(
            (DongTien(hm.loai, hm.thanh_tien, hm.ben_chiu_chi_phi) for hm in ds),
            la_vip=self.khach_hang.la_vip,
            ty_le_giam=cau_hinh("VIP_TY_LE_GIAM"),
            pham_vi=cau_hinh("VIP_PHAM_VI_GIAM"),
        )

    @property
    def tong_tien(self) -> int:
        """Tổng khách phải trả tính từ hạng mục (SPEC 5.2, 7.2)."""
        return self.bang_tinh_tien().tong_tien

    # ------------------------------------------------------------ phương thức nghiệp vụ (SPEC 5.2, bảng 6.1)

    def khoi_tao(self, da_chot_lich: bool) -> None:
        """T1/T2: đặt trạng thái ban đầu khi tạo đơn. Lịch hẹn của T2 do LichHenDAO tạo trong cùng giao dịch."""
        if self.pk is not None:
            raise ChuyenTrangThaiKhongHopLe("Đơn đã được tạo.")
        self._chuyen(SuKien.TAO_DON_DA_CHOT_LICH if da_chot_lich else SuKien.TAO_DON_CHUA_CHOT_LICH)
        self._luu()

    def bat_dau_cu_tho(self) -> None:
        """T2 (A-42): đơn mới tạo đã có lịch → vào hàng chờ cử thợ. Dùng khi khởi tạo đơn đã chốt lịch."""
        self.khoi_tao(da_chot_lich=True)

    def chot_lich(self, lich) -> None:
        """T3: khách chốt khung giờ. `lich` là LichHen HIEU_LUC vừa tạo cho đơn này."""
        if lich.don_id != self.pk or lich.trang_thai != "HIEU_LUC":
            raise ChuyenTrangThaiKhongHopLe("Lịch hẹn không thuộc đơn hoặc không hiệu lực.")
        self._chuyen(SuKien.CHOT_LICH)
        self._luu(["so_lan_nhac_xac_nhan", "lan_nhac_cuoi"])

    def ghi_nhan_nhac_xac_nhan(self, luc=None) -> bool:
        """T4/T5 (BR08): còn lượt → tăng số lần nhắc (giữ trạng thái), trả True; đã đủ lượt → hủy (T5), trả False."""
        luc = luc or timezone.now()
        if self.so_lan_nhac_xac_nhan < cau_hinh("SO_LAN_NHAC_TOI_DA"):
            self._chuyen(SuKien.NHAC_XAC_NHAN)
            self.so_lan_nhac_xac_nhan += 1
            self.lan_nhac_cuoi = luc
            self._luu(["so_lan_nhac_xac_nhan", "lan_nhac_cuoi"])
            return True
        self._chuyen(SuKien.HET_LUOT_NHAC)
        self.ly_do_huy = LY_DO_HET_LUOT_NHAC
        self._luu(["ly_do_huy"])
        return False

    def de_nghi_doi_lich(self) -> None:
        """T6: không có thợ phù hợp, tổng đài đề nghị khách đổi lịch → lịch hiện tại DA_HUY, chu kỳ nhắc BR08 bắt đầu lại."""
        self._chuyen(SuKien.DE_NGHI_DOI_LICH)
        self.ds_lich_hen.filter(trang_thai="HIEU_LUC").update(
            trang_thai="DA_HUY", cap_nhat_luc=timezone.now()
        )
        self.so_lan_nhac_xac_nhan = 0
        self.lan_nhac_cuoi = timezone.now()
        self.canh_bao_chua_cu_duoc = False
        self._luu(["so_lan_nhac_xac_nhan", "lan_nhac_cuoi", "canh_bao_chua_cu_duoc"])

    def giao_cho_tho(self, phan_cong) -> None:
        """T7: thợ nhận việc (BR03: đơn chưa có thợ). Hủy các đề nghị khác do PhanCongDAO làm (P3)."""
        if self.tho_id is not None:
            raise ChuyenTrangThaiKhongHopLe("Đơn đã có thợ nhận.")
        self._chuyen(SuKien.THO_NHAN_VIEC)
        self.tho = phan_cong.tho
        self.canh_bao_chua_cu_duoc = False
        self._luu(["tho", "canh_bao_chua_cu_duoc"])

    def huy_phan_cong_hien_tai(self, ly_do: str) -> None:
        """T8: thợ báo bận / tổng đài rút việc. Đổi PhanCong → DA_HUY do PhanCongDAO làm (P3)."""
        if not (ly_do or "").strip():
            raise ChuyenTrangThaiKhongHopLe("Cần lý do trả việc.")
        self._chuyen(SuKien.RUT_VIEC)
        self.tho = None
        self._luu(["tho"])

    def tho_den_noi(self) -> None:
        """T9 (sửa chữa → chờ duyệt giá) / T10 (vệ sinh → đang sửa, tạo dòng CONG theo bảng giá) — BR06."""
        if self.nhom_dich_vu == DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU:
            self._chuyen(SuKien.DEN_NOI_SUA_CHUA)
            self._luu()
            return
        self._chuyen(SuKien.DEN_NOI_VE_SINH)
        dv = self.dich_vu_yeu_cau
        HangMucSuaChua.objects.create(
            don=self,
            loai=HangMucSuaChua.Loai.CONG,
            dich_vu=dv,
            mo_ta=dv.ten_dich_vu,
            so_luong=Decimal(max(1, self.thiet_bi.count())),
            don_gia_thuc_te=dv.don_gia_tham_khao,
            ben_chiu_chi_phi=self.ben_chiu_mac_dinh(HangMucSuaChua.Loai.CONG),
        )
        self._luu()

    def _kiem_tra_bao_gia(self) -> None:
        if self.nhom_dich_vu != DichVu.NhomDichVu.SUA_CHUA_THAY_VAT_TU:
            raise ChuyenTrangThaiKhongHopLe(
                "Dịch vụ vệ sinh tính theo bảng giá, không có bước duyệt báo giá (BR06)."
            )
        if not self.ds_hang_muc.exists():
            raise ChuyenTrangThaiKhongHopLe("Chưa có hạng mục báo giá.")

    def _chot_bao_gia(self, nguoi: str, luc) -> None:
        self.ds_hang_muc.update(la_bao_gia=True)
        self.bao_gia_tong = self.tong_tien
        self.bao_gia_nguoi_xac_nhan = nguoi or self.khach_hang.ho_ten
        self.bao_gia_xac_nhan_luc = luc or timezone.now()

    def khach_duyet_gia(self, nguoi: str, luc=None) -> bool:
        """T11 nếu dưới ngưỡng OI-08; từ ngưỡng trở lên → gắn cờ chờ tổng đài gọi xác nhận (T12), trả False."""
        if self.trang_thai != TrangThaiDon.CHO_DUYET_GIA:
            tim_chuyen(self.trang_thai, SuKien.KHACH_DUYET_GIA)  # ném lỗi với thông điệp chuẩn
        self._kiem_tra_bao_gia()
        nguong = cau_hinh("NGUONG_BAO_GIA_TONG_DAI_XAC_NHAN")
        tong = self.tong_tien
        if nguong > 0 and tong >= nguong:
            self.cho_tong_dai_xac_nhan_gia = True
            self.bao_gia_tong = tong
            self.bao_gia_nguoi_xac_nhan = nguoi or self.khach_hang.ho_ten
            self._luu(["cho_tong_dai_xac_nhan_gia", "bao_gia_tong", "bao_gia_nguoi_xac_nhan"])
            return False
        self._chuyen(SuKien.KHACH_DUYET_GIA)
        self._chot_bao_gia(nguoi, luc)
        self._luu(["bao_gia_tong", "bao_gia_nguoi_xac_nhan", "bao_gia_xac_nhan_luc"])
        return True

    def tong_dai_xac_nhan_gia(self, luc=None) -> None:
        """T12: tổng đài đã gọi xác nhận báo giá vượt ngưỡng với khách."""
        if not self.cho_tong_dai_xac_nhan_gia:
            raise ChuyenTrangThaiKhongHopLe("Báo giá không ở trạng thái chờ tổng đài xác nhận.")
        self._kiem_tra_bao_gia()
        self._chuyen(SuKien.TONG_DAI_XAC_NHAN_GIA)
        self._chot_bao_gia(self.bao_gia_nguoi_xac_nhan, luc)
        self.cho_tong_dai_xac_nhan_gia = False
        self._luu(
            ["bao_gia_tong", "bao_gia_nguoi_xac_nhan", "bao_gia_xac_nhan_luc", "cho_tong_dai_xac_nhan_gia"]
        )

    def khach_tu_choi_gia(self, ly_do: str) -> None:
        """T13: khách từ chối báo giá; ghi phí kiểm tra nếu cấu hình > 0 (A-04)."""
        self._chuyen(SuKien.KHACH_TU_CHOI_GIA)
        self.ly_do_huy = (ly_do or "").strip() or "Khách từ chối báo giá"
        self.cho_tong_dai_xac_nhan_gia = False
        phi = cau_hinh("PHI_KIEM_TRA_KHI_TU_CHOI")
        if phi > 0:
            HangMucSuaChua.objects.create(
                don=self,
                loai=HangMucSuaChua.Loai.PHI_KHAC,
                mo_ta="Phí kiểm tra",
                so_luong=Decimal(1),
                don_gia_thuc_te=phi,
            )
        self._luu(["ly_do_huy", "cho_tong_dai_xac_nhan_gia"])

    def hoan_thanh(self, so_tien: int, so_anh: int) -> None:
        """T15: điều kiện đã nhập tiền thu, đủ ảnh. Tạo ThanhToan, PhieuBaoHanh do DAO làm (P4)."""
        if self.trang_thai != TrangThaiDon.DANG_SUA:
            tim_chuyen(self.trang_thai, SuKien.HOAN_THANH)
        if so_tien is None or int(so_tien) < 0:
            raise ChuyenTrangThaiKhongHopLe("Cần nhập số tiền đã thu (≥ 0).")
        if so_anh < cau_hinh("SO_ANH_TOI_THIEU_KHI_HOAN_THANH"):
            raise ChuyenTrangThaiKhongHopLe("Chưa đủ ảnh hiện trường.")
        if self.loai_don == self.LoaiDon.BAO_HANH and self.nguyen_nhan_bao_hanh in (
            None,
            self.NguyenNhanBaoHanh.CHUA_XAC_DINH,
        ):
            raise ChuyenTrangThaiKhongHopLe(
                "Đơn bảo hành: xác định nguyên nhân (tay nghề / vật tư) trước khi hoàn thành."
            )
        self._chuyen(SuKien.HOAN_THANH)
        self.tong_tien_phai_thu = self.tong_tien
        self._luu(["tong_tien_phai_thu"])

    def mo_bao_hanh(self, don_bh: "DonSuaChua") -> None:
        """T16: tạo đơn bảo hành cho đơn gốc này (phiếu bảo hành còn hạn)."""
        if don_bh.don_goc_id != self.pk:
            raise ChuyenTrangThaiKhongHopLe("Đơn bảo hành không thuộc đơn gốc này.")
        if self.trang_thai == TrangThaiDon.HOAN_THANH and not self.con_han_bao_hanh:
            raise ChuyenTrangThaiKhongHopLe("Phiếu bảo hành đã hết hạn — tạo đơn thường.")
        self._chuyen(SuKien.MO_BAO_HANH)
        self._luu()

    def ket_thuc_bao_hanh(self) -> None:
        """T17: đơn bảo hành con hoàn thành hoặc bị hủy."""
        self._chuyen(SuKien.KET_THUC_BAO_HANH)
        self._luu()

    def huy(self, ly_do: str, nguoi=None) -> None:
        """T14: khách hủy khi đơn đang xử lý; hủy lịch hiệu lực (và đề nghị đang chờ — P3)."""
        if not (ly_do or "").strip():
            raise ChuyenTrangThaiKhongHopLe("Cần lý do hủy.")
        self._chuyen(SuKien.KHACH_HUY)
        self.ly_do_huy = ly_do.strip()
        self.cho_tong_dai_xac_nhan_gia = False
        self.ds_lich_hen.filter(trang_thai="HIEU_LUC").update(
            trang_thai="DA_HUY", cap_nhat_luc=timezone.now()
        )
        ds_phan_cong = getattr(self, "ds_phan_cong", None)  # PhanCong có từ P3
        if ds_phan_cong is not None:
            ds_phan_cong.filter(trang_thai__in=["CHO_PHAN_HOI", "DA_NHAN"]).update(
                trang_thai="DA_HUY", cap_nhat_luc=timezone.now()
            )
        self._luu(["ly_do_huy", "cho_tong_dai_xac_nhan_gia"])

    def dong(self) -> None:
        """T18: hết hạn bảo hành (tác vụ hằng ngày, P5)."""
        if self.trang_thai == TrangThaiDon.HOAN_THANH and self.con_han_bao_hanh:
            raise ChuyenTrangThaiKhongHopLe("Phiếu bảo hành còn hạn.")
        self._chuyen(SuKien.HET_HAN_BAO_HANH)
        self._luu()

    # ------------------------------------------------------------ tiện ích

    def xac_dinh_nguyen_nhan(self, nguyen_nhan: str) -> None:
        """UC11/BR05: đặt nguyên nhân bảo hành và tính lại bên chịu chi phí của mọi dòng (không bao giờ là KHACH)."""
        if self.loai_don != self.LoaiDon.BAO_HANH:
            raise ChuyenTrangThaiKhongHopLe("Chỉ đơn bảo hành mới có nguyên nhân bảo hành.")
        if nguyen_nhan not in (self.NguyenNhanBaoHanh.TAY_NGHE, self.NguyenNhanBaoHanh.VAT_TU):
            raise ChuyenTrangThaiKhongHopLe("Chọn nguyên nhân: tay nghề hoặc vật tư.")
        if not self.dang_xu_ly:
            raise ChuyenTrangThaiKhongHopLe("Đơn đã kết thúc, không đổi nguyên nhân được.")
        self.nguyen_nhan_bao_hanh = nguyen_nhan
        self.save(update_fields=["nguyen_nhan_bao_hanh", "cap_nhat_luc"])
        for loai in HangMucSuaChua.Loai.values:
            self.ds_hang_muc.filter(loai=loai).update(
                ben_chiu_chi_phi=self.ben_chiu_mac_dinh(loai), cap_nhat_luc=timezone.now()
            )

    def ben_chiu_mac_dinh(self, loai: str) -> str:
        """BR05: đơn thường → khách chịu; đơn bảo hành không thu khách (tay nghề: thợ chịu công; còn lại công ty)."""
        if self.loai_don == self.LoaiDon.THUONG:
            return HangMucSuaChua.BenChiu.KHACH
        if self.nguyen_nhan_bao_hanh == self.NguyenNhanBaoHanh.TAY_NGHE and loai == HangMucSuaChua.Loai.CONG:
            return HangMucSuaChua.BenChiu.THO
        return HangMucSuaChua.BenChiu.CONG_TY


class HangMucSuaChua(MoHinhCoBan):
    class Loai(models.TextChoices):
        CONG = "CONG", "Tiền công"
        VAT_TU = "VAT_TU", "Vật tư"
        PHI_KHAC = "PHI_KHAC", "Phí khác"

    class NguoiUng(models.TextChoices):
        THO = "THO", "Thợ"
        CONG_TY = "CONG_TY", "Công ty"

    class BenChiu(models.TextChoices):
        KHACH = "KHACH", "Khách"
        THO = "THO", "Thợ"
        CONG_TY = "CONG_TY", "Công ty"

    don = models.ForeignKey(
        DonSuaChua, verbose_name="đơn", on_delete=models.CASCADE, related_name="ds_hang_muc"
    )
    loai = models.CharField("loại", max_length=10, choices=Loai.choices)
    dich_vu = models.ForeignKey(
        DichVu,
        verbose_name="dịch vụ",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ds_hang_muc",
    )
    thiet_bi = models.ForeignKey(
        ThietBi,
        verbose_name="thiết bị",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="ds_hang_muc",
    )
    mo_ta = models.CharField("mô tả", max_length=255)
    so_luong = models.DecimalField("số lượng", max_digits=10, decimal_places=2)
    don_gia_thuc_te = models.BigIntegerField("đơn giá thực tế (đ)")
    gia_mua = models.BigIntegerField("giá mua (đ)", null=True, blank=True)
    co_hoa_don = models.BooleanField("có hóa đơn", default=False)
    nguoi_ung = models.CharField(
        "người ứng tiền", max_length=10, choices=NguoiUng.choices, default=NguoiUng.THO
    )
    la_bao_gia = models.BooleanField("thuộc báo giá đã duyệt", default=False)
    ben_chiu_chi_phi = models.CharField(
        "bên chịu chi phí", max_length=10, choices=BenChiu.choices, default=BenChiu.KHACH
    )

    class Meta:
        db_table = "tblHangMucSuaChua"
        verbose_name = "hạng mục sửa chữa"
        verbose_name_plural = "hạng mục sửa chữa"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(so_luong__gt=0), name="hang_muc_so_luong_duong"),
            models.CheckConstraint(
                condition=models.Q(don_gia_thuc_te__gte=0), name="hang_muc_don_gia_khong_am"
            ),
        ]

    def __str__(self):
        return f"{self.get_loai_display()}: {self.mo_ta}"

    @property
    def thanh_tien(self) -> int:
        """so_luong × don_gia_thuc_te, làm tròn đến đồng."""
        return tinh_thanh_tien(self.so_luong, self.don_gia_thuc_te)


def duong_dan_anh(anh: "AnhHienTruong", ten_goc: str) -> str:
    """Tên tệp ngẫu nhiên, không chứa thông tin khách (NFR04)."""
    bay_gio = timezone.localtime()
    return f"anh/{bay_gio:%Y/%m}/{uuid.uuid4().hex}.jpg"


class AnhHienTruong(MoHinhCoBan):
    """Ảnh hiện trường / ảnh báo giá của đơn (UC08, UC09). Lớp hỗ trợ — A-67. Phục vụ qua /anh/<id>/ có kiểm quyền."""

    class Loai(models.TextChoices):
        HIEN_TRUONG = "HIEN_TRUONG", "Ảnh hiện trường"
        BAO_GIA = "BAO_GIA", "Ảnh báo giá"

    don = models.ForeignKey(DonSuaChua, verbose_name="đơn", on_delete=models.CASCADE, related_name="ds_anh")
    loai = models.CharField("loại", max_length=12, choices=Loai.choices, default=Loai.HIEN_TRUONG)
    tep = models.ImageField("tệp ảnh", upload_to=duong_dan_anh)
    rong = models.PositiveIntegerField("rộng (px)")
    cao = models.PositiveIntegerField("cao (px)")
    nguoi_tai = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="người tải", on_delete=models.PROTECT, related_name="+"
    )

    class Meta:
        db_table = "tblAnhHienTruong"
        verbose_name = "ảnh hiện trường"
        verbose_name_plural = "ảnh hiện trường"
        ordering = ["tao_luc", "id"]

    def __str__(self):
        return f"{self.don_id}: {self.get_loai_display()} #{self.pk}"
