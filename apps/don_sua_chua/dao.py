"""DonSuaChuaDAO — thao tác trên đơn (SPEC 2.2, Phụ lục C). Ghi: kiểm quyền, transaction.atomic(), khóa dòng đơn,
gọi phương thức nghiệp vụ (bảng CHUYEN_TRANG_THAI), ghi nhật ký mọi lần đổi trạng thái."""

from dataclasses import dataclass, field
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Prefetch, Q
from django.utils import timezone

from apps.he_thong.bo_dem import cap_so_thu_tu
from apps.he_thong.cau_hinh import cau_hinh
from apps.he_thong.models import NhatKyThaoTac
from apps.he_thong.nhat_ky import ghi_nhat_ky
from apps.tai_khoan.phan_quyen import GD, TD, VAN_PHONG, kiem_tra_vai_tro
from apps.thong_bao.dich_vu import DichVuThongBao

from .models import DonSuaChua
from .trang_thai import DANG_THUC_HIEN, DANG_XU_LY, TrangThaiDon

GHI_DON = (TD,)  # TONG_DAI và QUAN_TRI (SPEC 3.1: CRU + hủy)
XEM_DON = VAN_PHONG
XEM_BANG_DON = (TD, GD)
T = TrangThaiDon


def sinh_ma_don(ngay: date | None = None) -> str:
    """HF + yyMMdd + '-' + số thứ tự 3 chữ số trong ngày (giờ Việt Nam), ví dụ HF261010-007."""
    ngay = ngay or timezone.localdate()
    return f"HF{ngay:%y%m%d}-{cap_so_thu_tu(ngay):03d}"


def ghi_doi_trang_thai(nguoi_dung, don: DonSuaChua, ly_do: str = "") -> None:
    """Ghi nhật ký lần chuyển trạng thái gần nhất của đơn (nếu có)."""
    if not don._chuyen_gan_nhat:
        return
    ma, tu, den = don._chuyen_gan_nhat
    sau = {"trang_thai": den, "chuyen": ma}
    if ly_do:
        sau["ly_do"] = ly_do
    ghi_nhat_ky(nguoi_dung, "DOI_TRANG_THAI", don, {"trang_thai": tu}, sau)
    don._chuyen_gan_nhat = None


def _lich_hen_prefetch():
    # LichHen thuộc app tiep_nhan_dieu_phoi (tầng trên): lấy lớp qua quan hệ ngược, không import.
    LichHen = DonSuaChua.ds_lich_hen.rel.related_model
    return Prefetch(
        "ds_lich_hen", queryset=LichHen.objects.filter(trang_thai="HIEU_LUC"), to_attr="ds_lich_hieu_luc"
    )


def _phan_cong_prefetch():
    # PhanCong thuộc app tiep_nhan_dieu_phoi (tầng trên): lấy lớp qua quan hệ ngược, không import.
    PhanCong = DonSuaChua.ds_phan_cong.rel.related_model
    return Prefetch(
        "ds_phan_cong",
        queryset=PhanCong.objects.exclude(trang_thai="DA_HUY").select_related("tho"),
        to_attr="ds_phan_cong_hien_hanh",
    )


def gan_canh_bao(ds_don, bay_gio=None) -> None:
    """Gắn thuộc tính hiển thị cho thẻ đơn (UC06, BR02): đề nghị đang chờ + hạn gần nhất, cần cử lại,
    chờ cử thợ quá CANH_BAO_CHO_CU_THO_PHUT (tính từ lúc đơn có lịch hiệu lực — A-56)."""
    bay_gio = bay_gio or timezone.now()
    nguong = timedelta(minutes=cau_hinh("CANH_BAO_CHO_CU_THO_PHUT"))
    for d in ds_don:
        ds_pc = getattr(d, "ds_phan_cong_hien_hanh", [])
        d.de_nghi_dang_cho = [pc for pc in ds_pc if pc.trang_thai == "CHO_PHAN_HOI"]
        d.han_phan_hoi_gan_nhat = min((pc.han_phan_hoi for pc in d.de_nghi_dang_cho), default=None)
        cho_cu = d.trang_thai == T.CHO_CU_THO and d.tho_id is None
        d.can_cu_lai = (
            cho_cu and not d.de_nghi_dang_cho and any(pc.trang_thai in ("TU_CHOI", "QUA_HAN") for pc in ds_pc)
        )
        lich = d.lich_hieu_luc
        moc = lich.tao_luc if lich else d.ngay_tiep_nhan
        d.cho_cu_tho_qua_lau = cho_cu and bay_gio - moc > nguong
        d.hen_gan_chua_co_tho = (
            cho_cu and lich is not None and bay_gio <= lich.bat_dau <= bay_gio + timedelta(hours=2)
        )


@dataclass
class LocBangDon:
    ngay: date | None = None
    khu_vuc: int | None = None
    trang_thai: str = ""
    tho: int | None = None
    tu_khoa: str = ""


@dataclass
class BangDon:
    cot: list[tuple[str, list]] = field(default_factory=list)  # (tiêu đề cột, danh sách đơn)
    ket_thuc_hom_nay: list = field(default_factory=list)
    goi_lai_khach: list = field(default_factory=list)  # Việc cần làm: gọi lại khách (BR08)
    can_cu_lai: list = field(default_factory=list)  # hết hạn phản hồi / bị từ chối, cần cử lại (BR02)
    bao_gia_cho_xac_nhan: list = field(default_factory=list)  # OI-08
    hen_gan_chua_co_tho: list = field(default_factory=list)  # hẹn trong 2 giờ tới chưa có thợ


class DonSuaChuaDAO:
    # ------------------------------------------------------------ đọc

    @staticmethod
    def _co_ban():
        return DonSuaChua.objects.select_related(
            "khach_hang", "dia_chi__khu_vuc", "dich_vu_yeu_cau", "tho", "nguoi_tao"
        ).prefetch_related(_lich_hen_prefetch(), _phan_cong_prefetch())

    @staticmethod
    def lay_theo_ma(nguoi_dung, ma_don: str) -> DonSuaChua:
        kiem_tra_vai_tro(nguoi_dung, *XEM_DON)
        return DonSuaChuaDAO._co_ban().prefetch_related("thiet_bi", "ds_hang_muc").get(ma_don=ma_don)

    @staticmethod
    def tim_don_trung(don: DonSuaChua) -> list[str]:
        """UC02: khách đã có đơn đang xử lý cùng địa chỉ và cùng loại thiết bị → cảnh báo (vẫn cho lưu)."""
        return list(
            DonSuaChua.objects.filter(
                khach_hang_id=don.khach_hang_id,
                dia_chi_id=don.dia_chi_id,
                trang_thai__in=DANG_XU_LY,
                dich_vu_yeu_cau__loai_thiet_bi=don.dich_vu_yeu_cau.loai_thiet_bi,
            )
            .exclude(pk=don.pk)
            .order_by("ngay_tiep_nhan")
            .values_list("ma_don", flat=True)
        )

    @staticmethod
    def bang_don_trong_ngay(nguoi_dung, loc: LocBangDon | None = None) -> BangDon:
        """UC06: các cột theo nhóm Đang xử lý; VIP lên đầu cột; khối hoàn thành/hủy hôm nay; việc cần làm."""
        kiem_tra_vai_tro(nguoi_dung, *XEM_BANG_DON)
        loc = loc or LocBangDon()
        qs = DonSuaChuaDAO._co_ban()
        if loc.khu_vuc:
            qs = qs.filter(dia_chi__khu_vuc_id=loc.khu_vuc)
        if loc.trang_thai:
            qs = qs.filter(trang_thai=loc.trang_thai)
        if loc.tho:
            qs = qs.filter(tho_id=loc.tho)
        if loc.tu_khoa:
            tk = loc.tu_khoa.strip()
            so = "".join(c for c in tk if c.isdigit())
            dk = Q(ma_don__icontains=tk)
            if len(so) >= 4:
                if so.startswith("84") and len(so) == 11:
                    so = "0" + so[2:]
                dk |= Q(khach_hang__so_dien_thoai__contains=so) | Q(
                    khach_hang__so_dien_thoai_phu__contains=so
                )
            qs = qs.filter(dk)
        if loc.ngay:
            # Ngày hẹn theo lịch hiệu lực; đơn chưa có lịch thì theo ngày tiếp nhận (A-46)
            LichHen = DonSuaChua.ds_lich_hen.rel.related_model
            co_lich = LichHen.objects.filter(trang_thai="HIEU_LUC").values("don_id")
            hen_ngay = co_lich.filter(bat_dau__date=loc.ngay)
            qs = qs.filter(Q(pk__in=hen_ngay) | (~Q(pk__in=co_lich) & Q(ngay_tiep_nhan__date=loc.ngay)))
        dang_xu_ly = list(qs.filter(trang_thai__in=DANG_XU_LY).order_by("-uu_tien", "ngay_tiep_nhan"))
        gan_canh_bao(dang_xu_ly)
        bang = BangDon()
        for tieu_de, nhom in (
            ("Chờ xác nhận lịch", {T.CHO_XAC_NHAN_LICH}),
            ("Chờ cử thợ", {T.CHO_CU_THO}),
            ("Đã có thợ", {T.DA_CO_THO}),
            ("Đang thực hiện", DANG_THUC_HIEN),
        ):
            bang.cot.append((tieu_de, [d for d in dang_xu_ly if d.trang_thai in nhom]))
        hom_nay = loc.ngay or timezone.localdate()
        bang.ket_thuc_hom_nay = list(
            DonSuaChuaDAO._co_ban()
            .filter(trang_thai__in=[T.HOAN_THANH, T.DA_HUY], cap_nhat_luc__date=hom_nay)
            .order_by("-cap_nhat_luc")
        )
        bang.goi_lai_khach = [
            d for d in dang_xu_ly if d.trang_thai == T.CHO_XAC_NHAN_LICH and d.so_lan_nhac_xac_nhan > 0
        ]
        bang.can_cu_lai = [d for d in dang_xu_ly if d.can_cu_lai]
        bang.bao_gia_cho_xac_nhan = [d for d in dang_xu_ly if d.cho_tong_dai_xac_nhan_gia]
        bang.hen_gan_chua_co_tho = [d for d in dang_xu_ly if d.hen_gan_chua_co_tho]
        return bang

    @staticmethod
    def lay_don_cho_phan_cong(nguoi_dung) -> list[DonSuaChua]:
        """UC04 (tên theo slide Tuần 12): đơn chờ cử thợ, VIP trước, đơn cũ trước."""
        kiem_tra_vai_tro(nguoi_dung, *XEM_BANG_DON)
        ds = list(
            DonSuaChuaDAO._co_ban().filter(trang_thai=T.CHO_CU_THO).order_by("-uu_tien", "ngay_tiep_nhan")
        )
        gan_canh_bao(ds)
        return ds

    @staticmethod
    def nhat_ky_don(nguoi_dung, don: DonSuaChua):
        kiem_tra_vai_tro(nguoi_dung, *XEM_DON)
        return NhatKyThaoTac.objects.filter(doi_tuong=f"DonSuaChua:{don.ma_don}").select_related("nguoi_dung")

    # ------------------------------------------------------------ ghi

    @staticmethod
    def tao_don(
        nguoi_dung,
        *,
        khach_hang,
        dia_chi,
        dich_vu,
        kenh_tiep_nhan: str,
        da_chot_lich: bool,
        thiet_bi=(),
        mo_ta_su_co: str = "",
        khung_gio_mong_muon: str = "",
        loai_don: str = DonSuaChua.LoaiDon.THUONG,
        don_goc: DonSuaChua | None = None,
    ) -> DonSuaChua:
        """Tạo đơn (T1/T2). Với T2, bên gọi (TiepNhanDAO) tạo LichHen trong cùng giao dịch."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        with transaction.atomic():
            don = DonSuaChua(
                ma_don=sinh_ma_don(),
                khach_hang=khach_hang,
                dia_chi=dia_chi,
                dich_vu_yeu_cau=dich_vu,
                kenh_tiep_nhan=kenh_tiep_nhan,
                mo_ta_su_co=mo_ta_su_co,
                khung_gio_mong_muon=khung_gio_mong_muon,
                loai_don=loai_don,
                don_goc=don_goc,
                nguyen_nhan_bao_hanh=(
                    DonSuaChua.NguyenNhanBaoHanh.CHUA_XAC_DINH
                    if loai_don == DonSuaChua.LoaiDon.BAO_HANH
                    else None
                ),
                uu_tien=khach_hang.la_vip,  # BR07: khách VIP được ưu tiên trong ngày
                nguoi_tao=nguoi_dung,
            )
            don.khoi_tao(da_chot_lich)
            don.thiet_bi.set(thiet_bi)
            ghi_nhat_ky(
                nguoi_dung,
                "TAO_DON",
                don,
                du_lieu_sau={
                    "khach_hang": khach_hang.pk,
                    "dia_chi": dia_chi.pk,
                    "dich_vu": dich_vu.ma,
                    "thiet_bi": sorted(tb.pk for tb in thiet_bi),
                    "kenh": kenh_tiep_nhan,
                    "uu_tien": don.uu_tien,
                },
            )
            ghi_doi_trang_thai(nguoi_dung, don)
        return don

    @staticmethod
    def _thuc_hien(
        nguoi_dung, don: DonSuaChua, ham, hanh_dong: str | None = None, du_lieu: dict | None = None
    ):
        """Khóa dòng đơn, gọi phương thức nghiệp vụ, ghi nhật ký. Trả kết quả của `ham`."""
        with transaction.atomic():
            don_khoa = DonSuaChua.objects.select_for_update().get(pk=don.pk)
            ket_qua = ham(don_khoa)
            if hanh_dong:
                ghi_nhat_ky(nguoi_dung, hanh_dong, don_khoa, du_lieu_sau=du_lieu)
            ghi_doi_trang_thai(nguoi_dung, don_khoa, (du_lieu or {}).get("ly_do", ""))
        return ket_qua

    @staticmethod
    def _tho_co_de_nghi(don: DonSuaChua) -> list:
        """Người dùng (thợ) đang có đề nghị chờ hoặc đã nhận đơn — để báo khi đơn bị hủy/đổi lịch."""
        return [
            pc.tho.nguoi_dung
            for pc in don.ds_phan_cong.filter(
                trang_thai__in=["CHO_PHAN_HOI", "QUA_HAN", "DA_NHAN"]
            ).select_related("tho__nguoi_dung")
        ]

    @staticmethod
    def huy(nguoi_dung, don: DonSuaChua, ly_do: str) -> None:
        """T14: khách hủy (tổng đài thao tác); lịch và đề nghị đang chờ bị hủy, báo cho thợ liên quan."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        with transaction.atomic():
            ds_tho = DonSuaChuaDAO._tho_co_de_nghi(don)
            DonSuaChuaDAO._thuc_hien(
                nguoi_dung, don, lambda d: d.huy(ly_do, nguoi_dung), None, {"ly_do": ly_do}
            )
        for tho in ds_tho:
            DichVuThongBao.gui(tho, f"Đơn {don.ma_don} đã hủy", ly_do, "/tho/")

    @staticmethod
    def de_nghi_doi_lich(nguoi_dung, don: DonSuaChua) -> None:
        """UC04 luồng 2a — T6: không có thợ phù hợp, tổng đài đề nghị khách đổi lịch; hủy cả đề nghị đang chờ."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        with transaction.atomic():
            ds_tho = DonSuaChuaDAO._tho_co_de_nghi(don)

            def lam(d):
                d.de_nghi_doi_lich()
                d.ds_phan_cong.filter(trang_thai__in=["CHO_PHAN_HOI", "QUA_HAN"]).update(
                    trang_thai="DA_HUY", ghi_chu="Đề nghị khách đổi lịch", cap_nhat_luc=timezone.now()
                )

            DonSuaChuaDAO._thuc_hien(nguoi_dung, don, lam, "DE_NGHI_DOI_LICH")
        for tho in ds_tho:
            DichVuThongBao.gui(tho, f"Đề nghị {don.ma_don} đã hủy", "Khách sẽ đổi lịch hẹn.", "/tho/")

    @staticmethod
    def danh_dau_chua_cu_duoc(nguoi_dung, don: DonSuaChua, ly_do: str) -> None:
        """UC04 luồng 2a: đặt cờ “Chưa cử được thợ” (giữ 9 trạng thái — A-12), lý do bắt buộc."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        if not (ly_do or "").strip():
            raise ValidationError({"ly_do": "Nhập lý do chưa cử được thợ."})

        def lam(d):
            if d.trang_thai != T.CHO_CU_THO:
                raise ValidationError("Chỉ đánh dấu được đơn đang chờ cử thợ.")
            d.canh_bao_chua_cu_duoc = True
            d.ly_do_chua_cu_duoc = ly_do.strip()
            d.save(update_fields=["canh_bao_chua_cu_duoc", "ly_do_chua_cu_duoc", "cap_nhat_luc"])

        DonSuaChuaDAO._thuc_hien(nguoi_dung, don, lam, "CHUA_CU_DUOC_THO", {"ly_do": ly_do.strip()})

    @staticmethod
    def khach_giuc(nguoi_dung, don: DonSuaChua) -> int:
        """Nút “Khách giục” trên bảng đơn: tăng so_lan_giuc, ghi nhật ký (UC06)."""
        kiem_tra_vai_tro(nguoi_dung, *GHI_DON)

        def tang(d):
            if not d.dang_xu_ly:
                raise ValueError("Chỉ ghi nhận khách giục với đơn đang xử lý.")
            d.so_lan_giuc += 1
            d.save(update_fields=["so_lan_giuc", "cap_nhat_luc"])
            ghi_nhat_ky(nguoi_dung, "KHACH_GIUC", d, du_lieu_sau={"so_lan_giuc": d.so_lan_giuc})
            return d.so_lan_giuc

        return DonSuaChuaDAO._thuc_hien(nguoi_dung, don, tang)

    @staticmethod
    def nhac_xac_nhan(nguoi_dung, don: DonSuaChua, luc=None) -> bool:
        """Nút “Khách chưa trả lời” (UC03) và tác vụ BR08 dùng chung bộ đếm. Trả False nếu đơn bị hủy (T5)."""
        if nguoi_dung is not None:  # None = tác vụ nền của hệ thống
            kiem_tra_vai_tro(nguoi_dung, *GHI_DON)
        return DonSuaChuaDAO._thuc_hien(
            nguoi_dung, don, lambda d: d.ghi_nhan_nhac_xac_nhan(luc), "NHAC_XAC_NHAN"
        )
